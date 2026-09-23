# -*- coding: utf-8 -*-
"""Aura PearlPow motor — SRBMiner pearlhash under Aura UI."""
from __future__ import annotations

import os
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable


class PearlMotor:
    def __init__(
        self,
        aura_root: Path,
        on_log: Callable[[str], None] | None = None,
        on_stats: Callable[[dict], None] | None = None,
    ) -> None:
        self.aura_root = Path(aura_root)
        self.bin_dir = self.aura_root / "bin"
        self.exe = self.bin_dir / "SRBMiner-MULTI.exe"
        self.on_log = on_log or (lambda _m: None)
        self.on_stats = on_stats or (lambda _s: None)
        self._proc: subprocess.Popen | None = None
        self._reader: threading.Thread | None = None
        self._stop = threading.Event()
        self._watch: threading.Thread | None = None
        self._wallet_used = ""
        self._pool_used = ""
        self.stats = {
            "hashrate_hs": 0.0,
            "hashrate": "0 H/s",
            "accepted": 0,
            "rejected": 0,
            "total": 0,
            "engine": "Aura PearlPow AI",
        }

    def available(self) -> bool:
        return self.exe.is_file()

    def _pick_gpu_id(self) -> str:
        env = os.environ.get("AURA_GPU_ID")
        if env is not None and str(env).strip() != "":
            return str(env).strip()
        # Prefer NVIDIA over AMD iGPU for PearlPow
        try:
            out = subprocess.check_output(
                ["nvidia-smi", "-L"],
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=3,
                **(
                    {"creationflags": subprocess.CREATE_NO_WINDOW}
                    if hasattr(subprocess, "CREATE_NO_WINDOW")
                    else {}
                ),
            )
            if "NVIDIA" in out.upper() or "GeForce" in out or "RTX" in out:
                # On dual OpenCL platforms SRBMiner often lists AMD=0 NVIDIA=1
                return "1"
        except Exception:
            pass
        return "0"


    @staticmethod
    def _build_wallet(
        wallet: str,
        worker: str,
        payout_coin: str | None = None,
        payout_address: str | None = None,
    ) -> str:
        """unMineable: Alias.worker, PRL:prl1….worker, or COIN:addr.worker."""
        wallet = (wallet or "").strip()
        worker = (worker or "Aura").strip() or "Aura"
        if not wallet:
            return wallet
        # Already COIN:… or BTC:…
        if ":" in wallet:
            after = wallet.split(":", 1)[1]
            if "." not in after:
                return f"{wallet}.{worker}"
            return wallet
        low = wallet.lower()
        # Native Pearl bech32
        if low.startswith("prl1"):
            return f"PRL:{wallet}.{worker}" if "." not in wallet else f"PRL:{wallet}"
        # unMineable Alias (short alnum)
        if re.fullmatch(r"[A-Za-z0-9_-]{3,40}", wallet) and not low.startswith("r"):
            return f"{wallet}.{worker}" if "." not in wallet else wallet
        # Invalid native PRL (e.g. XRP-like r…) → payout coin (BTC)
        pc = (payout_coin or "").strip().upper()
        pa = (payout_address or "").strip()
        if pc and pa and pc not in ("NATIVE", "PRL"):
            if "." not in pa:
                return f"{pc}:{pa}.{worker}"
            return f"{pc}:{pa}"
        if pa and (pa.lower().startswith("bc1") or pa.startswith("1") or pa.startswith("3")):
            return f"BTC:{pa}.{worker}" if "." not in pa else f"BTC:{pa}"
        # Last resort legacy (may be rejected by pool)
        if "." in wallet:
            return f"PRL:{wallet}"
        return f"PRL:{wallet}.{worker}"

    def _build_cmd(self, wallet: str, pool_url: str, gid: str | None) -> list[str]:
        cmd = [
            str(self.exe),
            "--algorithm",
            "pearlhash",
            "--disable-cpu",
            "--pool",
            pool_url,
            "--wallet",
            wallet,
            "--gpu-boost",
            "3",
            "--keepalive",
            "true",
            "--log-file",
            str(self.bin_dir / "aura-pearl.log"),
            "--api-enable",
            "--api-port",
            "21550",
            "--api-rig-name",
            "Aura",
        ]
        if gid is not None:
            cmd.extend(["--gpu-id", gid])
        return cmd

    def _popen(self, cmd: list[str]) -> subprocess.Popen:
        creation = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        kwargs = dict(
            cwd=str(self.bin_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        if creation:
            kwargs["creationflags"] = creation
        return subprocess.Popen(cmd, **kwargs)

    def _kill_proc(self) -> None:
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=5)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
        self._proc = None

    def _log_shows_job_or_hash(self) -> bool:
        logf = self.bin_dir / "aura-pearl.log"
        try:
            if not logf.is_file():
                return False
            text = logf.read_text(encoding="utf-8", errors="replace")
            # only last ~8 KB
            tail = text[-8000:].lower()
            keys = (
                "job",
                "accepted",
                "authorized",
                "new job",
                "share accepted",
                "hashrate",
                "h/s",
            )
            # reconnect loop without job is failure
            if any(k in tail for k in keys):
                # if only reconnect and socket unavailable, treat as fail
                if "on_switch_pool" in tail and "user socket unavailable" in tail:
                    # still need positive signal
                    if not any(
                        k in tail
                        for k in ("accepted", "new job", "authorized", "job received")
                    ) and self.stats.get("hashrate_hs", 0) <= 0:
                        return False
                return True
        except Exception:
            pass
        return float(self.stats.get("hashrate_hs") or 0) > 0 or int(
            self.stats.get("accepted") or 0
        ) > 0

    def _reconnect_loop_detected(self) -> bool:
        logf = self.bin_dir / "aura-pearl.log"
        try:
            if not logf.is_file():
                return False
            tail = logf.read_text(encoding="utf-8", errors="replace")[-8000:].lower()
            return (
                "on_switch_pool" in tail
                and "user socket unavailable" in tail
                and not self._log_shows_job_or_hash()
            )
        except Exception:
            return False

    def _watch_failover(
        self, wallet: str, host: str, port: int, gid: str
    ) -> None:
        """Ako TCP i dalje reconnecta bez joba (~25s), restart na SSL :4444."""
        time.sleep(25)
        if self._stop.is_set() or not self.is_running():
            return
        if self._log_shows_job_or_hash():
            self.on_log("Pearl · TCP pool OK (job/hashrate)")
            return
        if not self._reconnect_loop_detected() and float(
            self.stats.get("hashrate_hs") or 0
        ) > 0:
            return
        ssl_host = host or "pearlpow.unmineable.com"
        ssl_url = f"stratum+ssl://{ssl_host}:4444"
        self.on_log(
            "Pearl · TCP bez joba / reconnect petlja — prebacujem na SSL :4444"
        )
        self._stop.set()
        self._kill_proc()
        self._stop.clear()
        # truncate hint in log via append note
        cmd = self._build_cmd(wallet, ssl_url, gid)
        self._pool_used = ssl_url
        self.on_log(f"Aura PearlPow AI · pool SSL {ssl_host}:4444 · GPU id {gid}")
        self._proc = self._popen(cmd)
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        time.sleep(1.2)
        if self._proc.poll() is not None:
            self.on_log("Pearl SSL retry bez --gpu-id …")
            cmd2 = self._build_cmd(wallet, ssl_url, None)
            self._proc = self._popen(cmd2)
            self._reader = threading.Thread(target=self._read_loop, daemon=True)
            self._reader.start()

    def start(self, wallet: str, host: str, port: int, worker: str = "Aura", payout_coin: str | None = None, payout_address: str | None = None) -> None:
        if self._proc and self._proc.poll() is None:
            return
        if not self.available():
            raise RuntimeError(
                "Nema SRBMiner-MULTI.exe u Aura\\bin. Dozvoli miner u Defenderu."
            )
        wallet_raw = (wallet or "").strip()
        if not wallet_raw:
            raise RuntimeError("Nema PRL wallet adrese")
        worker = (worker or "Aura").strip() or "Aura"
        w = self._build_wallet(wallet_raw, worker, payout_coin=payout_coin, payout_address=payout_address)
        self._wallet_used = w
        host = (host or "pearlpow.unmineable.com").strip()
        port = int(port or 3333)
        gid = self._pick_gpu_id()
        # Primary TCP; SRBMiner also accepts comma-separated failover pools
        ssl_primary = f"stratum+ssl://{host}:4444"
        tcp = f"stratum+tcp://{host}:{port}"
        # SSL first (TCP often drops auth); TCP as failover
        pool_arg = f"{ssl_primary},{tcp}"
        primary = ssl_primary
        self._pool_used = ssl_primary
        cmd = self._build_cmd(w, pool_arg, gid)
        self._stop.clear()
        self.on_log(f"Aura PearlPow AI · pool {host}:{port} (+SSL failover) · GPU id {gid}")
        self.on_log(
            f"Wallet {w[:20]}…{w[-10:] if len(w) > 30 else w}  [unMineable wallet]"
        )
        self.on_log("Pearl AI motor je SRBMiner pearlhash only (bez SHA256 AI)")
        self._proc = self._popen(cmd)
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        time.sleep(1.2)
        if self._proc.poll() is not None:
            self.on_log("Pearl retry bez --gpu-id …")
            cmd2 = self._build_cmd(w, pool_arg, None)
            self._proc = self._popen(cmd2)
            self._reader = threading.Thread(target=self._read_loop, daemon=True)
            self._reader.start()
            time.sleep(1.0)
            if self._proc.poll() is not None:
                # last resort: single TCP pool only
                self.on_log("Pearl retry samo TCP pool …")
                cmd3 = self._build_cmd(w, primary, gid)
                self._proc = self._popen(cmd3)
                self._reader = threading.Thread(target=self._read_loop, daemon=True)
                self._reader.start()
                time.sleep(1.0)
                if self._proc.poll() is not None:
                    raise RuntimeError(
                        "Pearl miner se ugasio odmah. Pogledaj Aura\\bin\\aura-pearl.log"
                    )
        # Background watcher: if still reconnecting after ~25s, force SSL-only
        self._watch = threading.Thread(
            target=self._watch_failover, args=(w, host, port, gid), daemon=True
        )
        self._watch.start()
        self._log_poll = threading.Thread(target=self._poll_log_stats, daemon=True)
        self._log_poll.start()

    def _poll_log_stats(self) -> None:
        """SRBMiner often logs to file more than stdout — keep UI stats from aura-pearl.log."""
        logf = self.bin_dir / "aura-pearl.log"
        rate_re = re.compile(r"Total:\s*([0-9]+(?:\.[0-9]+)?)\s*(H|KH|MH|GH|TH)/s", re.I)
        acc_re = re.compile(r"\bA:(\d+)\b")
        pos = 0
        if logf.is_file():
            try:
                pos = logf.stat().st_size
            except Exception:
                pos = 0
        while not self._stop.is_set() and self.is_running():
            try:
                if not logf.is_file():
                    time.sleep(2)
                    continue
                size = logf.stat().st_size
                if size < pos:
                    pos = 0
                if size > pos:
                    with open(logf, "r", encoding="utf-8", errors="replace") as f:
                        f.seek(pos)
                        chunk = f.read()
                        pos = f.tell()
                    for line in chunk.splitlines():
                        low = line.lower()
                        if "share accepted" in low:
                            self.stats["accepted"] = int(self.stats.get("accepted") or 0) + 1
                            self.stats["total"] = int(self.stats["accepted"]) + int(self.stats.get("rejected") or 0)
                            self.on_log(f"Pearl · {line[:220]}")
                            self.on_stats(dict(self.stats))
                        m = rate_re.search(line)
                        if m:
                            val = float(m.group(1))
                            unit = m.group(2).upper()
                            mult = {"H": 1.0, "KH": 1e3, "MH": 1e6, "GH": 1e9, "TH": 1e12}[unit]
                            self.stats["hashrate_hs"] = val * mult
                            self.stats["hashrate"] = f"{val} {unit}/s"
                            am = acc_re.search(line)
                            if am:
                                self.stats["accepted"] = int(am.group(1))
                                self.stats["total"] = int(self.stats["accepted"]) + int(self.stats.get("rejected") or 0)
                            self.on_stats(dict(self.stats))
            except Exception:
                pass
            time.sleep(2)

    def stop(self) -> None:
        self._stop.set()
        self._kill_proc()
        self.on_log("Aura PearlPow AI stop")

    def is_running(self) -> bool:
        return bool(self._proc and self._proc.poll() is None)

    def _read_loop(self) -> None:
        if not self._proc or not self._proc.stdout:
            return
        rate_re = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*(H|KH|MH|GH|TH)/s", re.I)
        for line in self._proc.stdout:
            if self._stop.is_set():
                break
            line = (line or "").rstrip()
            if not line:
                continue
            low = line.lower()
            interesting = any(
                k in low
                for k in (
                    "accept",
                    "reject",
                    "share",
                    "block",
                    "error",
                    "pool",
                    "job",
                    "hashrate",
                    "speed",
                    "connected",
                    "diff",
                    "gpu",
                    "authoriz",
                    "switch",
                    "socket",
                )
            )
            if interesting:
                self.on_log(f"Pearl · {line[:220]}")
            if "accept" in low and "reject" not in low:
                self.stats["accepted"] = int(self.stats.get("accepted") or 0) + 1
                self.stats["total"] = int(self.stats.get("accepted") or 0) + int(
                    self.stats.get("rejected") or 0
                )
            if "reject" in low:
                self.stats["rejected"] = int(self.stats.get("rejected") or 0) + 1
                self.stats["total"] = int(self.stats.get("accepted") or 0) + int(
                    self.stats.get("rejected") or 0
                )
            m = rate_re.search(line)
            if m:
                val = float(m.group(1))
                unit = m.group(2).upper()
                mult = {"H": 1.0, "KH": 1e3, "MH": 1e6, "GH": 1e9, "TH": 1e12}[unit]
                hs = val * mult
                self.stats["hashrate_hs"] = hs
                self.stats["hashrate"] = f"{val} {unit}/s"
                self.on_stats(dict(self.stats))
        self.on_log("Pearl miner process ended")
