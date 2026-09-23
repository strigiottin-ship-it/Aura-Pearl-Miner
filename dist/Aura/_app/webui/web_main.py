# -*- coding: utf-8 -*-
"""Aura Web UI — Settings/Workers/Stats aligned with Gupax/NiceHash/HiveOS."""
from __future__ import annotations

import ctypes
import json
import webbrowser
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

if sys.platform == "win32":
    try:
        ctypes.windll.kernel32.FreeConsole()
    except Exception:
        pass

def _aura_paths():
    """Resolve app + webui dirs for both script and frozen (PyInstaller) runs."""
    if getattr(sys, "frozen", False):
        # Onedir: exe beside _internal; writable config next to exe
        exe_dir = Path(sys.executable).resolve().parent
        meipass = Path(getattr(sys, "_MEIPASS", exe_dir))
        # Prefer bundled _app next to exe (if we copy layout), else _MEIPASS
        if (exe_dir / "_app").is_dir():
            app_dir = exe_dir / "_app"
            webui = app_dir / "webui"
        elif (meipass / "_app").is_dir():
            app_dir = meipass / "_app"
            webui = app_dir / "webui"
        else:
            app_dir = meipass
            webui = meipass / "webui" if (meipass / "webui").is_dir() else meipass
        config_dir = exe_dir  # writable
    else:
        webui = Path(__file__).resolve().parent
        app_dir = webui.parent
        # Writable config lives in Aura root (next to START.bat), not inside _app
        config_dir = app_dir.parent if app_dir.name == "_app" else app_dir
    return app_dir, webui, config_dir


APP_DIR, WEBUI, _CONFIG_DIR = _aura_paths()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
# Also allow importing from parent of _app when frozen layout differs
_parent = APP_DIR.parent if APP_DIR.name == "_app" else APP_DIR
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

import webview

from coins import (
    ORDER, PAYOUT_COINS, get_coin, labels, worker_login,
    unmineable_address_url, unmineable_coin, validate_payout_address,
)
from engine import MinerEngine, format_rate
from license import load_license
from market import fetch_unmineable_payout
from aura_ai import AuraAI
from pearl_motor import PearlMotor

CONFIG_PATH = _CONFIG_DIR / "config.json"


