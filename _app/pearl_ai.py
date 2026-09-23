# -*- coding: utf-8 -*-
"""Aura Pearl AI Hunter — agresivan lov na jobove/blok-kandidate.

Uloga koju je korisnik tražio natrag: AI rudar koji čim padne novi job
ulazi u race, gura GPU, uči boost, javlja teške shareove / kandidate.
Ne laže 'BTC blok nađen' osim ako miner/log stvarno kaže block found.
"""
from __future__ import annotations

import json
import re
import subprocess
import threading
import time
import urllib.request
from pathlib import Path
from typing import Callable


def _nvidia() -> dict:
    try:
        kw: dict = dict(stderr=subprocess.DEVNULL, text=True, timeout=3)
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            kw["creationflags"] = subprocess.CREATE_NO_WINDOW
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=index,temperature.gpu,utilization.gpu,power.draw,power.limit,clocks.gr,clocks.mem",
                "--format=csv,noheader,nounits",
            ],
            **kw,
        )
        # Prefer discrete NVIDIA (5070) — often index 0 on nvidia-smi even if SRB id=1
        best = {}
        for line in out.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            def f(i: int):
                try:
                    return float(parts[i])
                except Exception:
                    return None
            row = {
                "index": int(float(parts[0])) if parts else 0,
                "temp": f(1),
                "util": f(2),
                "power": f(3),
                "plimit": f(4),
                "core": f(5),
                "mem": f(6),
            }
            if not best or (row.get("plimit") or 0) >= (best.get("plimit") or 0):
                best = row
        return best
    except Exception:
        return {}


def _srb_api(port: int = 21550) -> dict:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}", timeout=2) as r:
            return json.loads(r.read().decode("utf-8", errors="replace"))
    except Exception:
        return {}


