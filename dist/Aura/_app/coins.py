"""Coin profiles: only Proof-of-Work coins Aura can actually hash."""

from __future__ import annotations

import re
from typing import Any

BTC_DIFF1 = 0x00000000FFFF0000000000000000000000000000000000000000000000000000
SCRYPT_DIFF1 = 0x0000FFFF00000000000000000000000000000000000000000000000000000000

COINS: dict[str, dict[str, Any]] = {
    "BTC": {
        "code": "BTC",
        "name": "Bitcoin",
        "label": "Bitcoin (BTC)",
        "algo": "sha256d",
        "mineable": True,
        "hardware": "gpu",
        "asic": True,
        "block_seconds": 600.0,
        "block_reward": 3.125,
        "diff1": BTC_DIFF1,
        "address_re": re.compile(r"^(1|3)[a-km-zA-HJ-NP-Z1-9]{25,34}$|^bc1[qp][a-z0-9]{25,87}$"),
        "address_label": "BTC ADRESA",
        "address_hint": "Unesi valjanu BTC adresu (1..., 3... ili bc1...).",
        "pool": ("btc.viabtc.io", "3333"),
        "solo": ("solo.ckpool.org", "3333"),
        "pool_login": "{address}.gpu",
        "solo_login": "{address}",
        "password": "x",
        "coingecko": "bitcoin",
        "coinbase": "BTC",
        "blockchair": "bitcoin",
        "wtm_tag": "BTC",
        "pool_stats": "mempool-viabtc",
        "pool_miner": "ViaBTC",
        "pool_blocks": True,
        "note": "SHA-256d na svim OpenCL GPU-evima i SHA-256 ASIC-ima. Pool: btc.viabtc.io. GPU je lutrija pored ASIC-a.",
    },
    "BCH": {
        "code": "BCH",
        "name": "Bitcoin Cash",
        "label": "Bitcoin Cash (BCH)",
        "algo": "sha256d",
        "mineable": True,
        "hardware": "gpu",
        "asic": True,
        "block_seconds": 600.0,
        "block_reward": 3.125,
        "diff1": BTC_DIFF1,
        "address_re": re.compile(
            r"^(1|3)[a-km-zA-HJ-NP-Z1-9]{25,34}$|^[qp][a-z0-9]{41}$",
            re.I,
        ),
        "address_label": "BCH ADRESA",
        "address_hint": "Unesi BCH adresu (cashaddr q.../p... ili legacy 1.../3...).",
        "pool": ("bch.viabtc.io", "3333"),
        "solo": ("solo-bch.2miners.com", "9393"),
        "pool_login": "{address}.gpu",
        "solo_login": "{address}",
        "password": "x",
        "coingecko": "bitcoin-cash",
        "coinbase": "BCH",
        "blockchair": "bitcoin-cash",
        "wtm_tag": "BCH",
        "pool_stats": "viabtc",
        "pool_miner": "ViaBTC",
        "pool_blocks": True,
        "note": "Isti SHA-256d kao BTC. GPU + SHA-256 ASIC. Pool: bch.viabtc.io. Solo: solo-bch.2miners.com:9393.",
    },
    "BSV": {
        "code": "BSV",
        "name": "Bitcoin SV",
        "label": "Bitcoin SV (BSV)",
        "algo": "sha256d",
        "mineable": True,
        "hardware": "gpu",
        "asic": True,
        "block_seconds": 600.0,
        "block_reward": 3.125,
        "diff1": BTC_DIFF1,
        "address_re": re.compile(r"^1[a-km-zA-HJ-NP-Z1-9]{25,34}$"),
        "address_label": "BSV ADRESA",
        "address_hint": "Unesi BSV legacy adresu (pocinje s 1...).",
        "pool": ("bsv.gorillapool.io", "3333"),
        "solo": ("bsv.gorillapool.io", "3333"),
        "pool_login": "{address}.gpu",
        "solo_login": "{address}",
        "password": "x",
        "coingecko": "bitcoin-cash-sv",
        "coinbase": "BSV",
        "wtm_tag": "BSV",
        "pool_stats": "gorillapool",
        "pool_miner": "GorillaPool",
        "pool_blocks": True,
        "note": "SHA-256d na GPU i SHA-256 ASIC. Pool: bsv.gorillapool.io:3333. Share diff moze biti visok za laptop GPU.",
    },
    "XEC": {
        "code": "XEC",
        "name": "eCash",
        "label": "eCash (XEC)",
        "algo": "sha256d",
        "mineable": True,
        "hardware": "gpu",
        "asic": True,
        "block_seconds": 600.0,
        "block_reward": 3_125_000.0,
        "diff1": BTC_DIFF1,
        "address_re": re.compile(r"^(ecash:)?[qp][a-z0-9]{41}$", re.I),
        "address_label": "XEC ADRESA",
        "address_hint": "Unesi eCash adresu (ecash:q... ili q...).",
        "uri_prefix": "ecash:",
        "pool": ("xec.hmpool.io", "3335"),
        "solo": ("xec.mkpool.com", "3393"),
        "pool_login": "{address}.gpu",
        "solo_login": "{address}",
        "password": "x",
        "coingecko": "ecash",
        "coinbase": None,
        "blockchair": "ecash",
        "wtm_tag": "XEC",
        "pool_stats": "hmpool",
        "pool_miner": "HMPool",
        "pool_blocks": True,
        "note": "SHA-256d na GPU i ASIC. Pool (GPU port): xec.hmpool.io:3335. Solo: xec.mkpool.com:3393. ASIC-i neka dignu port ako pool odbija shareove.",
    },
    "DGB": {
        "code": "DGB",
        "name": "DigiByte",
        "label": "DigiByte SHA-256 (DGB)",
        "algo": "sha256d",
        "mineable": True,
        "hardware": "gpu",
        "asic": True,
        "block_seconds": 75.0,
        "block_reward": 223.0,
        "diff1": BTC_DIFF1,
        "address_re": re.compile(r"^D[1-9A-HJ-NP-Za-km-z]{25,34}$|^dgb1[a-z0-9]{25,87}$"),
        "address_label": "DGB ADRESA",
        "address_hint": "Unesi DigiByte adresu (D... ili dgb1...).",
        "pool": ("digi.hmpool.io", "3335"),
        "solo": ("dgb.mkpool.com", "3373"),
        "pool_login": "{address}.gpu",
        "solo_login": "{address}",
        "password": "x",
        "coingecko": "digibyte",
        "coinbase": "DGB",
        "wtm_tag": "DGB",
        "wtm_name": "DGB-SHA",
        "pool_stats": "hmpool",
        "pool_miner": "HMPool",
        "pool_blocks": True,
        "note": "Samo SHA-256d dio DigiByte mreze (od 5 algoa). GPU + SHA-256 ASIC. Pool: digi.hmpool.io:3335. Solo: dgb.mkpool.com:3373.",
    },
    "LTC": {
        "code": "LTC",
        "name": "Litecoin",
        "label": "Litecoin (LTC)",
        "algo": "scrypt",
        "mineable": True,
        "hardware": "gpu",
        "asic": True,
        "block_seconds": 150.0,
        "block_reward": 6.25,
        "diff1": SCRYPT_DIFF1,
        "address_re": re.compile(r"^(L|M)[1-9A-HJ-NP-Za-km-z]{25,34}$|^ltc1[a-z0-9]{25,87}$"),
        "address_label": "LTC ADRESA",
        "address_hint": "Unesi valjanu Litecoin adresu (L..., M... ili ltc1...).",
        "pool": ("ltc.viabtc.io", "3333"),
        "solo": ("127.0.0.1", "3333"),
        "pool_login": "{address}.gpu",
        "solo_login": "{address}",
        "password": "x",
        "coingecko": "litecoin",
        "coinbase": "LTC",
        "blockchair": "litecoin",
        "wtm_tag": "LTC",
        "pool_stats": "litecoinspace-viabtc",
        "pool_miner": "ViaBTC",
        "pool_blocks": True,
        "note": "Scrypt na GPU i Scrypt ASIC. ViaBTC merge-isplacuje i DOGE, PEP, BEL, LKY. Solo treba tvoj LTC node.",
    },
    "DOGE": {
        "code": "DOGE",
        "name": "Dogecoin",
        "label": "Dogecoin (DOGE)",
        "algo": "scrypt",
        "mineable": True,
        "hardware": "gpu",
        "asic": True,
        "block_seconds": 60.0,
        "block_reward": 10000.0,
        "diff1": SCRYPT_DIFF1,
        "address_re": re.compile(r"^D[1-9A-HJ-NP-Za-km-z]{25,34}$"),
        "address_label": "DOGE ADRESA",
        "address_hint": "Unesi valjanu Dogecoin adresu (pocinje s D).",
        "pool": ("ltc.viabtc.io", "3333"),
        "solo": ("127.0.0.1", "19327"),
        "pool_login": "{address}.gpu",
        "solo_login": "{address}",
        "password": "x",
        "coingecko": "dogecoin",
        "coinbase": "DOGE",
        "blockchair": "dogecoin",
        "wtm_tag": "DOGE",
        "pool_stats": "litecoinspace-viabtc",
        "pool_miner": "ViaBTC",
        "pool_blocks": False,
        "note": "Scrypt na GPU i ASIC. DOGE se merge-rudari uz Litecoin (ltc.viabtc.io). Solo treba tvoj DOGE node.",
    },
    "PEP": {
        "code": "PEP",
        "name": "Pepecoin",
        "label": "Pepecoin (PEP)",
        "algo": "scrypt",
        "mineable": True,
        "hardware": "gpu",
        "asic": True,
        "block_seconds": 60.0,
        "block_reward": 50.0,
        "diff1": SCRYPT_DIFF1,
        "address_re": re.compile(r"^P[1-9A-HJ-NP-Za-km-z]{25,34}$"),
        "address_label": "PEP ADRESA",
        "address_hint": "Unesi Pepecoin (PEP) adresu (pocinje s P), ne PEPE token.",
        "pool": ("ltc.viabtc.io", "3333"),
        "solo": ("127.0.0.1", "3388"),
        "pool_login": "{address}.gpu",
        "solo_login": "{address}",
        "password": "x",
        "coingecko": "pepecoin-network",
        "coinbase": None,
        "wtm_tag": "PEP",
        "pool_stats": "litecoinspace-viabtc",
        "pool_miner": "ViaBTC",
        "pool_blocks": False,
        "note": "Scrypt GPU + ASIC. PEP je merge uz LTC na ltc.viabtc.io (nije PEPE token). Solo treba tvoj PEP node.",
    },
    "BEL": {
        "code": "BEL",
        "name": "Bellscoin",
        "label": "Bellscoin (BEL)",
        "algo": "scrypt",
        "mineable": True,
        "hardware": "gpu",
        "asic": True,
        "block_seconds": 60.0,
        "block_reward": 50.0,
        "diff1": SCRYPT_DIFF1,
        "address_re": re.compile(r"^B[1-9A-HJ-NP-Za-km-z]{25,34}$|^bel1[a-z0-9]{25,87}$"),
        "address_label": "BEL ADRESA",
        "address_hint": "Unesi Bellscoin adresu (B... ili bel1...), ne Bella Protocol.",
        "pool": ("ltc.viabtc.io", "3333"),
        "solo": ("127.0.0.1", "3333"),
        "pool_login": "{address}.gpu",
        "solo_login": "{address}",
        "password": "x",
        "coingecko": "bellscoin",
        "coinbase": None,
        "wtm_tag": "BEL",
        "pool_stats": "litecoinspace-viabtc",
        "pool_miner": "ViaBTC",
        "pool_blocks": False,
        "note": "Scrypt GPU + ASIC. BEL se merge-rudari uz LTC na ltc.viabtc.io. Solo treba tvoj BEL node.",
    },
    "LKY": {
        "code": "LKY",
        "name": "Luckycoin",
        "label": "Luckycoin (LKY)",
        "algo": "scrypt",
        "mineable": True,
        "hardware": "gpu",
        "asic": True,
        "block_seconds": 60.0,
        "block_reward": 88.0,
        "diff1": SCRYPT_DIFF1,
        "address_re": re.compile(r"^L[1-9A-HJ-NP-Za-km-z]{25,34}$"),
        "address_label": "LKY ADRESA",
        "address_hint": "Unesi Luckycoin adresu (pocinje s L).",
        "pool": ("ltc.viabtc.io", "3333"),
        "solo": ("127.0.0.1", "3333"),
        "pool_login": "{address}.gpu",
        "solo_login": "{address}",
        "password": "x",
        "coingecko": "luckycoin",
        "coinbase": None,
        "wtm_tag": "LKY",
        "pool_stats": "litecoinspace-viabtc",
        "pool_miner": "ViaBTC",
        "pool_blocks": False,
        "note": "Scrypt GPU + ASIC. LKY se merge-rudari uz LTC na ltc.viabtc.io. Solo treba tvoj LKY node.",
    },
    "XMR": {
        "code": "XMR",
        "name": "Monero",
        "label": "Monero (XMR)",
        "algo": "randomx",
        "mineable": True,
        "hardware": "cpu",
        "asic": False,
        "block_seconds": 120.0,
        "block_reward": 0.6,
        "diff1": 0,
        "address_re": re.compile(r"^[48][1-9A-HJ-NP-Za-km-z]{93,106}$"),
        "address_label": "XMR ADRESA",
        "address_hint": "Unesi valjanu Monero adresu (4... ili 8...).",
        "pool": ("pool.supportxmr.com", "3333"),
        "solo": ("127.0.0.1", "3333"),
        "pool_login": "{address}",
        "solo_login": "{address}",
        "password": "x",
        "coingecko": "monero",
        "coinbase": None,
        "wtm_tag": "XMR",
        "pool_stats": "supportxmr",
        "pool_miner": "SupportXMR",
        "pool_blocks": True,
        "note": "RandomX na CPU. SHA-256/Scrypt ASIC API ovdje ne radi. Pool: pool.supportxmr.com:3333. Solo: p2pool 127.0.0.1:3333.",
    },
    "RVN": {
        "code": "RVN",
        "name": "Ravencoin",
        "label": "Ravencoin (RVN)",
        "algo": "kawpow",
        "stratum": "eth",
        "mineable": True,
        "hardware": "gpu",
        "asic": True,
        "block_seconds": 60.0,
        "block_reward": 2500.0,
        "diff1": 0,
        "address_re": re.compile(r"^R[1-9A-HJ-NP-Za-km-z]{25,34}$"),
        "address_label": "RVN ADRESA",
        "address_hint": "Unesi Ravencoin adresu (pocinje s R).",
        "pool": ("rvn.2miners.com", "6060"),
        "solo": ("solo-rvn.2miners.com", "6060"),
        "pool_login": "{address}.gpu",
        "solo_login": "{address}.gpu",
        "password": "x",
        "coingecko": "ravencoin",
        "coinbase": None,
        "wtm_tag": "RVN",
        "pool_stats": "2miners",
        "pool_api": "https://rvn.2miners.com/api/stats",
        "pool_miner": "2Miners",
        "pool_blocks": True,
        "note": "KawPow na GPU (i KawPow ASIC). Pool: rvn.2miners.com:6060. Solo: solo-rvn.2miners.com:6060. Isplata moze u BTC, BCH, XMR ili XRP preko unMineable.",
    },
    "ETC": {
        "code": "ETC",
        "name": "Ethereum Classic",
        "label": "Ethereum Classic (ETC)",
        "algo": "etchash",
        "stratum": "eth",
        "mineable": True,
        "hardware": "gpu",
        "asic": False,
        "block_seconds": 13.0,
        "block_reward": 2.56,
        "diff1": 0,
        "address_re": re.compile(r"^0x[0-9a-fA-F]{40}$"),
        "address_label": "ETC ADRESA",
        "address_hint": "Unesi ETC adresu (0x i 40 hex znakova).",
        "pool": ("etc.2miners.com", "1010"),
        "solo": ("solo-etc.2miners.com", "1010"),
        "pool_login": "{address}.gpu",
        "solo_login": "{address}.gpu",
        "password": "x",
        "coingecko": "ethereum-classic",
        "coinbase": None,
        "wtm_tag": "ETC",
        "pool_stats": "2miners",
        "pool_api": "https://etc.2miners.com/api/stats",
        "pool_miner": "2Miners",
        "pool_blocks": True,
        "note": "Etchash na GPU. Pool: etc.2miners.com:1010. Solo: solo-etc.2miners.com:1010. Prvi start gradi DAG u VRAM. Isplata moze u BTC, BCH, XMR ili XRP.",
    },
    "IRON": {
        "code": "IRON",
        "name": "Iron Fish",
        "label": "Iron Fish (IRON)",
        "algo": "fishhash",
        "stratum": "eth",
        "mineable": True,
        "hardware": "gpu",
        "asic": False,
        "block_seconds": 60.0,
        "block_reward": 19.0,
        "diff1": 0,
        "address_re": re.compile(r"^[0-9a-fA-F]{64}$"),
        "address_label": "IRON ADRESA",
        "address_hint": "Unesi Iron Fish adresu (64 hex znaka, bez 0x).",
        "pool": ("iron.kryptex.network", "7017"),
        "solo": ("iron.kryptex.network", "7017"),
        "pool_login": "{address}.gpu",
        "solo_login": "solo:{address}.gpu",
        "password": "x",
        "coingecko": "iron-fish",
        "coinbase": None,
        "wtm_tag": "IRON",
        "pool_stats": "2miners",
        "pool_api": "https://iron.2miners.com/api/stats",
        "pool_miner": "Kryptex",
        "pool_blocks": True,
        "note": "FishHash na GPU. Pool: iron.kryptex.network:7017. Isplata moze u BTC, BCH, XMR ili XRP preko unMineable.",
    },
    "PRL": {
        "code": "PRL",
        "name": "Pearl",
        "label": "Pearl (PRL)",
        "algo": "pearlpow",
        "stratum": "eth",
        "mineable": True,
        "hardware": "gpu",
        "asic": False,
        "block_seconds": 194.0,
        "block_reward": 50.0,
        "diff1": 0,
        "address_re": re.compile(r"^prl1[02-9ac-hj-np-z]{20,80}$"),
        "address_label": "PRL ADRESA",
        "address_hint": "Unesi Pearl adresu (pocinje s prl1...).",
        "pool": ("prl.2miners.com", "1818"),
        "solo": ("solo-prl.2miners.com", "1919"),
        "pool_login": "{address}.gpu",
        "solo_login": "{address}.gpu",
        "password": "x",
        "coingecko": "pearl-2",
        "coinbase": None,
        "wtm_tag": "PRL",
        "pool_stats": "2miners",
        "pool_api": "https://prl.2miners.com/api/stats",
        "pool_miner": "2Miners",
        "pool_blocks": True,
        "note": "PearlPow/PearlHash na GPU. Pool: prl.2miners.com:1818. Solo: solo-prl.2miners.com:1919. Isplata moze u BTC, BCH, XMR ili XRP preko unMineable.",
    },
}