def load_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_config(cfg: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


def _gpu_telemetry() -> list[dict]:
    """NiceHash-style device status via nvidia-smi when available."""
    try:
        cmd = [
            "nvidia-smi",
            "--query-gpu=name,temperature.gpu,utilization.gpu,power.draw,fan.speed",
            "--format=csv,noheader,nounits",
        ]
        # Hide black console flash on Windows (CREATE_NO_WINDOW)
        kwargs = dict(stderr=subprocess.DEVNULL, text=True, timeout=3)
        if sys.platform == "win32":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
            try:
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = 0
                kwargs["startupinfo"] = si
            except Exception:
                pass
        out = subprocess.check_output(cmd, **kwargs)
        rows = []
        for i, line in enumerate(out.strip().splitlines()):
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 4:
                continue

            def num(x):
                try:
                    return float(re.sub(r"[^0-9.]+", "", x) or 0)
                except Exception:
                    return None

            rows.append({
                "name": parts[0] or f"GPU-{i}",
                "temp": num(parts[1]),
                "util": num(parts[2]),
                "power": num(parts[3]),
                "fan": num(parts[4]) if len(parts) > 4 else None,
            })
        return rows
    except Exception:
        return []


class Api:
    def __init__(self) -> None:
        self.cfg = load_config()
        self._status = "Ready"
        self._logs: list[str] = []
        self._started_at = 0.0
        self._pool_bal_cache = None
        self._pool_bal_at = 0.0
        self._lock = threading.Lock()
        self.engine = MinerEngine(
            APP_DIR,
            on_status=self._on_status,
            on_stats=self._on_stats,
            on_log=self._on_log,
        )
        self._last_stats = dict(self.engine.stats)
        self._gpu_cache: list[dict] = []
        self._gpu_ts = 0.0
        self.ai = AuraAI(
            CONFIG_PATH,
            on_log=self._on_log,
            get_stats=lambda: self._last_stats,
        )
        self.pearl = PearlMotor(
            _parent if APP_DIR.name == "_app" else APP_DIR,
            on_log=self._on_log,
            on_stats=self._on_stats,
        )

    def _on_status(self, msg: str) -> None:
        self._status = str(msg)

    def _on_stats(self, stats: dict) -> None:
        self._last_stats = dict(stats or {})
        try:
            rate = float(self._last_stats.get("hashrate_hs") or 0)
            cfg = load_config()
            peak = float(cfg.get("hs_peak") or 0)
            if rate > peak:
                cfg["hs_peak"] = rate
                save_config(cfg)
        except Exception:
            pass

    def _on_log(self, line: str) -> None:
        self._logs.insert(0, str(line))
        self._logs = self._logs[:100]

    def _gpus(self) -> list[dict]:
        now = time.time()
        if now - self._gpu_ts > 5.0:
            self._gpu_cache = _gpu_telemetry()
            self._gpu_ts = now
        return self._gpu_cache

    def _endpoints(self) -> dict:
        out = {}
        for code in ORDER:
            try:
                c = get_coin(code)
            except Exception:
                continue
            out[code] = {
                "pool": list(c.get("pool") or ("", "")),
                "solo": list(c.get("solo") or ("", "")),
            }
        return out

    def _coin_meta(self) -> dict:
        out = {}
        for code in ORDER:
            try:
                c = get_coin(code)
            except Exception:
                continue
            out[code] = {
                "algo": c.get("algo") or "",
                "password": c.get("password") or "x",
                "pool_login": c.get("pool_login") or "",
                "solo_login": c.get("solo_login") or "",
                "pool_miner": c.get("pool_miner") or "",
                "address_hint": c.get("address_hint") or "",
                "address_label": c.get("address_label") or "",
            }
        return out

    def _workers(self, mining: bool, host: str, port: str, algo: str, rate_s: str) -> list:
        rows = []
        gpus = self._gpus()
        if gpus:
            for i, g in enumerate(gpus):
                rows.append({
                    "name": g.get("name") or f"GPU-{i}",
                    "type": "NVIDIA GPU",
                    "algo": algo or "—",
                    "hashrate": rate_s if mining else "0 H/s",
                    "temp": g.get("temp"),
                    "util": g.get("util"),
                    "power": g.get("power"),
                    "active": mining,
                })
        else:
            rows.append({
                "name": "GPU-0",
                "type": "OpenCL / CUDA",
                "algo": algo or "—",
                "hashrate": rate_s if mining else "0 H/s",
                "temp": None,
                "util": None,
                "power": None,
                "active": mining,
            })

        cfg = self.cfg
        ips = [x.strip() for x in str(cfg.get("asic_ips") or "").split(",") if x.strip()]
        for ip in ips:
            rows.append({
                "name": ip,
                "type": "ASIC / LAN",
                "algo": algo or "—",
                "hashrate": "—",
                "temp": None,
                "util": None,
                "power": None,
                "active": False,
            })

        nm = cfg.get("nerdminer") if isinstance(cfg.get("nerdminer"), dict) else {}
        if nm.get("host") or nm.get("active"):
            rows.append({
                "name": str(nm.get("host") or "USB"),
                "type": "NerdMiner USB",
                "algo": "sha256d",
                "hashrate": str(nm.get("hashrate") or "—"),
                "temp": None,
                "util": None,
                "power": None,
                "active": bool(nm.get("active")),
            })
        return rows


    def _live_pool_balance(self, cfg: dict) -> dict:
        """Live unMineable balance for payout wallet (BTC while PearlPow)."""
        now = time.time()
        if self._pool_bal_cache is not None and now - float(self._pool_bal_at or 0) < 45:
            return dict(self._pool_bal_cache)
        wallets = cfg.get("wallets") if isinstance(cfg.get("wallets"), dict) else {}
        pay = str(cfg.get("payout") or "BTC").upper()
        if pay in ("NATIVE", "PRL", ""):
            pay = "BTC"
        addr = str(wallets.get(pay) or wallets.get("BTC") or "").strip()
        out = {"coin": pay, "address": addr, "balance": None, "threshold": None, "ok": False}
        if not addr:
            self._pool_bal_cache = out
            self._pool_bal_at = now
            return out
        try:
            data = fetch_unmineable_payout(pay, addr)
            if data:
                out["balance"] = data.get("balance")
                raw = data.get("raw") if isinstance(data.get("raw"), dict) else {}
                nested = raw.get("data") if isinstance(raw.get("data"), dict) else raw
                if isinstance(nested, dict):
                    out["threshold"] = nested.get("payment_threshold")
                    if out["balance"] is None:
                        out["balance"] = nested.get("balance") or nested.get("balance_payable")
                out["ok"] = out["balance"] is not None
        except Exception:
            pass
        self._pool_bal_cache = out
        self._pool_bal_at = now
        return out

    def get_state(self) -> dict:
        cfg = load_config()
        self.cfg = cfg
        coin = str(cfg.get("coin") or "BTC")
        wallets = cfg.get("wallets") if isinstance(cfg.get("wallets"), dict) else {}
        addr = str(wallets.get(coin) or cfg.get("address") or "")
        stats = dict(self._last_stats)
        mining = bool(self.engine.is_running() or getattr(self, "pearl", None) and self.pearl.is_running())
        if getattr(self, "pearl", None) and self.pearl.is_running():
            stats.update(self.pearl.stats)
            self._last_stats.update(self.pearl.stats)
        rate_hs = float(stats.get("hashrate_hs") or 0)
        peak = float(cfg.get("hs_peak") or 0)
        host = str(cfg.get("host") or "")
        port = str(cfg.get("port") or "")
        mode = "solo" if cfg.get("mode") == "solo" else "pool"

        algo = ""
        pool_miner = ""
        try:
            c = get_coin(coin)
            algo = str(c.get("algo") or "")
            pool_miner = str(c.get("pool_miner") or "")
        except Exception:
            pass

        coins = []
        for code in ORDER:
            try:
                c = get_coin(code)
                if c.get("mineable"):
                    coins.append({"code": code, "label": c.get("label") or labels.get(code, code)})
            except Exception:
                continue
        if not coins:
            coins = [{"code": coin, "label": coin}]

        pool = self._live_pool_balance(cfg)
        pay_c = str(pool.get("coin") or "BTC")
        bal_f = None
        try:
            if pool.get("balance") is not None:
                bal_f = float(pool.get("balance"))
        except Exception:
            bal_f = None
        thr = pool.get("threshold")
        pile = cfg.get("session_pile") if isinstance(cfg.get("session_pile"), dict) else {}
        usd = float(pile.get("usd") or 0)
        eur = float(pile.get("eur") or 0)
        hashes = float(pile.get("hashes") or 0)
        if bal_f is not None:
            thr_s = str(thr) if thr is not None else "?"
            session_line = f"{pay_c} na poolu: {bal_f:.8f} (isplata od {thr_s} {pay_c})"
            session_by_coin = f"{pay_c}: {bal_f:.8f} (unMineable live)"
        else:
            session_line = f"${usd:.6f} · €{eur:.6f} (lokalna procjena)"
            by_coin = pile.get("by_coin") if isinstance(pile.get("by_coin"), dict) else {}
            session_by_coin = " · ".join(
                f"{k}: {float(v):.8g}" for k, v in sorted(by_coin.items()) if float(v or 0) > 0
            )
        if hashes >= 1e12:
            hashes_line = f"{hashes/1e12:.2f} TH total"
        elif hashes >= 1e9:
            hashes_line = f"{hashes/1e9:.2f} GH total"
        elif hashes >= 1e6:
            hashes_line = f"{hashes/1e6:.2f} MH total"
        else:
            hashes_line = f"{hashes:.0f} H total"

            f"{k}: {float(v):.8g}" for k, v in sorted(by_coin.items()) if float(v or 0) > 0
        )

        uptime = time.time() - self._started_at if mining and self._started_at else 0
        engine_name = str(stats.get("engine") or "GPU OpenCL")
        rate_s = stats.get("hashrate") or format_rate(rate_hs)
        acc = int(stats.get("accepted") or 0)
        rej = int(stats.get("rejected") or 0)
        if getattr(self, "pearl", None) and self.pearl.is_running():
            rate_now = stats.get("hashrate") or format_rate(rate_hs)
            hashes_line = f"{rate_now} · accepted {acc} · odbijeno {rej}"

        total = int(stats.get("total") or (acc + rej))

        gpus = self._gpus()
        if gpus:
            g0 = gpus[0]
            gpu_name = g0.get("name") or "GPU"
            gpu_detail = f"{g0.get('temp')}°C · {g0.get('util')}% · {g0.get('power')} W"
        else:
            gpu_name = "GPU"
            gpu_detail = "nvidia-smi n/a"

        nm = cfg.get("nerdminer") if isinstance(cfg.get("nerdminer"), dict) else {}
        wn = str(cfg.get("worker_name") or "").strip()
        try:
            login_auto = worker_login(
                get_coin(coin), addr, mode,
                payout=str(cfg.get("payout") or "NATIVE"),
                payout_tag=str(cfg.get("payout_tag") or ""),
            )
        except Exception:
            login_auto = addr

        worker_conn = (
            f"{'Mining' if mining else 'Idle'} · login {wn or login_auto} @ {host}:{port}"
            f" · {pool_miner or 'pool'} · {algo or 'algo'}"
        )

        return {
            "running": mining,
            "hashrate": rate_hs,
            "hashrate_s": rate_s,
            "peak": peak,
            "accepted": acc,
            "rejected": rej,
            "total_shares": total,
            "uptime": uptime,
            "coin": coin,
            "mode": mode,
            "host": host,
            "port": port,
            "wallet": addr,
            "algo": algo,
            "engine": engine_name,
            "coins": coins,
            "endpoints": self._endpoints(),
            "coin_meta": self._coin_meta(),
            "workers": self._workers(mining, host, port, algo, rate_s),
            "worker_conn": worker_conn,
            "session_line": session_line,
            "hashes_line": hashes_line,
            "session_by_coin": session_by_coin,
            "gpu_name": gpu_name,
            "gpu_detail": gpu_detail,
            "log": list(reversed(self._logs[:60])),
            "status": self._status,
            "email": getattr(load_license(), "email", "") or "",
            "settings": {
                "coin": coin,
                "mode": mode,
                "host": host,
                "port": port,
                "wallet": addr,
                "wallets": dict(cfg.get("wallets") or {}),
                "withdraw_addresses": dict(cfg.get("withdraw_addresses") or {}),
                "worker_name": wn,
                "pool_password": str(cfg.get("pool_password") or ""),
                "payout": str(cfg.get("payout") or "NATIVE"),
                "payout_tag": str(cfg.get("payout_tag") or ""),
                "payout_target": str(cfg.get("payout_target") or ""),
                "asic_ips": str(cfg.get("asic_ips") or ""),
                "extra_subnet": str(cfg.get("extra_subnet") or ""),
                "nm_host": str(nm.get("host") or ""),
                "nm_hashrate": str(nm.get("hashrate") or ""),
                "nm_wifi": str(nm.get("wifi_ssid") or nm.get("ssid") or ""),
                "nm_active": bool(nm.get("active")),
            },
        }

    def toggle_mining(self, coin_code: str = "") -> dict:
        with self._lock:
            if self.engine.is_running() or (getattr(self, "pearl", None) and self.pearl.is_running()):
                try:
                    self.engine.stop()
                except Exception as exc:
                    self._on_log(f"Stop error: {exc}")
                    return {"ok": False, "error": str(exc), "running": False}
                self._started_at = 0.0
                self._status = "Stopped"
                try:
                    self.ai.stop()
                except Exception:
                    pass
                try:
                    self.pearl.stop()
                except Exception:
                    pass
                self._on_log("Stopped mining")
                return {"ok": True, "running": False}

            cfg = load_config()
            code = (coin_code or cfg.get("coin") or "BTC").strip().upper()
            try:
                coin = dict(get_coin(code))
            except Exception as exc:
                return {"ok": False, "error": str(exc)}
            if not coin.get("mineable"):
                return {"ok": False, "error": coin.get("note") or "Coin nije mineable"}

            # HiveOS-style pool password override
            pw = str(cfg.get("pool_password") or "").strip()
            if pw:
                coin["password"] = pw

            wallets = cfg.get("wallets") if isinstance(cfg.get("wallets"), dict) else {}
            address = str(wallets.get(code) or cfg.get("address") or "").strip()
            if not address:
                return {"ok": False, "error": "Nema wallet adrese za ovaj coin"}

            host = str(cfg.get("host") or "").strip()
            port = str(cfg.get("port") or "3333").strip()
            mode = "solo" if cfg.get("mode") == "solo" else "pool"
            if not host:
                pair = coin.get("solo" if mode == "solo" else "pool")
                if pair:
                    host, port = str(pair[0]), str(pair[1])
                    cfg["host"], cfg["port"] = host, port
            if not host:
                return {"ok": False, "error": "Nema pool hosta"}

            payout = str(cfg.get("payout") or "NATIVE")
            payout_tag = str(cfg.get("payout_tag") or "")
            login = str(cfg.get("worker_name") or "").strip() or None
            asic_ips = [x.strip() for x in str(cfg.get("asic_ips") or "").split(",") if x.strip()]

            cfg["coin"] = code
            save_config(cfg)
            self.cfg = cfg
            self._status = "Starting…"
            try:
                algo = str(coin.get("algo") or "")
                if code == "PRL" or algo == "pearlpow":
                    worker = str(cfg.get("worker_name") or "Aura").strip() or "Aura"
                    btc_addr = str(wallets.get("BTC") or "").strip()
                    pay = str(payout or "NATIVE").strip().upper()
                    pay_addr = btc_addr if pay in ("BTC", "NATIVE") or not address.lower().startswith("prl1") else address
                    pay_coin = "BTC" if not address.lower().startswith("prl1") else (pay if pay not in ("NATIVE", "") else "PRL")
                    if not address.lower().startswith("prl1") and btc_addr:
                        self._on_log("PRL adresa nije prl1… — PearlPow pool ide na BTC payout (unMineable)")
                        pay_coin, pay_addr = "BTC", btc_addr
                    self.pearl.start(address, host, int(port), worker=worker, payout_coin=pay_coin, payout_address=pay_addr)
                    self._started_at = time.time()
                    self._status = "Mining"
                    self._on_log(f"Started PRL PearlPow AI {host}:{port}")
                    # Pearl AI motor je SRBMiner pearlhash only — ne pokreći SHA256 OpenCL AI
                    self._on_log("Pearl AI motor: SRBMiner pearlhash only (SHA256 AI preskočen)")
                    return {"ok": True, "running": True}
                self.engine.start(
                    address=address,
                    host=host,
                    port=int(port),
                    coin=coin,
                    mode=mode,
                    payout=payout,
                    payout_tag=payout_tag,
                    login=login,
                    asic_ips=asic_ips or None,
                )
                self._started_at = time.time()
                self._status = "Mining"
                self._on_log(f"Started {code} {mode} {host}:{port}")
                try:
                    self.ai.start()
                except Exception as ai_exc:
                    self._on_log(f"AI start: {ai_exc}")
                return {"ok": True, "running": True}
            except Exception as exc:
                self._status = "Error"
                self._on_log(f"Start error: {exc}")
                return {"ok": False, "error": str(exc), "running": False}

    def set_coin(self, coin: str) -> dict:
        coin = (coin or "").strip().upper()
        if not coin:
            return {"ok": False}
        cfg = load_config()
        cfg["coin"] = coin
        mode = "solo" if cfg.get("mode") == "solo" else "pool"
        try:
            c = get_coin(coin)
            pair = c.get("solo" if mode == "solo" else "pool")
            if pair:
                cfg["host"], cfg["port"] = str(pair[0]), str(pair[1])
        except Exception:
            pass
        save_config(cfg)
        self.cfg = cfg
        self._on_log(f"Coin → {coin}")
        return {"ok": True}

    def save_settings(self, payload: dict) -> dict:
        try:
            cfg = load_config()
            coin = (payload.get("coin") or cfg.get("coin") or "BTC").strip().upper()
            mode = (payload.get("mode") or "pool").strip().lower()
            if mode not in ("pool", "solo"):
                mode = "pool"
            host = (payload.get("host") or "").strip()
            port = str(payload.get("port") or "").strip()
            wallet = (payload.get("wallet") or "").strip()
            worker_name = (payload.get("worker_name") or "").strip()
            pool_password = (payload.get("pool_password") or "").strip()
            payout = (payload.get("payout") or "NATIVE").strip() or "NATIVE"
            payout_tag = (payload.get("payout_tag") or "").strip()
            payout_target = (payload.get("payout_target") or "").strip()
            asic_ips = (payload.get("asic_ips") or "").strip()
            extra_subnet = (payload.get("extra_subnet") or "").strip()

            if not host:
                try:
                    c = get_coin(coin)
                    pair = c.get("solo" if mode == "solo" else "pool")
                    if pair:
                        host, port = str(pair[0]), str(pair[1])
                except Exception:
                    pass

            cfg["coin"] = coin
            cfg["mode"] = mode
            cfg["host"] = host
            cfg["port"] = port
            cfg["worker_name"] = worker_name
            cfg["pool_password"] = pool_password
            cfg["payout"] = payout
            cfg["payout_tag"] = payout_tag
            cfg["payout_target"] = payout_target
            cfg["asic_ips"] = asic_ips
            cfg["extra_subnet"] = extra_subnet

            # full wallets map from Settings
            if isinstance(payload.get("wallets"), dict):
                merged = dict(cfg.get("wallets") or {})
                for k, v in payload["wallets"].items():
                    merged[str(k).upper()] = str(v or "").strip()
                cfg["wallets"] = merged
                if wallet:
                    merged[coin] = wallet
                elif merged.get(coin):
                    wallet = merged[coin]
            if isinstance(payload.get("withdraw_addresses"), dict):
                wdraw = dict(cfg.get("withdraw_addresses") or {})
                for k, v in payload["withdraw_addresses"].items():
                    wdraw[str(k).upper()] = str(v or "").strip()
                cfg["withdraw_addresses"] = wdraw
            wallets = dict(cfg.get("wallets") or {})
            if wallet:
                wallets[coin] = wallet
                cfg["wallets"] = wallets
                cfg["address"] = wallet

            nm_in = payload.get("nerdminer") if isinstance(payload.get("nerdminer"), dict) else {}
            nm = dict(cfg.get("nerdminer") or {})
            if "host" in nm_in:
                nm["host"] = str(nm_in.get("host") or "")
            if "hashrate" in nm_in:
                nm["hashrate"] = str(nm_in.get("hashrate") or "")
            if "wifi_ssid" in nm_in or "ssid" in nm_in:
                ssid = str(nm_in.get("wifi_ssid") or nm_in.get("ssid") or "")
                nm["wifi_ssid"] = ssid
                nm["ssid"] = ssid
            if "active" in nm_in:
                nm["active"] = bool(nm_in.get("active"))
            cfg["nerdminer"] = nm

            save_config(cfg)
            self.cfg = cfg
            self._on_log(f"Settings saved · {coin} {mode} {host}:{port}")
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}



    def _withdraw_address(self, pay: str) -> str:
        cfg = load_config()
        pay = (pay or "BTC").upper()
        addrs = cfg.get("withdraw_addresses") if isinstance(cfg.get("withdraw_addresses"), dict) else {}
        return str(addrs.get(pay) or cfg.get("withdraw_address") or "").strip()

    def get_withdraw_state(self) -> dict:
        cfg = load_config()
        self.cfg = cfg
        raw = str(cfg.get("payout") or "BTC").upper()
        pay = (unmineable_coin(raw) or raw or "BTC").upper()
        if pay == "NATIVE" or pay not in PAYOUT_COINS:
            pay = "BTC"
        addr = self._withdraw_address(pay)
        tags = cfg.get("withdraw_dest_tags") if isinstance(cfg.get("withdraw_dest_tags"), dict) else {}
        # flat tag from withdraw_tag or dest tags WALLET
        tag = str(cfg.get("withdraw_tag") or "")
        try:
            tag = str((tags.get("WALLET") or {}).get(pay) or tag or "")
        except Exception:
            pass
        bal_text = "—"
        hint = "Zalijepi wallet i stisni POVUCI. Isplata ide kad bazen dosegne minimum (kao stari HashStart)."
        try:
            if addr:
                data = fetch_unmineable_payout(pay, addr)
                if isinstance(data, dict) and not data.get("error"):
                    bal = data.get("balance")
                    bal_text = f"{bal} {pay}" if bal is not None else "—"
                    hint = "Saldo s unMineable. POVUCI sprema adresu i pokrece zahtjev."
                elif isinstance(data, dict) and data.get("error"):
                    hint = str(data.get("error"))
        except Exception as e:
            hint = f"Saldo trenutno nije dostupan ({e}). Mozes i dalje spremiti adresu / POVUCI."
        return {
            "payout": pay,
            "address": addr,
            "tag": tag,
            "amount": str(cfg.get("withdraw_amount") or ""),
            "balance_text": bal_text,
            "hint": hint,
        }

    def set_payout_coin(self, coin: str) -> dict:
        cfg = load_config()
        coin = (coin or "BTC").strip().upper()
        if coin not in PAYOUT_COINS:
            coin = "BTC"
        cfg["payout"] = coin
        save_config(cfg)
        self.cfg = cfg
        return {"ok": True, "payout": coin}

    def open_unmineable(self, payload: dict | None = None) -> dict:
        payload = payload or {}
        pay = (payload.get("payout") or "BTC").strip().upper()
        addr = (payload.get("address") or self._withdraw_address(pay)).strip()
        if not addr:
            return {"ok": False, "error": "Nema adrese"}
        url = unmineable_address_url(pay, addr)
        if url:
            webbrowser.open(url)
            return {"ok": True, "url": url}
        return {"ok": False, "error": "Nema URL"}

    def povuci(self, payload: dict | None = None) -> dict:
        """Like old HashStart POVUCI: save wallet, log, refresh — payout when pool min reached."""
        payload = payload or {}
        cfg = load_config()
        pay = (payload.get("payout") or cfg.get("payout") or "BTC").strip().upper()
        pay = (unmineable_coin(pay) or pay).upper()
        if pay not in PAYOUT_COINS:
            return {"ok": False, "error": "Odaberi BTC / BCH / XMR / XRP"}
        addr = (payload.get("address") or "").strip()
        tag = (payload.get("tag") or "").strip()
        amount = (payload.get("amount") or "").strip()
        if not addr:
            return {"ok": False, "error": "Zalijepi wallet adresu"}
        ok, msg = validate_payout_address(pay, addr)
        if not ok:
            return {"ok": False, "error": msg or "Adresa nije validna"}
        cfg["payout"] = pay
        cfg["withdraw_address"] = addr
        addrs = dict(cfg.get("withdraw_addresses") or {})
        addrs[pay] = addr
        cfg["withdraw_addresses"] = addrs
        if tag:
            cfg["withdraw_tag"] = tag
        if amount:
            cfg["withdraw_amount"] = amount
        # also set as mining convert target style
        cfg["payout_tag"] = tag
        save_config(cfg)
        self.cfg = cfg
        self._on_log(f"POVUCI {pay} → {addr[:10]}…{addr[-4:] if len(addr)>14 else addr}")
        # Try balance after save
        bal = None
        try:
            data = fetch_unmineable_payout(pay, addr)
            if isinstance(data, dict) and not data.get("error"):
                bal = data.get("balance")
        except Exception:
            pass
        message = (
            f"Spremljeno. POVUCI {pay} na tvoj wallet. "
            "Kao u starom HashStartu — bazen salje kad dosegne minimum."
        )
        if bal is not None:
            message += f" Trenutni saldo: {bal} {pay}."
        return {"ok": True, "message": message, "balance": bal}


