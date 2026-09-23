# -*- coding: utf-8 -*-
"""Aura Motor — fast SHA-256d nonce scan (Numba). Desktop ASIC-style batch hasher."""
from __future__ import annotations

import hashlib
import struct
from typing import Any

import numpy as np

try:
    from numba import njit
    _HAS_NUMBA = True
except Exception:  # pragma: no cover
    _HAS_NUMBA = False
    def njit(*_a, **_k):
        def wrap(fn):
            return fn
        return wrap


# SHA-256 constants
_K = np.array([
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
], dtype=np.uint32)

_IV = np.array([
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
], dtype=np.uint32)


@njit(cache=True)
def _rotr(x, n):
    x = x & np.uint32(0xFFFFFFFF)
    return ((x >> n) | (x << (np.uint32(32) - n))) & np.uint32(0xFFFFFFFF)


@njit(cache=True)
def _sha256_block(state, block):
    w = np.empty(64, dtype=np.uint32)
    for i in range(16):
        j = i * 4
        w[i] = (
            (np.uint32(block[j]) << 24)
            | (np.uint32(block[j + 1]) << 16)
            | (np.uint32(block[j + 2]) << 8)
            | np.uint32(block[j + 3])
        )
    for i in range(16, 64):
        s0 = _rotr(w[i - 15], 7) ^ _rotr(w[i - 15], 18) ^ (w[i - 15] >> 3)
        s1 = _rotr(w[i - 2], 17) ^ _rotr(w[i - 2], 19) ^ (w[i - 2] >> 10)
        w[i] = (w[i - 16] + s0 + w[i - 7] + s1) & np.uint32(0xFFFFFFFF)

    a, b, c, d, e, f, g, h = state[0], state[1], state[2], state[3], state[4], state[5], state[6], state[7]
    K = _K
    for i in range(64):
        S1 = _rotr(e, 6) ^ _rotr(e, 11) ^ _rotr(e, 25)
        ch = (e & f) ^ ((~e) & g)
        t1 = (h + S1 + ch + K[i] + w[i]) & np.uint32(0xFFFFFFFF)
        S0 = _rotr(a, 2) ^ _rotr(a, 13) ^ _rotr(a, 22)
        maj = (a & b) ^ (a & c) ^ (b & c)
        t2 = (S0 + maj) & np.uint32(0xFFFFFFFF)
        h = g
        g = f
        f = e
        e = (d + t1) & np.uint32(0xFFFFFFFF)
        d = c
        c = b
        b = a
        a = (t1 + t2) & np.uint32(0xFFFFFFFF)

    state[0] = (state[0] + a) & np.uint32(0xFFFFFFFF)
    state[1] = (state[1] + b) & np.uint32(0xFFFFFFFF)
    state[2] = (state[2] + c) & np.uint32(0xFFFFFFFF)
    state[3] = (state[3] + d) & np.uint32(0xFFFFFFFF)
    state[4] = (state[4] + e) & np.uint32(0xFFFFFFFF)
    state[5] = (state[5] + f) & np.uint32(0xFFFFFFFF)
    state[6] = (state[6] + g) & np.uint32(0xFFFFFFFF)
    state[7] = (state[7] + h) & np.uint32(0xFFFFFFFF)