ORDER = (
    "BTC",
    "BCH",
    "BSV",
    "XEC",
    "DGB",
    "LTC",
    "DOGE",
    "PEP",
    "BEL",
    "LKY",
    "XMR",
    "RVN",
    "ETC",
    "IRON",
    "PRL",
)

HASHER_ALGOS = frozenset({"sha256d", "scrypt", "randomx", "kawpow", "etchash"})
ETH_ALGOS = frozenset({"kawpow", "etchash", "fishhash", "pearlpow"})

UNMINEABLE = {
    "sha256d": ("sha256.unmineable.com", "3333"),
    "scrypt": ("scrypt.unmineable.com", "3333"),
    "randomx": ("rx.unmineable.com", "3333"),
    "kawpow": ("kp.unmineable.com", "3333"),
    "etchash": ("etchash.unmineable.com", "3333"),
    "fishhash": ("fishhash.unmineable.com", "3333"),
    "pearlpow": ("pearlpow.unmineable.com", "3333"),
}

XRP_RE = re.compile(r"^r[1-9A-HJ-NP-Za-km-z]{24,34}$")

PAYOUTS: dict[str, dict[str, Any]] = {
    "NATIVE": {
        "code": "NATIVE",
        "label": "Isti coin",
        "short": "ISTI COIN",
        "network": "",
    },
    "BTC": {
        "code": "BTC",
        "label": "Bitcoin (BTC)",
        "short": "BTC",
        "unmineable": "BTC",
        "network": "Bitcoin",
        "address_re": COINS["BTC"]["address_re"],
        "address_label": "BTC ADRESA (ISPLATA)",
        "address_hint": COINS["BTC"]["address_hint"],
    },
    "BCH": {
        "code": "BCH",
        "label": "Bitcoin Cash (BCH)",
        "short": "BCH",
        "unmineable": "BCH",
        "network": "Bitcoin Cash",
        "address_re": COINS["BCH"]["address_re"],
        "address_label": "BCH ADRESA (ISPLATA)",
        "address_hint": COINS["BCH"]["address_hint"],
    },
    "XMR": {
        "code": "XMR",
        "label": "Monero (XMR)",
        "short": "XMR",
        "unmineable": "XMR",
        "network": "Monero",
        "address_re": COINS["XMR"]["address_re"],
        "address_label": "XMR ADRESA (ISPLATA)",
        "address_hint": COINS["XMR"]["address_hint"],
    },
    "XRP": {
        "code": "XRP",
        "label": "Ripple (XRP)",
        "short": "XRP",
        "unmineable": "XRP",
        "network": "XRP Ledger",
        "address_re": XRP_RE,
        "address_label": "XRP ADRESA (ISPLATA)",
        "address_hint": "Unesi XRP adresu (pocinje s r). Destination tag ostavi prazan ako wallet ne trazi.",
        "needs_tag": True,
    },
}