def _ensure_single_instance() -> bool:
    """True = nastavi (ovaj proces je vlasnik). False = vec radi, focus postojeci."""
    if sys.platform != "win32":
        return True
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32
        ERROR_ALREADY_EXISTS = 183
        mutex = kernel32.CreateMutexW(None, False, "Global\\AuraMinerUISingleInstance")
        if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            EnumWindows = user32.EnumWindows
            EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
            GetWindowTextW = user32.GetWindowTextW
            GetWindowTextLengthW = user32.GetWindowTextLengthW
            IsWindowVisible = user32.IsWindowVisible
            found = []

            def _cb(hwnd, _lparam):
                if not IsWindowVisible(hwnd):
                    return True
                n = GetWindowTextLengthW(hwnd)
                if n <= 0:
                    return True
                buf = ctypes.create_unicode_buffer(n + 1)
                GetWindowTextW(hwnd, buf, n + 1)
                if buf.value == "Aura":
                    found.append(hwnd)
                return True

            EnumWindows(EnumWindowsProc(_cb), 0)
            for hwnd in found:
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                user32.SetForegroundWindow(hwnd)
            return False
        return True
    except Exception:
        return True

def main() -> None:
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Aura.Miner")
        except Exception:
            pass
    if not _ensure_single_instance():
        return
    api = Api()
    index = (WEBUI / "index.html").as_uri()
    webview.create_window(
        "Aura",
        index,
        js_api=api,
        width=988,
        height=728,
        min_size=(900, 650),
        background_color="#0a0612",
    )
    webview.start(debug=False)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        from pathlib import Path as _P
        _P(r"C:\Users\neno\Downloads\Aura\aura_ui_crash.log").write_text(traceback.format_exc(), encoding="utf-8")
        raise
