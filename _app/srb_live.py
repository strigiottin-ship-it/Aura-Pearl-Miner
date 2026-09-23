# -*- coding: utf-8 -*-
"""Read live stats from SRBMiner HTTP API (port 21550)."""
from __future__ import annotations

import json
import urllib.request
from typing import Any


def fetch_srb(port: int = 21550) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}", timeout=2) as r:
            return json.loads(r.read().decode("utf-8", errors="replace"))
    except Exception:
        return {}


def summarize_srb(data: dict[str, Any] | None = None) -> dict[str, Any]:
    data = data if data is not None else fetch_srb()
    out: dict[str, Any] = {
        "ok": bool(data),
        "hashrate_hs": 0.0,
        "hashrate": "0 H/s",
        "accepted": 0,
        "rejected": 0,
        "total": 0,
        "uptime": 0,
        "pool": "",
        "wallet": "",
        "difficulty": None,
        "latency_ms": None,
        "last_job_sec": None,
        "temp": None,
        "power": None,
        "fan": None,
        "core_clock": None,
        "mem_clock": None,
        "gpu_name": "",
        "algo": "pearlhash",
        "engine": "Aura PearlPow AI",
    }
    if not data:
        return out
    out["uptime"] = int(data.get("mining_time") or 0)
    algos = data.get("algorithms") or []
    a0 = algos[0] if algos and isinstance(algos[0], dict) else {}
    pool = a0.get("pool") if isinstance(a0.get("pool"), dict) else {}
    shares = a0.get("shares") if isinstance(a0.get("shares"), dict) else {}
    hr = a0.get("hashrate") if isinstance(a0.get("hashrate"), dict) else {}
    hs = float(hr.get("1min") or 0)
    if not hs and isinstance(hr.get("gpu"), dict):
        hs = float(hr["gpu"].get("total") or 0)
    out["hashrate_hs"] = hs
    out["hashrate"] = _fmt(hs)
    out["accepted"] = int(shares.get("accepted") or 0)
    out["rejected"] = int(shares.get("rejected") or 0)
    out["total"] = int(shares.get("total") or (out["accepted"] + out["rejected"]))
    out["pool"] = str(pool.get("pool") or "")
    out["wallet"] = str(pool.get("wallet") or "")
    out["difficulty"] = pool.get("difficulty")
    out["latency_ms"] = pool.get("latency")
    out["last_job_sec"] = pool.get("last_job_received")
    out["algo"] = str(a0.get("name") or "pearlhash")
    gpus = data.get("gpu_devices") or []
    g0 = gpus[0] if gpus and isinstance(gpus[0], dict) else {}
    # prefer nvidia entry
    for g in gpus:
        if isinstance(g, dict) and "nvidia" in str(g.get("vendor") or "").lower():
            g0 = g
            break
    out["temp"] = g0.get("temperature")
    out["power"] = g0.get("asic_power")
    out["fan"] = g0.get("fan_speed_percent")
    out["core_clock"] = g0.get("core_clock")
    out["mem_clock"] = g0.get("memory_clock")
    model = str(g0.get("model") or "").replace("_", " ")
    out["gpu_name"] = model.title() if model else ""
    return out


def _fmt(hs: float) -> str:
    n = float(hs or 0)
    for unit, div in (("TH/s", 1e12), ("GH/s", 1e9), ("MH/s", 1e6), ("KH/s", 1e3)):
        if n >= div:
            return f"{n / div:.2f} {unit}"
    return f"{n:.0f} H/s"