PAYOUT_ORDER = ("NATIVE", "BTC", "BCH", "XMR", "XRP")
PAYOUT_COINS = tuple(code for code in PAYOUT_ORDER if code != "NATIVE")

# Typical native-chain wait AFTER the pool broadcasts a real payout TX (TXID exists).
# Never start this 10–60 min countdown for a local POVUCI — that is not on-chain.
# Without a TXID the payout is still at unMineable (saldo / minimum).
PAYOUT_WAIT: dict[str, dict[str, Any]] = {
    "BTC": {"lo": 10, "hi": 60, "typical": 30, "conf": 3, "block_min": 10.0},
    "BCH": {"lo": 10, "hi": 20, "typical": 12, "conf": 1, "block_min": 10.0},
    "XMR": {"lo": 10, "hi": 20, "typical": 20, "conf": 10, "block_min": 2.0},
    "XRP": {"lo": 1, "hi": 5, "typical": 3, "conf": 1, "block_min": 0.1},
}

# Honest copy while the pool has not broadcast a TX yet.
PAYOUT_WAIT_POOL_HEAD = "ČEKA BAZEN"
PAYOUT_WAIT_POOL_SUB = "nema još TX na lancu — čeka bazen (unMineable saldo / minimum)."
PAYOUT_WAIT_PENDING_POOL = "čeka bazen"
PAYOUT_WAIT_PENDING_CHAIN = "na mreži"