class PearlAI:
    """AI rudar za PearlPow: race na novi job, maximizira lov."""

    def __init__(
        self,
        config_path: Path,
        aura_root: Path,
        on_log: Callable[[str], None] | None = None,
        get_stats: Callable[[], dict] | None = None,
        restart_miner: Callable[[], None] | None = None,
        on_notify: Callable[[str, str], None] | None = None,
    ) -> None:
        self.config_path = Path(config_path)
        self.aura_root = Path(aura_root)
        self.log_path = self.aura_root / "bin" / "aura-pearl.log"
        self.on_log = on_log or (lambda _m: None)
        self.get_stats = get_stats or (lambda: {})
        self.restart_miner = restart_miner
        self.on_notify = on_notify or (lambda _t, _b: None)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._log_pos = 0
        self._last_job_key = ""
        self._boost = 4
        self._best_boost = 4
        self._best_rate = 0.0
        self._shares = 0
        self._hard_shares = 0
        self._jobs_seen = 0
        self._tick = 0
        self._race_until = 0.0
        self._stable = 0
        self._last_rate = 0.0
        self._last_share_ms = None
        self._ms_re = re.compile(r"share accepted\s*\[\s*(\d+)\s*ms\]", re.I)
        self._diff_re = re.compile(r"diff[:\s]+([\d.]+)", re.I)

    def _load_cfg(self) -> dict:
        try:
            return json.loads(self.config_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_cfg(self, cfg: dict) -> None:
        try:
            self.config_path.write_text(
                json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception:
            pass

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        cfg = self._load_cfg()
        cfg["auto_ai"] = True
        cfg["pearl_ai"] = True
        # Agresivniji default boost 4 (1..8)
        self._boost = int(cfg.get("pearl_ai_boost") or cfg.get("ai_intensity") or 4)
        self._boost = max(1, min(8, self._boost))
        self._best_boost = int(cfg.get("pearl_ai_best_boost") or self._boost)
        self._best_rate = float(cfg.get("pearl_ai_best_rate") or 0)
        self._save_cfg(cfg)
        if self.log_path.is_file():
            try:
                self._log_pos = self.log_path.stat().st_size
            except Exception:
                self._log_pos = 0
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="PearlAI", daemon=True)
        self._thread.start()
        mode = str(cfg.get("mode") or "pool")
        self.on_log(
            f"Aura AI hunter ON · PearlPow · boost={self._boost} · mode={mode} "
            f"(agresivan lov — novi job = race, teški share = kandidat)"
        )
        self.on_notify("Aura AI", f"Hunter upaljen · boost {self._boost}")

    def stop(self) -> None:
        self._stop.set()
        self.on_log("Aura AI hunter OFF")

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive() and not self._stop.is_set())

    def current_boost(self) -> int:
        return int(self._boost)

    def _loop(self) -> None:
        time.sleep(2)
        # Odmah race-warm: digni GPU
        self._nudge_gpu_race(force=True)
        while not self._stop.is_set():
            self._tick += 1
            try:
                self._read_log_events()
                self._watch_api_job()
                self._step()
            except Exception as exc:
                self.on_log(f"AI hunter greška: {exc}")
            # Brži tick = brži odziv na job (2s umjesto 4s)
            self._stop.wait(2)

    def _watch_api_job(self) -> None:
        """Ako log ne uhvati job, SRB API 'last job' / mining time hint."""
        api = _srb_api(21550)
        if not api:
            return
        # Some builds expose algorithms[].pool or similar
        try:
            key = ""
            for alg in api.get("algorithms") or []:
                if not isinstance(alg, dict):
                    continue
                key = str(alg.get("pool") or alg.get("difficulty") or "") + str(
                    alg.get("accepted_shares") or alg.get("shares") or ""
                )
            if key and key != self._last_job_key and "accepted" in key.lower():
                # don't false-race on share count alone
                pass
        except Exception:
            pass

    def _read_log_events(self) -> None:
        if not self.log_path.is_file():
            return
        try:
            size = self.log_path.stat().st_size
            if size < self._log_pos:
                self._log_pos = 0
            if size == self._log_pos:
                return
            with open(self.log_path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(self._log_pos)
                chunk = f.read()
                self._log_pos = f.tell()
        except Exception:
            return
        for line in chunk.splitlines():
            low = line.lower()
            # Novi job / diff / reconnected work
            if any(
                k in low
                for k in (
                    "new job",
                    "job received",
                    "last job:",
                    "difficulty set",
                    "diff:",
                    "connected to",
                )
            ):
                # Avoid reconnect spam: only race on clear job/diff signals
                if "reconnect" in low:
                    continue
                key = line.strip()[-140:]
                if key != self._last_job_key:
                    self._last_job_key = key
                    self._jobs_seen += 1
                    self._enter_race(line)
            if "share accepted" in low:
                self._shares += 1
                ms = None
                m = self._ms_re.search(line)
                if m:
                    ms = int(m.group(1))
                    self._last_share_ms = ms
                hard = ms is not None and ms >= 400
                if hard:
                    self._hard_shares += 1
                    msg = (
                        f"AI TEŽAK SHARE (kandidat) · {ms}ms · "
                        f"session hard={self._hard_shares} total={self._shares}"
                    )
                    self.on_log(msg)
                    self.on_notify("Aura AI · kandidat", f"Težak share {ms}ms — nastavljam lov")
                else:
                    self.on_log(
                        f"AI share OK"
                        + (f" · {ms}ms" if ms is not None else "")
                        + f" · ukupno {self._shares}"
                    )
            if "block" in low and any(
                k in low for k in ("found", "mined", "yes!", "detected", "solved")
            ):
                self.on_log(f"AI BLOK SIGNAL · {line[:200]}")
                self.on_notify("Aura AI · BLOK", line[:160])

    def _enter_race(self, line: str) -> None:
        # Duži race prozor — 45s (prije 25s)
        self._race_until = time.time() + 45
        self.on_log(
            f"AI LOVI NOVI JOB/BLOK · race 45s · boost={self._boost} · {line[:110]}"
        )
        self.on_notify("Aura AI · race", f"Novi job — boost {self._boost}, lov 45s")
        self._nudge_gpu_race(force=True)
        # Ako nismo na max boostu i temp dozvoljava — digne boost odmah
        gpu = _nvidia()
        temp = gpu.get("temp")
        if self._boost < 8 and (temp is None or temp < 80):
            self._set_boost(min(8, self._boost + 1), restart=False)
            self.on_log(f"AI race boost bump → {self._boost} (bez restarta)")

    def _nudge_gpu_race(self, force: bool = False) -> None:
        try:
            kw: dict = dict(
                stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL, timeout=4
            )
            if hasattr(subprocess, "CREATE_NO_WINDOW"):
                kw["creationflags"] = subprocess.CREATE_NO_WINDOW
            subprocess.run(["nvidia-smi", "-pm", "1"], **kw)
            gpu = _nvidia()
            idx = int(gpu.get("index") or 0)
            pl = gpu.get("plimit")
            if pl and pl < 120:
                target = int(min(max(pl + (8 if force else 5), pl), 150))
                subprocess.run(
                    ["nvidia-smi", "-i", str(idx), "-pl", str(target)], **kw
                )
                if force or self._tick % 5 == 0:
                    self.on_log(f"AI race · GPU{idx} power → {target}W")
        except Exception:
            pass

    def _step(self) -> None:
        api = _srb_api(21550)
        stats = self.get_stats() or {}
        rate = float(stats.get("hashrate_hs") or 0)
        try:
            for a0 in api.get("algorithms") or []:
                if not isinstance(a0, dict):
                    continue
                for k in ("hashrate", "hashrate_1min", "total_hashrate", "hashrate_60s"):
                    hr = a0.get(k)
                    if isinstance(hr, (int, float)) and hr > rate:
                        rate = float(hr)
        except Exception:
            pass

        gpu = _nvidia()
        temp = gpu.get("temp")
        util = gpu.get("util")
        racing = time.time() < self._race_until

        if rate > self._best_rate * 1.015 and rate > 0:
            self._best_rate = rate
            self._best_boost = self._boost
            cfg = self._load_cfg()
            cfg["pearl_ai_best_rate"] = self._best_rate
            cfg["pearl_ai_best_boost"] = self._best_boost
            if rate > float(cfg.get("hs_peak") or 0):
                cfg["hs_peak"] = rate
            self._save_cfg(cfg)
            if rate >= 1e12:
                pretty, unit = rate / 1e12, "TH/s"
            elif rate >= 1e9:
                pretty, unit = rate / 1e9, "GH/s"
            else:
                pretty, unit = rate / 1e6, "MH/s"
            self.on_log(
                f"AI naučio bolje · {pretty:.2f} {unit} @ boost {self._boost}"
                + (f" · {temp:.0f}°C" if temp is not None else "")
            )

        if temp is not None and temp >= 85:
            if self._boost > 2:
                self.on_log(f"AI hladi · {temp:.0f}°C → boost down")
                self._set_boost(self._boost - 1, restart=True)
            return

        if racing:
            if self._tick % 4 == 0:
                self.on_log(
                    f"AI RACE · util={util or '?'}% temp={temp or '?'}°C "
                    f"shares={self._shares} hard={self._hard_shares} jobs={self._jobs_seen}"
                )
                self._nudge_gpu_race(force=False)
            return

        if rate > 0 and self._last_rate > 0:
            gain = (rate - self._last_rate) / max(self._last_rate, 1.0)
            if abs(gain) < 0.035:
                self._stable += 1
            else:
                self._stable = 0
        self._last_rate = rate

        cool = temp is None or temp < 78
        if self._stable >= 2 and cool and self._boost < 8:
            self.on_log(f"AI traži brži lov · boost {self._boost} → {self._boost + 1}")
            self._set_boost(self._boost + 1, restart=True)
            self._stable = 0
            return

        if (
            self._best_rate > 0
            and rate > 0
            and rate < self._best_rate * 0.88
            and self._boost != self._best_boost
        ):
            self.on_log(f"AI vraća najbolji boost {self._best_boost}")
            self._set_boost(self._best_boost, restart=True)

        if self._tick % 15 == 0:
            acc = int(stats.get("accepted") or self._shares or 0)
            self.on_log(
                f"AI status · jobs={self._jobs_seen} shares={self._shares}/{acc} "
                f"hard={self._hard_shares} boost={self._boost} · lov aktivan"
            )

    def _set_boost(self, level: int, restart: bool = False) -> None:
        level = max(1, min(8, int(level)))
        prev = self._boost
        self._boost = level
        cfg = self._load_cfg()
        cfg["pearl_ai_boost"] = level
        cfg["ai_intensity"] = level
        cfg["hs_boost"] = float(level)
        cfg["pearl_ai"] = True
        self._save_cfg(cfg)
        if restart and self.restart_miner and level != prev:
            try:
                self.on_log(f"AI primjenjuje boost={level} (restart minera)")
                self.restart_miner()
            except Exception as exc:
                self.on_log(f"AI restart: {exc}")
