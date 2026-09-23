# -*- coding: utf-8 -*-
"""Aura AI Motor — mathematical GPU optimization loop for desktop mining.

Learns best OpenCL intensity from live hashrate + nvidia-smi telemetry.
Does NOT invent blocks or fake TH/s; pushes real GPU work harder when safe.
"""
from __future__ import annotations

import json
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Callable


def _nvidia() -> dict:
    try:
        kw = dict(stderr=subprocess.DEVNULL, text=True, timeout=3)
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            kw["creationflags"] = subprocess.CREATE_NO_WINDOW
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=temperature.gpu,utilization.gpu,power.draw,clocks.gr,clocks.mem",
                "--format=csv,noheader,nounits",
            ],
            **kw,
        )
        parts = [p.strip() for p in out.strip().splitlines()[0].split(",")]
        def f(i):
            try:
                return float(parts[i])
            except Exception:
                return None
        return {"temp": f(0), "util": f(1), "power": f(2), "core": f(3), "mem": f(4)}
    except Exception:
        return {}


class AuraAI:
    """Background optimizer attached to MinerEngine + config."""

    def __init__(
        self,
        config_path: Path,
        on_log: Callable[[str], None] | None = None,
        get_stats: Callable[[], dict] | None = None,
    ) -> None:
        self.config_path = Path(config_path)
        self.on_log = on_log or (lambda _m: None)
        self.get_stats = get_stats or (lambda: {})
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._intensity = 4
        self._best_rate = 0.0
        self._best_intensity = 4
        self._last_rate = 0.0
        self._stable = 0
        self._tick = 0

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
        self._intensity = int(cfg.get("ai_intensity") or cfg.get("hs_boost") or 4)
        self._best_intensity = int(cfg.get("ai_best_intensity") or self._intensity)
        self._best_rate = float(cfg.get("ai_best_rate") or 0)
        self._save_cfg(cfg)
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="AuraAI", daemon=True)
        self._thread.start()
        self.on_log(
            f"Aura AI motor ON · start intensity={self._intensity} "
            f"(uči optimalnu snagu GPU-a, ne laže blokove)"
        )
        # Apply initial intensity
        self._apply_intensity(self._intensity)

    def stop(self) -> None:
        self._stop.set()
        self.on_log("Aura AI motor OFF")

    def _apply_intensity(self, level: int) -> None:
        level = max(1, min(8, int(level)))
        self._intensity = level
        try:
            from sha256_gpu import bump_all_gpus, get_gpu

            # set absolute by repeated set_intensity
            g = get_gpu(0)
            note = g.set_intensity(level)
            self.on_log(f"AI → {note}")
        except Exception as exc:
            try:
                from engine import bump_gpu_intensity

                # relative bumps toward target
                notes = bump_gpu_intensity(1 if level >= 5 else -1)
                for n in notes:
                    self.on_log(f"AI · {n}")
            except Exception as exc2:
                self.on_log(f"AI intensity: {exc} / {exc2}")
        cfg = self._load_cfg()
        cfg["ai_intensity"] = level
        cfg["auto_ai"] = True
        # hs_boost kept as soft multiplier display hint (1..8)
        cfg["hs_boost"] = float(level)
        self._save_cfg(cfg)

    def _loop(self) -> None:
        # Warm-up
        time.sleep(8)
        while not self._stop.is_set():
            self._tick += 1
            try:
                self._step()
            except Exception as exc:
                self.on_log(f"AI step error: {exc}")
            self._stop.wait(12)

    def _step(self) -> None:
        stats = self.get_stats() or {}
        rate = float(stats.get("hashrate_hs") or 0)
        gpu = _nvidia()
        temp = gpu.get("temp")
        util = gpu.get("util")
        power = gpu.get("power")

        if rate > self._best_rate * 1.02:
            self._best_rate = rate
            self._best_intensity = self._intensity
            cfg = self._load_cfg()
            cfg["ai_best_rate"] = self._best_rate
            cfg["ai_best_intensity"] = self._best_intensity
            if rate > float(cfg.get("hs_peak") or 0):
                cfg["hs_peak"] = rate
            self._save_cfg(cfg)
            self.on_log(
                f"AI naučio bolje · {rate/1e6:.1f} MH/s @ intensity {self._intensity}"
                + (f" · {temp:.0f}°C" if temp is not None else "")
            )

        # Thermal guard
        if temp is not None and temp >= 83:
            if self._intensity > 1:
                self.on_log(f"AI hladi · temp {temp:.0f}°C → intensity down")
                self._apply_intensity(self._intensity - 1)
            self._stable = 0
            self._last_rate = rate
            return

        if temp is not None and temp >= 78 and self._intensity >= 7:
            self.on_log(f"AI drži · temp {temp:.0f}°C, ne ide više gore")
            self._last_rate = rate
            return

        # Plateau detection → try more intensity if cool
        if rate > 0 and self._last_rate > 0:
            gain = (rate - self._last_rate) / max(self._last_rate, 1.0)
            if abs(gain) < 0.03:
                self._stable += 1
            else:
                self._stable = 0
        self._last_rate = rate

        cool_ok = temp is None or temp < 75
        util_ok = util is None or util >= 85 or util < 50  # low util → room to push work
        if self._stable >= 2 and cool_ok and self._intensity < 8:
            # Explore upward
            self.on_log(
                f"AI traži više snage · plateau @ {rate/1e6:.1f} MH/s → intensity {self._intensity + 1}"
            )
            self._apply_intensity(self._intensity + 1)
            self._stable = 0
            return

        # If we went too high and rate dropped >8%, revert to best
        if (
            self._best_rate > 0
            and rate > 0
            and rate < self._best_rate * 0.92
            and self._intensity != self._best_intensity
        ):
            self.on_log(
                f"AI vraća best · {self._best_intensity} ({self._best_rate/1e6:.1f} MH/s)"
            )
            self._apply_intensity(self._best_intensity)
            self._stable = 0

        if self._tick % 5 == 0:
            bits = [f"AI watch · {rate/1e6:.1f} MH/s · I={self._intensity}"]
            if temp is not None:
                bits.append(f"{temp:.0f}°C")
            if util is not None:
                bits.append(f"util {util:.0f}%")
            if power is not None:
                bits.append(f"{power:.0f}W")
            self.on_log(" · ".join(bits))