# Wrapped / wrong-chain tickers — never send these to unMineable.
WRAPPED_UNMINEABLE = {
    "WBTC": "BTC",
    "BTCB": "BTC",
    "BTC.B": "BTC",
    "CBBTC": "BTC",
    "HBTC": "BTC",
    "RENBTC": "BTC",
    "TBTC": "BTC",
    "BTCBEP20": "BTC",
    "BTCERC20": "BTC",
    "WXMR": "XMR",
    "WXRP": "XRP",
}

_ETH_ADDR_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
_TRON_ADDR_RE = re.compile(r"^T[1-9A-HJ-NP-Za-km-z]{33}$")
_CASHADDR_RE = re.compile(r"^(bitcoincash:)?[qp][a-z0-9]{41}$", re.I)

_KIND_HR = {
    "ETH": "Ethereum (0x / ERC-20)",
    "BTC": "Bitcoin",
    "BCH": "Bitcoin Cash",
    "XMR": "Monero",
    "XRP": "XRP Ledger",
    "TRX": "Tron (TRC-20)",
    "LTC": "Litecoin",
    "DOGE": "Dogecoin",
    "ETC": "Ethereum Classic",
}

_ADDR_HINT = {
    "BTC": "Bitcoin adresu (bc1..., 1... ili 3...)",
    "BCH": "Bitcoin Cash adresu (q... / p... ili legacy 1.../3...)",
    "XMR": "Monero adresu (4... ili 8..., oko 95 znakova)",
    "XRP": "XRP adresu (pocinje s r)",
}


