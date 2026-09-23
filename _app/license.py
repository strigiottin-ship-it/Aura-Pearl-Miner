# -*- coding: utf-8 -*-
from __future__ import annotations
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

DONATE_BTC = "YOUR_BTC_WALLET"


def _license_paths() -> list[Path]:
    home = Path(os.path.expandvars(r"%USERPROFILE%")) if os.name == "nt" else Path.home()
    here = Path(__file__).resolve().parent
    roots = [
        here.parent / "license.json",
        here / "license.json",
        home / "AppData" / "Roaming" / "Aura" / "license.json",
        home / "AppData" / "Roaming" / "HashStart" / "license.json",
    ]
    return roots


@dataclass
class LicenseInfo:
    ok: bool = True
    email: str = ""
    plan: str = "owner"
    expiry: int = 4102444800
    label: str = "Aura · owner"

    @property
    def valid(self) -> bool:
        return self.ok


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def valid_email(email: str) -> bool:
    email = normalize_email(email)
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))


def load_license() -> LicenseInfo:
    data = {}
    for p in _license_paths():
        try:
            if p.is_file():
                data = json.loads(p.read_text(encoding="utf-8"))
                break
        except Exception:
            continue
    email = normalize_email(str(data.get("email") or "strigiottin@gmail.com"))
    plan = str(data.get("plan") or "owner")
    expiry = int(data.get("expiry") or 4102444800)
    ok = True
    label = f"Aura · {plan}" if email else "Aura"
    if email:
        label = f"{email} · {plan}"
    return LicenseInfo(ok=ok, email=email, plan=plan, expiry=expiry, label=label)


def activate(email: str, key: str = "") -> dict:
    email = normalize_email(email)
    if not valid_email(email):
        return {"ok": False, "error": "Email nije validan"}
    info = {"email": email, "plan": "owner", "expiry": 4102444800}
    home = Path(os.path.expandvars(r"%USERPROFILE%")) if os.name == "nt" else Path.home()
    for folder in (home / "AppData" / "Roaming" / "Aura", home / "AppData" / "Roaming" / "HashStart"):
        try:
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "license.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
        except Exception:
            pass
    try:
        Path(__file__).resolve().parent.parent.joinpath("license.json").write_text(
            json.dumps(info, indent=2), encoding="utf-8"
        )
    except Exception:
        pass
    return {"ok": True, "license": info}


def logout() -> None:
    for p in _license_paths():
        try:
            if p.is_file() and p.name == "license.json" and "Roaming" not in str(p):
                p.unlink()
        except Exception:
            pass