@njit(cache=True)
def _sha256d_76_nonce(prefix76, nonce):
    # First hash of 80-byte header
    block = np.zeros(64, dtype=np.uint8)
    for i in range(64):
        block[i] = prefix76[i]
    st = _IV.copy()
    _sha256_block(st, block)

    block2 = np.zeros(64, dtype=np.uint8)
    for i in range(12):
        block2[i] = prefix76[64 + i]
    block2[12] = np.uint8(nonce & 0xFF)
    block2[13] = np.uint8((nonce >> 8) & 0xFF)
    block2[14] = np.uint8((nonce >> 16) & 0xFF)
    block2[15] = np.uint8((nonce >> 24) & 0xFF)
    # padding for 80-byte message
    block2[16] = np.uint8(0x80)
    # length 640 bits
    block2[62] = np.uint8(0x02)
    block2[63] = np.uint8(0x80)
    _sha256_block(st, block2)

    # digest1 big-endian words -> bytes
    dig = np.empty(32, dtype=np.uint8)
    for i in range(8):
        v = st[i]
        dig[i * 4] = np.uint8((v >> 24) & 0xFF)
        dig[i * 4 + 1] = np.uint8((v >> 16) & 0xFF)
        dig[i * 4 + 2] = np.uint8((v >> 8) & 0xFF)
        dig[i * 4 + 3] = np.uint8(v & 0xFF)

    # Second SHA-256
    st2 = _IV.copy()
    block3 = np.zeros(64, dtype=np.uint8)
    for i in range(32):
        block3[i] = dig[i]
    block3[32] = np.uint8(0x80)
    # length 256 bits
    block3[62] = np.uint8(0x01)
    block3[63] = np.uint8(0x00)
    _sha256_block(st2, block3)

    out = np.empty(32, dtype=np.uint8)
    for i in range(8):
        v = st2[i]
        out[i * 4] = np.uint8((v >> 24) & 0xFF)
        out[i * 4 + 1] = np.uint8((v >> 16) & 0xFF)
        out[i * 4 + 2] = np.uint8((v >> 8) & 0xFF)
        out[i * 4 + 3] = np.uint8(v & 0xFF)
    return out


@njit(cache=True)
def _digest_le_u256_ok(digest, target_be):
    # int.from_bytes(digest,'little') <= int.from_bytes(target_be,'big')
    for i in range(32):
        a = digest[i]  # little: low byte first
        b = target_be[31 - i]  # big target low byte at end -> compare from low
        # Actually compare as 256-bit integers:
        # little digest: digest[0] is LSB
        # big target: target_be[31] is LSB
    # Compare from MSB of the integer value
    for i in range(32):
        da = digest[31 - i]  # MSB first from little-endian bytes
        tb = target_be[i]    # MSB first from big-endian bytes
        if da < tb:
            return True
        if da > tb:
            return False
    return True


@njit(cache=True)
def _scan_numba(prefix76, nonce_start, batch, target_be, out_nonces):
    found = 0
    max_out = out_nonces.shape[0]
    n0 = np.uint32(nonce_start)
    for i in range(batch):
        nonce = np.uint32((n0 + np.uint32(i)) & np.uint32(0xFFFFFFFF))
        dig = _sha256d_76_nonce(prefix76, nonce)
        if _digest_le_u256_ok(dig, target_be):
            if found < max_out:
                out_nonces[found] = nonce
            found += 1
            if found >= max_out:
                break
    return found


def _scan_python(prefix76, nonce_start, batch, target_be, out_nonces):
    found = 0
    max_out = int(out_nonces.shape[0])
    prefix = bytes(prefix76[:76])
    target_int = int.from_bytes(bytes(target_be[:32]), "big")
    for i in range(int(batch)):
        nonce = (int(nonce_start) + i) & 0xFFFFFFFF
        header = prefix + struct.pack("<I", nonce)
        digest = hashlib.sha256(hashlib.sha256(header).digest()).digest()
        if int.from_bytes(digest, "little") <= target_int:
            if found < max_out:
                out_nonces[found] = np.uint32(nonce)
            found += 1
            if found >= max_out:
                break
    return found


def scan_nonces(prefix_arr: Any, nonce_start: int, batch: int, target_arr: Any, out_nonces: Any) -> int:
    """Scan batch nonces; fill out_nonces; return number found."""
    prefix76 = np.ascontiguousarray(prefix_arr, dtype=np.uint8).ravel()[:76]
    target_be = np.ascontiguousarray(target_arr, dtype=np.uint8).ravel()[:32]
    out = np.ascontiguousarray(out_nonces, dtype=np.uint32).ravel()
    if prefix76.size < 76 or target_be.size < 32:
        return 0
    if _HAS_NUMBA:
        return int(_scan_numba(prefix76, np.uint32(nonce_start), int(batch), target_be, out))
    return int(_scan_python(prefix76, int(nonce_start), int(batch), target_be, out))