def unmineable_coin(code: str) -> str:
    """unMineable ticker = native coin only (BTC, never WBTC / BEP-20 / ERC-20)."""
    raw = (code or "").upper().strip()
    if not raw or raw == "NATIVE":
        return ""
    raw = WRAPPED_UNMINEABLE.get(raw, raw)
    spec = PAYOUTS.get(raw) or {}
    ticker = str(spec.get("unmineable") or "").upper()
    if ticker:
        return WRAPPED_UNMINEABLE.get(ticker, ticker)
    if raw in COINS:
        return raw
    return raw


def native_network(code: str) -> str:
    """Human native-chain name. Never ERC-20 / BEP-20 / wrapped."""
    raw = (code or "").upper().strip()
    mapped = unmineable_coin(raw) or raw
    spec = PAYOUTS.get(mapped) or {}
    if spec.get("network"):
        return str(spec["network"])
    coin = COINS.get(mapped) or COINS.get(raw)
    if coin:
        return str(coin.get("name") or mapped)
    return mapped or raw


def payout_wait_minutes(code: str) -> dict[str, Any]:
    """Typical confirmation wait on the native payout chain, in minutes.

    Use only after a real TXID exists. Without a TXID show PAYOUT_WAIT_POOL_*
    instead of these minutes — the pool has not broadcast yet.
    """
    pay = (unmineable_coin(code) or (code or "").upper()).strip()
    spec = PAYOUT_WAIT.get(pay)
    if spec:
        out = dict(spec)
        out["coin"] = pay
        out["known"] = True
        return out
    return {
        "coin": pay,
        "lo": 10,
        "hi": 60,
        "typical": 30,
        "conf": 1,
        "block_min": 10.0,
        "known": False,
    }


