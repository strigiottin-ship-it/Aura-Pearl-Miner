# -*- coding: utf-8 -*-
from __future__ import annotations
import json
import urllib.request
from typing import Any

WINDOWS = True
UNMINEABLE_FEE = 0.01


def fetch_unmineable_payout(coin: str, address: str) -> dict[str, Any]:
    coin = (coin or "BTC").strip().upper()
    address = (address or "").strip()
    if not address:
        return {"error": "Nema adrese"}
    urls = [
        f"https://api.unmineable.com/v4/address/{address}?coin={coin}",
        f"https://api.unmineable.com/v3/address/{address}?coin={coin}",
    ]
    last_err = None
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Aura/1.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = json.loads(resp.read().decode("utf-8", errors="replace"))
            data = raw.get("data") if isinstance(raw, dict) else None
            if isinstance(data, dict):
                bal = data.get("balance")
                if bal is None:
                    bal = data.get("balance_payable") or data.get("pending_balance")
                return {
                    "balance": bal,
                    "raw": data,
                    "coin": coin,
                    "address": address,
                }
            if isinstance(raw, dict) and "balance" in raw:
                return {"balance": raw.get("balance"), "raw": raw, "coin": coin, "address": address}
            last_err = f"Neocekivan odgovor API-ja"
        except Exception as e:
            last_err = str(e)
    return {"error": last_err or "API nedostupan"}


def fetch_unmineable_payments(coin: str, address: str) -> list:
    return []


def fetch_market(*a, **k):
    return {}


def fetch_price_usd(*a, **k):
    return None


def fetch_price_pair(*a, **k):
    return None


def expected_coins(*a, **k):
    return None


def format_coin_amount(x, *a, **k):
    return str(x)


def format_earn(*a, **k):
    return "—"


def format_hashes(*a, **k):
    return "—"


def format_hashrate(*a, **k):
    return "—"


def format_miners(*a, **k):
    return "—"


def format_money_hr(*a, **k):
    return "—"


def format_odds(*a, **k):
    return "—"


def format_price(*a, **k):
    return "—"


def format_share(*a, **k):
    return "—"


def hit_probability(*a, **k):
    return None


def odds_footnote(*a, **k):
    return ""