def payout_chain_confirm_sub(code: str) -> str:
    """On-chain confirm copy — only after a real TXID exists, never for local POVUCI."""
    pay = (unmineable_coin(code) or (code or "").upper()).strip() or "coin"
    net = native_network(pay) or "mreži"
    return f"{pay} još čeka potvrde na {net}."


def network_tag(code: str) -> str:
    raw = (code or "").upper().strip()
    mapped = unmineable_coin(raw) or raw
    net = native_network(mapped)
    if not mapped or mapped == "NATIVE":
        return net or "—"
    if net and net.upper() != mapped:
        return f"{mapped} · {net}"
    return mapped or "—"


def network_send_hint(code: str) -> str:
    pay = unmineable_coin(code) or (code or "").upper()
    net = native_network(pay)
    if pay == "BTC":
        return "BTC ide Bitcoin mrežom. Nije wrapped, nije Ethereum, nije BEP-20."
    if pay == "BCH":
        return "BCH ide Bitcoin Cash mrežom. Nije Bitcoin (bc1), nije Ethereum."
    if pay == "XMR":
        return "XMR ide Monero mrežom. Nije Ethereum, nije wrapped."
    if pay == "XRP":
        return "XRP ide XRP Ledger mrežom. Nije Ethereum, nije wrapped."
    if net:
        return f"{pay or net} ide {net} mrežom. Nije wrapped, nije tuđa mreža."
    return "Svaki coin ide svojom nativnom mrežom. Nije wrapped."


def unmineable_address_url(coin: str, address: str) -> str:
    code = unmineable_coin(coin)
    addr = (address or "").strip()
    if not code or not addr:
        return ""
    return f"https://unmineable.com/coins/{code}/address/{addr}"


def guess_address_kind(address: str) -> str:
    """Best-effort native-chain guess for a pasted wallet address."""
    addr = (address or "").strip()
    if not addr:
        return ""
    low = addr.lower()
    if _ETH_ADDR_RE.match(addr):
        return "ETH"
    if low.startswith("bc1"):
        return "BTC"
    if low.startswith("ltc1"):
        return "LTC"
    if COINS["XMR"]["address_re"].match(addr):
        return "XMR"
    if _CASHADDR_RE.match(addr) or low.startswith("bitcoincash:"):
        return "BCH"
    if XRP_RE.match(addr):
        return "XRP"
    if _TRON_ADDR_RE.match(addr):
        return "TRX"
    if COINS["LTC"]["address_re"].match(addr):
        return "LTC"
    if COINS["DOGE"]["address_re"].match(addr):
        return "DOGE"
    if COINS["BTC"]["address_re"].match(addr):
        return "BTC"
    if COINS["ETC"]["address_re"].match(addr):
        return "ETC"
    return ""


DESTINATIONS: dict[str, dict[str, Any]] = {
    "WALLET": {
        "code": "WALLET",
        "short": "NOVČANIK",
        "label": "Novčanik",
        "exchange": False,
    },
    "REVOLUT": {
        "code": "REVOLUT",
        "short": "REVOLUT X",
        "label": "Revolut X",
        "exchange": False,
    },
    "BINANCE": {
        "code": "BINANCE",
        "short": "BINANCE",
        "label": "Binance",
        "exchange": True,
    },
    "COINBASE": {
        "code": "COINBASE",
        "short": "COINBASE",
        "label": "Coinbase",
        "exchange": True,
    },
    "KRAKEN": {
        "code": "KRAKEN",
        "short": "KRAKEN",
        "label": "Kraken",
        "exchange": True,
    },
}
DEST_ORDER = ("WALLET", "REVOLUT", "BINANCE", "COINBASE", "KRAKEN")
_DEST_ALIASES = {
    "WALLET": "WALLET",
    "NOVČANIK": "WALLET",
    "NOVCANIK": "WALLET",
    "REVOLUT": "REVOLUT",
    "REVOLUTX": "REVOLUT",
    "REVOLUT X": "REVOLUT",
    "BINANCE": "BINANCE",
    "COINBASE": "COINBASE",
    "COIN BASE": "COINBASE",
    "KRAKEN": "KRAKEN",
}


def normalize_dest(code: str) -> str:
    raw = str(code or "").strip().upper().replace("_", " ")
    raw = raw.replace("Č", "C").replace("Ć", "C")
    return _DEST_ALIASES.get(raw, "WALLET" if raw not in DESTINATIONS else raw)


def dest_spec(code: str) -> dict[str, Any]:
    return DESTINATIONS.get(normalize_dest(code), DESTINATIONS["WALLET"])


def dest_label(code: str) -> str:
    raw = str(code or "").strip()
    if not raw:
        return ""
    return str(dest_spec(raw).get("label") or "Novčanik")


def dest_is_exchange(code: str) -> bool:
    return bool(dest_spec(code).get("exchange"))


def dest_shows_tag(dest: str, pay: str = "") -> bool:
    if (pay or "").upper() == "XRP":
        return True
    return dest_is_exchange(dest)


def dest_requires_tag(dest: str, pay: str = "") -> bool:
    return dest_is_exchange(dest) and (pay or "").upper() == "XRP"


def destination_hint(dest: str, pay: str = "") -> str:
    pay = unmineable_coin(pay) or (pay or "").upper()
    net = native_network(pay) or "nativna"
    where = dest_label(dest)
    code = normalize_dest(dest)
    if code == "WALLET":
        return (
            f"Zalijepi adresu svog {pay or 'coin'} novčanika. "
            f"{pay or 'Coin'} ide {net} mrežom — ne wrapped, ne Ethereum."
        )
    if code == "REVOLUT":
        return (
            f"U Revolut X: Receive → {pay or 'coin'} → mreža {net} "
            f"(ne ERC-20 / BEP-20). Zalijepi tu adresu. Bez API ključa."
        )
    extra = ""
    if pay == "XRP":
        extra = f" Zalijepi i TAG / MEMO — {where} bez taga ne pripisuje XRP."
    elif pay == "BTC":
        extra = f" U {where} Deposit odaberi Bitcoin, ne BEP20 / ERC20 / WBTC."
    return (
        f"U {where}: Deposit / Receive → {pay or 'coin'} → mreža {net}. "
        f"Zalijepi Deposit Address iz aplikacije.{extra} Aura ne traži lozinku ni API."
    )


def dest_tag_hint(dest: str, pay: str = "") -> str:
    where = dest_label(dest)
    if (pay or "").upper() == "XRP" and dest_is_exchange(dest):
        return (
            f"{where} za XRP TRAŽI destination tag / memo. "
            "Kopiraj ga uz adresu iz Deposit ekrana. Bez taga novac se može izgubiti."
        )
    if (pay or "").upper() == "XRP":
        return "XRP destination tag — ostavi prazan ako Revolut X / novčanik ne traži."
    if dest_is_exchange(dest):
        return (
            f"TAG / MEMO za {where}. Za BTC na Bitcoin mreži obično prazno. "
            "Upiši samo ako Deposit ekran pokazuje Memo."
        )
    return "Destination tag / memo — samo ako odredište traži."


def _wrong_chain_msg(pay: str, kind: str, dest: str = "") -> str:
    net = native_network(pay)
    seen = _KIND_HR.get(kind, kind)
    want = _ADDR_HINT.get(pay, f"{pay} adresu ({net})")
    extra = ""
    if pay == "BTC" and kind == "ETH":
        extra = " — ne ERC-20, ne WBTC, ne BEP-20"
    elif kind == "ETH":
        extra = " — ne Ethereum / ERC-20"
    elif pay == "BTC" and kind == "BCH":
        extra = " — ne BCH cashaddr"
    elif pay == "BCH" and kind == "BTC":
        extra = " — bc1 je Bitcoin, nije BCH"
    where = dest_label(dest) if dest else ""
    if dest_is_exchange(dest):
        return (
            f"Odabrao si {where}, ali ovo izgleda kao {seen} adresa. "
            f"U {where} Deposit odaberi mrežu {net}{extra}. "
            f"Zalijepi {where} {want}."
        )
    return (
        f"Ovo izgleda kao {seen} adresa. {pay} ide SAMO {net} mrežom{extra}. "
        f"Zalijepi {want}."
    )


def validate_payout_address(address: str, pay: str, dest: str = "") -> tuple[bool, str]:
    """Rough native-network check. Warns in Croatian if the paste is the wrong chain."""
    pay = unmineable_coin(pay) or (pay or "").upper()
    addr = (address or "").strip()
    if pay == "BTC" and addr.lower().startswith("bc1"):
        addr = addr.lower()
    net = native_network(pay)
    where = dest_label(dest) if dest else "novčanika"
    if not addr:
        if dest_is_exchange(dest):
            return False, (
                f"Upiši {where} Deposit Address za {pay} ({net} mreža). "
                "Kopiraj je iz aplikacije — Aura ne traži API ni lozinku."
            )
        return False, f"Upiši {pay} adresu ({net} mreža). Polje gore ne smije biti prazno."
    if len(addr) < 20:
        return False, f"Adresa je prekratka za {pay} ({net}). Zalijepi punu adresu s {where}."
    spec = PAYOUTS.get(pay) or {}
    cre = spec.get("address_re")
    body = addr
    if pay == "BCH" and addr.lower().startswith("bitcoincash:"):
        body = addr.split(":", 1)[-1]
    if cre is not None:
        try:
            if cre.match(addr) or cre.match(body):
                return True, ""
        except Exception:
            pass
    kind = guess_address_kind(addr)
    if pay == "BCH" and kind == "BTC" and addr[:1] in "13":
        return True, ""
    if kind and kind != pay:
        return False, _wrong_chain_msg(pay, kind, dest)
    hint = _ADDR_HINT.get(pay, f"{pay} adresu")
    return False, f"Ovo ne izgleda kao {pay} adresa na mreži {net}. Zalijepi {hint}."


def validate_payout_tag(tag: str, pay: str, dest: str = "") -> tuple[bool, str]:
    text = str(tag or "").strip()
    if not dest_requires_tag(dest, pay):
        return True, ""
    where = dest_label(dest)
    if not text:
        return False, (
            f"{where} za XRP traži TAG / MEMO. Kopiraj Destination Tag "
            f"uz Deposit Address u {where} aplikaciji."
        )
    return True, ""


def get_coin(code: str) -> dict[str, Any]:
    return COINS.get((code or "BTC").upper(), COINS["BTC"])


def labels() -> list[str]:
    return [COINS[code]["label"] for code in ORDER]


def code_from_label(label: str) -> str:
    for code in ORDER:
        if COINS[code]["label"] == label:
            return code
    return "BTC"


def format_address(coin: dict[str, Any], address: str) -> str:
    text = (address or "").strip()
    prefix = str(coin.get("uri_prefix") or "")
    if prefix and not text.lower().startswith(prefix.lower()):
        return prefix + text
    return text


def uses_convert(coin: dict[str, Any], mode: str, payout: str | None) -> bool:
    if (mode or "pool") != "pool":
        return False
    code = (payout or "NATIVE").upper()
    if code in ("", "NATIVE"):
        return False
    if code == str(coin.get("code") or "").upper():
        return False
    return str(coin.get("algo") or "") in UNMINEABLE


def payout_spec(coin: dict[str, Any], payout: str | None) -> dict[str, Any]:
    code = (payout or "NATIVE").upper()
    if code in ("", "NATIVE") or code == str(coin.get("code") or "").upper():
        return coin
    spec = PAYOUTS.get(code) or PAYOUTS["NATIVE"]
    if spec.get("address_re"):
        return spec
    return coin


def wallet_key(coin: dict[str, Any], payout: str | None) -> str:
    spec = payout_spec(coin, payout)
    return str(spec.get("code") or coin["code"])


def unmineable_login(pay_code: str, address: str, payout_tag: str = "") -> str:
    addr = (address or "").strip()
    pay = unmineable_coin(pay_code) or (pay_code or "").upper()
    tag = (payout_tag or "").strip()
    if pay == "XRP" and tag:
        return f"{pay}:{addr}:{tag}.aura"
    return f"{pay}:{addr}.aura"


def resolve_session(
    coin: dict[str, Any],
    address: str,
    mode: str,
    payout: str = "NATIVE",
    payout_tag: str = "",
    prefer_gpu: bool = True,
) -> dict[str, Any]:
    original = dict(coin)
    code = str(original.get("code") or "BTC")
    algo = str(original.get("algo") or "")
    addr = (address or "").strip()
    mode = "solo" if mode == "solo" else "pool"
    pay = (payout or "NATIVE").upper()
    convert = uses_convert(original, mode, pay)
    engine_coin = dict(original)

    if algo not in HASHER_ALGOS:
        fallback = "sha256d" if prefer_gpu else "randomx"
        engine_coin["algo"] = fallback
        engine_coin["asic"] = fallback in ("sha256d", "scrypt")
        engine_coin["hardware"] = "cpu" if fallback == "randomx" else "gpu"
        host, port = UNMINEABLE[fallback]
        pay_code = unmineable_coin(pay if convert else code) or (pay if convert else code)
        return {
            "host": str(host),
            "port": str(port),
            "login": unmineable_login(pay_code, addr, payout_tag),
            "engine_coin": engine_coin,
            "mode": "pool",
            "payout": pay if convert else "NATIVE",
            "note": (
                f"{algo} kernel ide preko {fallback} na unMineable, "
                f"isplata {pay_code} na mreži {native_network(pay_code)}. Radi 24h."
            ),
        }

    host, port = endpoint(original, mode, pay)
    return {
        "host": str(host),
        "port": str(port),
        "login": worker_login(original, addr, mode, pay, payout_tag),
        "engine_coin": engine_coin,
        "mode": mode,
        "payout": pay,
        "note": None,
    }


def worker_login(
    coin: dict[str, Any],
    address: str,
    mode: str,
    payout: str = "NATIVE",
    payout_tag: str = "",
) -> str:
    addr = (address or "").strip()
    if uses_convert(coin, mode, payout):
        pay = unmineable_coin(payout) or (payout or "").upper()
        tag = (payout_tag or "").strip()
        if pay == "XRP" and tag:
            return f"{pay}:{addr}:{tag}.aura"
        return f"{pay}:{addr}.aura"
    template = coin["solo_login"] if mode == "solo" else coin["pool_login"]
    return template.format(address=format_address(coin, addr))


def endpoint(coin: dict[str, Any], mode: str, payout: str = "NATIVE") -> tuple[str, str]:
    if uses_convert(coin, mode, payout):
        host, port = UNMINEABLE[str(coin["algo"])]
        return str(host), str(port)
    host, port = coin["solo"] if mode == "solo" else coin["pool"]
    return str(host), str(port)
