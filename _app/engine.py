"""Built-in Bitcoin SHA-256d Stratum miner (no third-party EXE)."""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import queue
import socket
import struct
import threading
import time
from multiprocessing import Array, Process, Queue, RawValue, Value, cpu_count
from pathlib import Path
from typing import Callable

# --- HashStart: hide child process consoles on Windows (no black cmd flash) ---
def _hashstart_hide_mp_consoles():
    """Force multiprocessing spawn without visible console windows on Windows."""
    import sys as _sys
    if _sys.platform != "win32":
        return
    try:
        import multiprocessing as _mp
        # Prefer pythonw.exe so children are GUI/no-console subsystem
        try:
            import os as _os
            _exe = _sys.executable or ""
            _dir = _os.path.dirname(_exe)
            _candidates = [
                _os.path.join(_dir, "pythonw.exe"),
                _os.path.join(_dir, "pythonw"),
            ]
            _pyw = next((c for c in _candidates if c and _os.path.isfile(c)), None)
            if _pyw:
                # Point multiprocessing at pythonw for spawn
                try:
                    from multiprocessing import spawn as _spawn
                    _spawn.set_executable(_pyw)
                except Exception:
                    pass
                try:
                    _mp.set_executable(_pyw)
                except Exception:
                    pass
        except Exception:
            pass

        CREATE_NO_WINDOW = 0x08000000
        try:
            import multiprocessing.popen_spawn_win32 as _popen_win32
        except Exception:
            return

        _OrigPopen = _popen_win32.Popen

        class _NoWindowPopen(_OrigPopen):
            def __init__(self, process_obj):
                # Wrap base init: patch subprocess.Popen temporarily
                import subprocess as _sp
                _RealPopen = _sp.Popen

                class _HiddenPopen(_RealPopen):
                    def __init__(self, *args, **kwargs):
                        # Merge CREATE_NO_WINDOW into creationflags
                        cf = kwargs.get("creationflags", 0) or 0
                        kwargs["creationflags"] = cf | CREATE_NO_WINDOW
                        # Also hide via STARTUPINFO if provided/possible
                        try:
                            si = kwargs.get("startupinfo")
                            if si is None:
                                si = _sp.STARTUPINFO()
                                kwargs["startupinfo"] = si
                            si.dwFlags |= getattr(_sp, "STARTF_USESHOWWINDOW", 1)
                            si.wShowWindow = 0  # SW_HIDE
                        except Exception:
                            pass
                        super().__init__(*args, **kwargs)

                _sp.Popen = _HiddenPopen
                try:
                    super().__init__(process_obj)
                finally:
                    _sp.Popen = _RealPopen

        _popen_win32.Popen = _NoWindowPopen
    except Exception:
        pass


try:
    _hashstart_hide_mp_consoles()
except Exception:
    pass
# --- end HashStart console hide ---

def _hashstart_cap_cpu_workers(n):
    """Never saturate every core — leave at least one free."""
    try:
        import os as _os
        n = int(n or 1)
        cores = _os.cpu_count() or 2
        return max(1, min(n, max(1, cores - 1)))
    except Exception:
        return max(1, int(n or 1))



GPU_BATCH = 1 << 22

DIFF1_TARGET = 0x00000000FFFF0000000000000000000000000000000000000000000000000000
SCRYPT_DIFF1 = 0x0000FFFF00000000000000000000000000000000000000000000000000000000
BATCH = 8192
SCRYPT_BATCH = 64
XMR_NONCE_OFFSET = 39
XMR_BATCH = 8
BLOB_SIZE = 16384
HIGH_PRIORITY_CLASS = 0x00000080
FAST_SCAN = False
scan_nonces = None
_FAST_SCAN_TRIED = False


def _load_fast_scan() -> bool:
    """Numba SHA-256d tek kad krene rudarenje, ne pri otvaranju prozora."""
    global FAST_SCAN, scan_nonces, BATCH, _FAST_SCAN_TRIED
    if _FAST_SCAN_TRIED:
        return FAST_SCAN
    _FAST_SCAN_TRIED = True
    try:
        from sha256_scan import scan_nonces as _scan

        scan_nonces = _scan
        FAST_SCAN = True
        BATCH = 262144
    except Exception:
        FAST_SCAN = False
        scan_nonces = None
        BATCH = 8192
    return FAST_SCAN

StatusCb = Callable[[str], None]
ProgressCb = Callable[[float, int, int], None]
StatsCb = Callable[[dict], None]
LogCb = Callable[[str], None]


def _sha256(data: bytes = b""):
    try:
        return hashlib.sha256(data, usedforsecurity=False)
    except TypeError:
        return hashlib.sha256(data)


def sha256d(data: bytes) -> bytes:
    return _sha256(_sha256(data).digest()).digest()


def difficulty_to_target(difficulty: float, diff1: int = DIFF1_TARGET) -> int:
    if difficulty <= 0:
        difficulty = 1.0
    return int(diff1 / difficulty)


def scrypt_pow(header80: bytes) -> bytes:
    return hashlib.scrypt(header80, salt=header80, n=1024, r=1, p=1, dklen=32)


def target_to_be(target: int) -> bytes:
    return target.to_bytes(32, "big")


def build_merkle_root(coinbase: bytes, branches: list) -> bytes:
    merkle = sha256d(coinbase)
    for branch in branches:
        merkle = sha256d(merkle + bytes.fromhex(branch))
    return merkle


def meets_target(digest: bytes, target_be: bytes) -> bool:
    for i in range(32):
        a = digest[31 - i]
        b = target_be[i]
        if a < b:
            return True
        if a > b:
            return False
    return True


def _tune_worker(worker_id: int) -> None:
    if os.name != "nt":
        return
    try:
        k32 = ctypes.windll.kernel32
        handle = k32.GetCurrentProcess()
        k32.SetPriorityClass(handle, HIGH_PRIORITY_CLASS)
        cores = min(cpu_count() or 1, 64)
        k32.SetProcessAffinityMask(handle, 1 << (worker_id % cores))
    except OSError:
        pass


def worker_loop(
    worker_id: int,
    job_blob,
    job_generation,
    hash_counter,
    share_queue,
    stop_flag,
) -> None:
    _tune_worker(worker_id)
    _load_fast_scan()
    import numpy as np

    sha256 = _sha256
    pack_into = struct.pack_into
    last_gen = -1
    job_id = ''
    extranonce2 = ''
    ntime = ''
    target_be = b'\xff' * 32
    target_arr = None
    prefix_arr = None
    mid = None
    chunk = bytearray(16)
    nonce = worker_id
    out_nonces = np.zeros(32, dtype=np.uint32) if FAST_SCAN else None

    while not stop_flag.value:
        gen = job_generation.value
        if gen != last_gen:
            with job_blob.get_lock():
                raw = bytes(job_blob[:]).split(b'\x00', 1)[0]
            if not raw:
                time.sleep(0.02)
                continue
            payload = json.loads(raw.decode('utf-8'))
            en2_size = int(payload.get('en2_size') or 4)
            extranonce2 = worker_id.to_bytes(en2_size, 'big').hex()
            coinbase = bytes.fromhex(
                payload['coinb1'] + payload['extranonce1'] + extranonce2 + payload['coinb2']
            )
            merkle_root = build_merkle_root(coinbase, list(payload['merkle']))
            prefix = (
                bytes.fromhex(payload['version'])
                + bytes.fromhex(payload['prevhash'])
                + merkle_root[::-1]
                + bytes.fromhex(payload['ntime'])
                + bytes.fromhex(payload['nbits'])
            )
            job_id = payload['job_id']
            ntime = payload['ntime']
            target_be = target_to_be(int(payload['target']))
            if FAST_SCAN:
                prefix_arr = np.frombuffer(prefix, dtype=np.uint8).copy()
                target_arr = np.frombuffer(target_be, dtype=np.uint8).copy()
            else:
                mid = sha256(prefix[:64])
                chunk[0:12] = prefix[64:76]
            nonce = worker_id
            last_gen = gen

        if FAST_SCAN:
            if prefix_arr is None:
                time.sleep(0.02)
                continue
            found = scan_nonces(prefix_arr, nonce, BATCH, target_arr, out_nonces)
            for i in range(int(found)):
                used = int(out_nonces[i])
                share_queue.put(
                    {
                        'job_id': job_id,
                        'extranonce2': extranonce2,
                        'ntime': ntime,
                        'nonce': f'{used:08x}',
                    }
                )
            hash_counter.value += BATCH
            nonce = (nonce + BATCH) & 0xFFFFFFFF
            continue

        if mid is None:
            time.sleep(0.02)
            continue
        for _ in range(BATCH):
            pack_into('<I', chunk, 12, nonce)
            first = mid.copy()
            first.update(chunk)
            digest = sha256(first.digest()).digest()
            if int.from_bytes(digest, 'little') <= int.from_bytes(target_be, 'big'):
                share_queue.put(
                    {
                        'job_id': job_id,
                        'extranonce2': extranonce2,
                        'ntime': ntime,
                        'nonce': f'{nonce:08x}',
                    }
                )
            nonce = (nonce + 1) & 0xFFFFFFFF
        hash_counter.value += BATCH


def scrypt_worker_loop(
    worker_id: int,
    job_blob,
    job_generation,
    hash_counter,
    share_queue,
    stop_flag,
) -> None:
    _tune_worker(worker_id)
    pack_into = struct.pack_into
    last_gen = -1
    job_id = ""
    extranonce2 = ""
    ntime = ""
    target_int = 2**256 - 1
    header = bytearray(80)
    nonce = worker_id
    while not stop_flag.value:
        gen = job_generation.value
        if gen != last_gen:
            with job_blob.get_lock():
                raw = bytes(job_blob[:]).split(b"\x00", 1)[0]
            if not raw:
                time.sleep(0.02)
                continue
            payload = json.loads(raw.decode("utf-8"))
            en2_size = int(payload.get("en2_size") or 4)
            extranonce2 = worker_id.to_bytes(en2_size, "big").hex()
            coinbase = bytes.fromhex(
                payload["coinb1"] + payload["extranonce1"] + extranonce2 + payload["coinb2"]
            )
            merkle_root = build_merkle_root(coinbase, list(payload["merkle"]))
            prefix = (
                bytes.fromhex(payload["version"])
                + bytes.fromhex(payload["prevhash"])
                + merkle_root[::-1]
                + bytes.fromhex(payload["ntime"])
                + bytes.fromhex(payload["nbits"])
            )
            header[0:76] = prefix
            job_id = payload["job_id"]
            ntime = payload["ntime"]
            target_int = int(payload["target"])
            nonce = worker_id
            last_gen = gen
        if last_gen < 0:
            time.sleep(0.02)
            continue
        for _ in range(SCRYPT_BATCH):
            pack_into("<I", header, 76, nonce)
            digest = scrypt_pow(bytes(header))
            if int.from_bytes(digest, "little") <= target_int:
                share_queue.put(
                    {
                        "job_id": job_id,
                        "extranonce2": extranonce2,
                        "ntime": ntime,
                        "nonce": f"{nonce:08x}",
                    }
                )
            nonce = (nonce + 1) & 0xFFFFFFFF
        hash_counter.value += SCRYPT_BATCH


def scrypt_gpu_worker_loop(
    job_blob,
    job_generation,
    hash_counter,
    share_queue,
    stop_flag,
    gpu_index=0,
    gpu_count=1,
    on_log=None,
) -> None:
    from scrypt_gpu import get_scrypt_gpu
    import numpy as np

    log = on_log or (lambda _line: None)
    gpu = get_scrypt_gpu(int(gpu_index))
    kh = gpu.tuned_rate / 1e3
    log(f"GPU {gpu.device_index} {gpu.device_name} Scrypt spreman · {kh:.0f} kH/s")
    last_gen = -1
    job_id = ""
    extranonce2 = ""
    ntime = ""
    prefix_arr = None
    target_arr = None
    nonce = 0
    gpu_count = max(int(gpu_count), 1)
    while not stop_flag.value:
        gen = job_generation.value
        if gen != last_gen:
            with job_blob.get_lock():
                raw = bytes(job_blob[:]).split(b"\x00", 1)[0]
            if not raw:
                time.sleep(0.02)
                continue
            payload = json.loads(raw.decode("utf-8"))
            en2_size = int(payload.get("en2_size") or 4)
            extranonce2 = (1 + int(gpu_index)).to_bytes(en2_size, "big").hex()
            coinbase = bytes.fromhex(
                payload["coinb1"] + payload["extranonce1"] + extranonce2 + payload["coinb2"]
            )
            merkle_root = build_merkle_root(coinbase, list(payload["merkle"]))
            prefix = (
                bytes.fromhex(payload["version"])
                + bytes.fromhex(payload["prevhash"])
                + merkle_root[::-1]
                + bytes.fromhex(payload["ntime"])
                + bytes.fromhex(payload["nbits"])
            )
            job_id = payload["job_id"]
            ntime = payload["ntime"]
            target_be = target_to_be(int(payload["target"]))
            prefix_arr = np.frombuffer(prefix, dtype=np.uint8).copy()
            target_arr = np.frombuffer(target_be, dtype=np.uint8).copy()
            nonce = int(gpu_index) * int(getattr(gpu, "batch_size", 1024))
            last_gen = gen
        if prefix_arr is None:
            time.sleep(0.02)
            continue
        batch = int(getattr(gpu, "batch_size", 1024))
        _found_n, found, hashed = gpu.scan(prefix_arr, nonce, batch, target_arr)
        for used in found:
            share_queue.put(
                {
                    "job_id": job_id,
                    "extranonce2": extranonce2,
                    "ntime": ntime,
                    "nonce": f"{int(used):08x}",
                }
            )
        stepped = int(hashed) if hashed else batch
        hash_counter.value += stepped
        nonce = (nonce + stepped * gpu_count) & 0xFFFFFFFF


def xmr_worker_loop(
    worker_id: int,
    n_workers: int,
    job_blob,
    job_generation,
    hash_counter,
    share_queue,
    stop_flag,
) -> None:
    from randomx_cpu import RandomXHasher, meets_xmr_target

    hasher = RandomXHasher(b"\x00" * 32, full_mem=False)
    last_gen = -1
    job_id = ""
    target = ""
    blob = bytearray()
    nonce = worker_id
    while not stop_flag.value:
        gen = job_generation.value
        if gen != last_gen:
            with job_blob.get_lock():
                raw = bytes(job_blob[:]).split(b"\x00", 1)[0]
            if not raw:
                time.sleep(0.02)
                continue
            payload = json.loads(raw.decode("utf-8"))
            blob = bytearray.fromhex(payload["blob"])
            if len(blob) <= XMR_NONCE_OFFSET + 4:
                time.sleep(0.05)
                continue
            hasher.set_key(bytes.fromhex(payload["seed_hash"]))
            job_id = payload["job_id"]
            target = payload["target"]
            nonce = worker_id
            last_gen = gen
        if last_gen < 0:
            time.sleep(0.02)
            continue
        for _ in range(XMR_BATCH):
            struct.pack_into("<I", blob, XMR_NONCE_OFFSET, nonce)
            digest = hasher.hash(bytes(blob))
            if meets_xmr_target(digest, target):
                share_queue.put(
                    {
                        "job_id": job_id,
                        "nonce": blob[XMR_NONCE_OFFSET : XMR_NONCE_OFFSET + 4].hex(),
                        "result": digest.hex(),
                    }
                )
            nonce = (nonce + n_workers) & 0xFFFFFFFF
        hash_counter.value += XMR_BATCH


def gpu_worker_loop(
    job_blob,
    job_generation,
    hash_counter,
    share_queue,
    stop_flag,
    gpu_index=0,
    gpu_count=1,
    on_log=None,
) -> None:
    from sha256_gpu import get_gpu
    import numpy as np

    log = on_log or (lambda _line: None)
    gpu = get_gpu(int(gpu_index))
    mh = gpu.tuned_rate / 1e6
    log(f"GPU {gpu.device_index} {gpu.device_name} spreman · {mh:.0f} MH/s · nper={gpu.nper} local={gpu.local_size}")
    last_gen = -1
    job_id = ""
    extranonce2 = ""
    ntime = ""
    prefix_arr = None
    target_arr = None
    nonce = 0
    gpu_count = max(int(gpu_count), 1)
    while not stop_flag.value:
        gen = job_generation.value
        if gen != last_gen:
            with job_blob.get_lock():
                raw = bytes(job_blob[:]).split(b"\x00", 1)[0]
            if not raw:
                time.sleep(0.02)
                continue
            payload = json.loads(raw.decode("utf-8"))
            en2_size = int(payload.get("en2_size") or 4)
            extranonce2 = (1 + int(gpu_index)).to_bytes(en2_size, "big").hex()
            coinbase = bytes.fromhex(
                payload["coinb1"] + payload["extranonce1"] + extranonce2 + payload["coinb2"]
            )
            merkle_root = build_merkle_root(coinbase, list(payload["merkle"]))
            prefix = (
                bytes.fromhex(payload["version"])
                + bytes.fromhex(payload["prevhash"])
                + merkle_root[::-1]
                + bytes.fromhex(payload["ntime"])
                + bytes.fromhex(payload["nbits"])
            )
            job_id = payload["job_id"]
            ntime = payload["ntime"]
            target_be = target_to_be(int(payload["target"]))
            prefix_arr = np.frombuffer(prefix, dtype=np.uint8).copy()
            target_arr = np.frombuffer(target_be, dtype=np.uint8).copy()
            nonce = int(gpu_index) * int(getattr(gpu, "batch_size", GPU_BATCH))
            last_gen = gen
        if prefix_arr is None:
            time.sleep(0.02)
            continue
        batch = int(getattr(gpu, "batch_size", GPU_BATCH))
        found_n, found, hashed = gpu.scan(prefix_arr, nonce, batch, target_arr)
        for used in found:
            share_queue.put(
                {
                    "job_id": job_id,
                    "extranonce2": extranonce2,
                    "ntime": ntime,
                    "nonce": f"{int(used):08x}",
                }
            )
        stepped = int(hashed) if hashed else batch
        hash_counter.value += stepped
        nonce = (nonce + stepped * gpu_count) & 0xFFFFFFFF


def format_rate(rate: float) -> str:
    units = ["H/s", "kH/s", "MH/s", "GH/s"]
    value = float(rate)
    unit = units[0]
    for candidate in units:
        unit = candidate
        if value < 1000:
            break
        value /= 1000.0
    if value >= 100:
        return f"{value:.0f} {unit}"
    if value >= 10:
        return f"{value:.1f} {unit}"
    return f"{value:.2f} {unit}"


def bump_gpu_intensity(direction: int = 1) -> list[str]:
    """Prema MAX OpenCL koracima, ili jedan korak nazad. Ne izumije hes."""
    notes: list[str] = []
    toward_max = int(direction) > 0
    try:
        if toward_max:
            from sha256_gpu import max_all_gpus

            notes.extend(max_all_gpus())
        else:
            from sha256_gpu import bump_all_gpus

            notes.extend(bump_all_gpus(-1))
    except Exception as exc:
        notes.append(f"SHA256 GPU: {exc}")
    try:
        if toward_max:
            from scrypt_gpu import max_all_gpus as sc_max

            notes.extend(sc_max())
        else:
            from scrypt_gpu import bump_all_gpus as sc_bump

            notes.extend(sc_bump(-1))
    except Exception as exc:
        notes.append(f"Scrypt GPU: {exc}")
    return [n for n in notes if n]


class MinerEngine:
    def __init__(
        self,
        root_dir: Path,
        on_status: StatusCb | None = None,
        on_progress: ProgressCb | None = None,
        on_stats: StatsCb | None = None,
        on_log: LogCb | None = None,
    ) -> None:
        self.root_dir = root_dir
        self.on_status = on_status or (lambda _msg: None)
        self.on_progress = on_progress or (lambda *_args: None)
        self.on_stats = on_stats or (lambda _stats: None)
        self.on_log = on_log or (lambda _line: None)
        self._stop = threading.Event()
        self._sock = None
        self._net_thread = None
        self._meter_thread = None
        self._msg_id = 0
        self.extranonce1 = ""
        self.extranonce2_size = 4
        self.difficulty = 1.0
        self._n_workers = max(cpu_count() or 1, 1)
        self.coin = {
            "code": "BTC",
            "algo": "sha256d",
            "diff1": DIFF1_TARGET,
            "password": "x",
            "mineable": True,
            "pool_login": "{address}.gpu",
            "solo_login": "{address}",
        }
        self.mode = "pool"
        self.worker_name = ""
        self.stats = {
            "hashrate": "0 H/s",
            "hashrate_hs": 0.0,
            "accepted": 0,
            "rejected": 0,
            "total": 0,
            "engine": f"sha256d x{self._n_workers}",
            "cpu": "",
        }
        self._job_generation = None
        self._hash_counter = None
        self._stop_flag = None
        self._share_queue = None
        self._job_blob = None
        self._workers = []
        self._gpu_threads = []
        self._gpu_names = []
        self._gpu_count = 0
        self._scrypt_gpu = False
        self._asic_ips = []
        self._asic_devices: list[dict] = []
        self._asic_active = False
        self.xmr_session = ""
        self._rpc_kind = {}

    def is_running(self) -> bool:
        if self._net_thread is not None and self._net_thread.is_alive():
            return True
        return bool(self._asic_active) and not self._stop.is_set()

    def _list_gpus(self) -> list[str]:
        try:
            from sha256_gpu import list_gpu_names

            return list_gpu_names()
        except Exception as exc:
            self.on_log(f"OpenCL popis GPU-a: {exc}")
            return []

    def ensure_engine(self) -> Path:
        algo = (self.coin or {}).get("algo")
        self._gpu_names = []
        self._gpu_count = 0
        if algo == "scrypt":
            self.on_progress(1.0, 1, 1)
            names = self._list_gpus()
            if names:
                self._scrypt_gpu = True
                self._gpu_names = names
                self._gpu_count = len(names)
                self.stats["engine"] = "GPU Scrypt " + " + ".join(names)
                self.on_status(f"Scrypt na {len(names)} GPU: {', '.join(names)}")
                self.on_log(f"Scrypt GPU-evi: {', '.join(names)}")
                return self.root_dir
            self._scrypt_gpu = False
            if self._asic_ips:
                self.stats["engine"] = "ASIC Scrypt"
                self.on_status("Nema lokalnog GPU-a · ASIC Scrypt")
                self.on_log("Nema OpenCL GPU-a, ostaje ASIC farm.")
                return self.root_dir
            n = self._n_workers
            self.stats["engine"] = f"CPU Scrypt x{n}"
            self.on_status(f"CPU Scrypt x{n} (nema OpenCL GPU-a)")
            self.on_log("GPU Scrypt fallback na CPU")
            return self.root_dir
        if algo == "randomx":
            from randomx_cpu import RandomXHasher, _dll_path

            self.on_progress(1.0, 1, 1)
            self.on_status("Inicijaliziram RandomX...")
            if not _dll_path().is_file():
                raise RuntimeError(f"Nema RandomX DLL: {_dll_path()}")
            RandomXHasher(b"init", full_mem=False)
            n = max(1, min(self._n_workers, 4))
            self._xmr_workers = n
            self.stats["engine"] = f"RandomX CPU x{n}"
            self.on_status(f"RandomX spreman ({n} CPU worker-a, light mode)")
            self.on_log(f"RandomX DLL OK · light cache · {n} procesa")
            return self.root_dir
        if algo in ("kawpow", "etchash", "fishhash", "pearlpow"):
            from ethash import selfcheck

            self.on_progress(1.0, 1, 1)
            selfcheck()
            names = self._list_gpus()
            if names:
                self._gpu_names = names
                self._gpu_count = len(names)
                self.stats["engine"] = f"GPU {algo} " + " + ".join(names)
                self.on_status(f"{algo} na {len(names)} GPU")
                self.on_log(f"{algo} GPU: {', '.join(names)}")
                return self.root_dir
            if self._asic_ips and algo == "kawpow":
                self.stats["engine"] = "ASIC KawPow"
                self.on_status("KawPow ASIC farm")
                return self.root_dir
            n = max(1, self._n_workers)
            self._eth_cpu_workers = n
            self.stats["engine"] = f"CPU {algo} x{n}"
            self.on_status(f"CPU {algo} x{n} (nema OpenCL GPU-a)")
            self.on_log(f"{algo} fallback na CPU cache/light")
            return self.root_dir
        if algo and algo != "sha256d":
            raise RuntimeError(f"Algoritam {algo} nije ugraden u HashStart.")
        self.on_progress(1.0, 1, 1)
        names = self._list_gpus()
        if names:
            self._gpu_names = names
            self._gpu_count = len(names)
            self.stats["engine"] = "GPU " + " + ".join(names)
            self.on_status(f"{len(names)} GPU: {', '.join(names)}")
            self.on_log(f"SHA-256d GPU-evi: {', '.join(names)}")
            return self.root_dir
        if self._asic_ips:
            self.stats["engine"] = "ASIC SHA-256d"
            self.on_status("Nema lokalnog GPU-a · ASIC SHA-256d")
            self.on_log("Nema OpenCL GPU-a, ostaje ASIC farm.")
            return self.root_dir
        raise RuntimeError("Nema OpenCL GPU-a. Spoji GPU ili unesi ASIC IP na LAN-u.")

    def start(
        self,
        address: str,
        host: str,
        port: int,
        coin: dict | None = None,
        mode: str = "pool",
        asic_ips: list[str] | None = None,
        asic_devices: list[dict] | None = None,
        payout: str = "NATIVE",
        payout_tag: str = "",
        login: str | None = None,
    ) -> None:
        if self.is_running():
            return
        from coins import ETH_ALGOS, worker_login

        self.coin = coin or self.coin
        self.mode = "solo" if mode == "solo" else "pool"
        if not self.coin.get("mineable"):
            raise RuntimeError(self.coin.get("note") or "Ovaj coin se ne moze rudariti.")
        algo = (self.coin or {}).get("algo")
        self._asic_devices = [d for d in (asic_devices or []) if isinstance(d, dict) and d.get("host")]
        self._asic_ips = list(asic_ips or [])
        if not self._asic_ips and self._asic_devices:
            self._asic_ips = [str(d.get("host")) for d in self._asic_devices if d.get("host")]
        if self._asic_ips and algo == "randomx":
            self.on_log("ASIC cgminer API je za SHA-256/Scrypt, ne za RandomX. Zanemarujem ASIC IP-ove.")
            self._asic_ips = []
            self._asic_devices = []
        if self._asic_ips and algo in ETH_ALGOS and not self.coin.get("asic"):
            self.on_log("Ovaj algo nema cgminer ASIC API. Zanemarujem ASIC IP-ove.")
            self._asic_ips = []
            self._asic_devices = []
        self.worker_name = login or worker_login(self.coin, address, self.mode, payout=payout, payout_tag=payout_tag)
        self.on_log(f"Login {self.worker_name} @ {host}:{port}")
        self.ensure_engine()
        self._stop.clear()
        self._keep_awake(True)
        self._asic_active = bool(self._asic_ips)
        if self._asic_ips:
            self._push_asics(host, int(port), address)
        local = self._needs_local_hashing()
        if not local:
            self.on_status("ASIC farm · ovaj PC ne hasha")
            self.on_stats(dict(self.stats))
            return
        self._job_generation = Value("i", 0)
        self._hash_counter = RawValue("Q", 0)
        self._stop_flag = Value("i", 0)
        self._share_queue = Queue()
        self._job_blob = Array("B", BLOB_SIZE)
        self.stats.update({"hashrate": "0 H/s", "hashrate_hs": 0.0, "accepted": 0, "rejected": 0, "total": 0})
        self.on_stats(dict(self.stats))
        self._spawn_workers()
        if algo == "randomx":
            net_loop = self._xmr_network_loop
        elif algo in ETH_ALGOS:
            net_loop = self._eth_network_loop
        else:
            net_loop = self._network_loop
        self._net_thread = threading.Thread(
            target=net_loop,
            args=(self.worker_name, host, int(port)),
            daemon=True,
        )
        self._meter_thread = threading.Thread(target=self._meter_loop, daemon=True)
        self._net_thread.start()
        self._meter_thread.start()

    def _needs_local_hashing(self) -> bool:
        algo = (self.coin or {}).get("algo")
        if algo in ("randomx", "kawpow", "etchash", "fishhash", "pearlpow"):
            if algo == "kawpow" and self._asic_ips and self._gpu_count <= 0:
                return False
            return True
        if self._gpu_count > 0:
            return True
        if algo == "scrypt" and not self._scrypt_gpu:
            return True
        return False

    def _push_asics(self, host: str, port: int, address: str) -> None:
        from coins import format_address
        from devices import push_found_devices, push_stratum

        user = self.worker_name or format_address(self.coin, address)
        password = (self.coin or {}).get("password") or "x"
        devices = list(getattr(self, "_asic_devices", None) or [])
        ips = [ip for ip in list(self._asic_ips) if not str(ip).upper().startswith("COM")]
        algo = str((self.coin or {}).get("algo") or "")
        if algo not in ("sha256d", "scrypt"):
            self.on_log("LAN uredaji (NM Miner/NerdMiner/Bitaxe/ASIC) rade SHA-256/Scrypt — ovaj algo ih preskace.")
            return

        def run() -> None:
            ok = 0
            notes: list[str] = []
            if algo == "scrypt":
                from asic import apply_pool, probe_asic

                for ip in ips:
                    try:
                        if not probe_asic(ip):
                            self.on_log(f"{ip}: Bitaxe/NerdMiner je SHA-256, ne Scrypt — preskacem.")
                            continue
                        msg = apply_pool(ip, f"stratum+tcp://{host}:{int(port)}", user, password)
                        notes.append(msg)
                    except Exception as exc:
                        notes.append(f"{ip}: {exc}")
            elif devices:
                notes = push_found_devices(devices, host, int(port), user, password)
            else:
                for ip in ips:
                    try:
                        notes.append(push_stratum(ip, host, int(port), user, password))
                    except Exception as exc:
                        notes.append(f"{ip}: {exc}")
            for msg in notes:
                self.on_log(msg)
                low = msg.lower()
                if "nema cgminer" not in low and "nije primio" not in low and "web ui" not in low and "nema hosta" not in low and "nema lan" not in low:
                    ok += 1
            total = len(devices) or len(ips)
            self.on_log(f"LAN uredaji: {ok}/{total} na {host}:{port} ({self.mode})")
            if ok:
                self.on_status(f"POJACANO LAPTOP + UREDAJ · {ok} na {self.mode}")

        threading.Thread(target=run, daemon=True).start()

    def _keep_awake(self, on: bool) -> None:
        if os.name != "nt":
            return
        try:
            k32 = ctypes.windll.kernel32
            es_continuous = 0x80000000
            es_system = 0x00000001
            es_away = 0x00000040
            if on:
                k32.SetThreadExecutionState(es_continuous | es_system | es_away)
            else:
                k32.SetThreadExecutionState(es_continuous)
        except Exception:
            pass

    def stop(self) -> None:
        self._stop.set()
        self._asic_active = False
        self._keep_awake(False)
        if self._stop_flag is not None:
            self._stop_flag.value = 1
        sock = self._sock
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass
        self._sock = None
        self._join_workers()
        if self._asic_ips:
            self.on_log("STOP zaustavlja samo ovaj PC. LAN uredaji nastavljaju na bazenu/solo.")
        self.on_status("Zaustavljeno")

    def _spawn_gpu_threads(self, target, copies: int = 1) -> None:
        names = self._gpu_names or ["GPU"]
        gpu_n = max(self._gpu_count, len(names), 1)
        copies = max(1, int(copies))
        total = gpu_n if copies <= 1 else gpu_n * copies
        self._gpu_threads = []
        for index in range(total):
            name = names[index % gpu_n]
            thread = threading.Thread(
                target=self._gpu_thread_guard,
                args=(target, index, total, name),
                daemon=True,
            )
            thread.start()
            self._gpu_threads.append(thread)
        self.on_log(f"Pokrecem {total} GPU thread-ova ({self.mode})")

    def _gpu_thread_guard(self, target, index: int, count: int, name: str) -> None:
        try:
            target(
                self._job_blob,
                self._job_generation,
                self._hash_counter,
                self._share_queue,
                self._stop_flag,
                index,
                count,
                self.on_log,
            )
        except Exception as exc:
            self.on_log(f"GPU {index} {name}: {exc}")

    def _spawn_workers(self) -> None:
        algo = (self.coin or {}).get("algo")
        self._workers = []
        self._gpu_threads = []
        if algo == "scrypt":
            if self._scrypt_gpu:
                self.stats["engine"] = "GPU Scrypt " + " + ".join(self._gpu_names)
                self._spawn_gpu_threads(scrypt_gpu_worker_loop)
                return
            n = _hashstart_cap_cpu_workers(self._n_workers)  # HashStart fix: CPU worker cap
            self.stats["engine"] = f"CPU Scrypt x{n}"
            for worker_id in range(n):
                proc = Process(
                    target=scrypt_worker_loop,
                    args=(
                        worker_id,
                        self._job_blob,
                        self._job_generation,
                        self._hash_counter,
                        self._share_queue,
                        self._stop_flag,
                    ),
                )
                proc.daemon = True
                proc.start()
                self._workers.append(proc)
            self.on_log(f"CPU Scrypt hashing: {n} procesa ({self.mode})")
            return
        if algo in ("kawpow", "etchash", "fishhash", "pearlpow"):
            from eth_gpu import eth_cpu_worker_loop, eth_gpu_worker_loop

            if self._gpu_count > 0:
                copies = 1  # HashStart fix: was max(8,...); 1 copy per GPU avoids PC freeze
                self.stats["engine"] = f"GPU {algo} x{copies} " + " + ".join(self._gpu_names)
                self._spawn_gpu_threads(eth_gpu_worker_loop, copies=copies)
                return
            n = int(getattr(self, "_eth_cpu_workers", 0) or max(1, self._n_workers))
            self.stats["engine"] = f"CPU {algo} x{n}"
            for worker_id in range(n):
                proc = Process(
                    target=eth_cpu_worker_loop,
                    args=(
                        worker_id,
                        n,
                        self._job_blob,
                        self._job_generation,
                        self._hash_counter,
                        self._share_queue,
                        self._stop_flag,
                    ),
                )
                proc.daemon = True
                proc.start()
                self._workers.append(proc)
            self.on_log(f"{algo} CPU hashing: {n} procesa ({self.mode})")
            return
        if algo == "randomx":
            n = int(getattr(self, "_xmr_workers", 0) or max(1, min(self._n_workers, 4)))
            self.stats["engine"] = f"RandomX CPU x{n}"
            for worker_id in range(n):
                proc = Process(
                    target=xmr_worker_loop,
                    args=(
                        worker_id,
                        n,
                        self._job_blob,
                        self._job_generation,
                        self._hash_counter,
                        self._share_queue,
                        self._stop_flag,
                    ),
                )
                proc.daemon = True
                proc.start()
                self._workers.append(proc)
            self.on_log(f"RandomX hashing: {n} procesa ({self.mode})")
            return
        self.stats["engine"] = "GPU " + " + ".join(self._gpu_names)
        self._spawn_gpu_threads(gpu_worker_loop)

    def _join_workers(self) -> None:
        for thread in list(self._gpu_threads):
            thread.join(timeout=3)
        self._gpu_threads = []
        thread = getattr(self, "_gpu_thread", None)
        if thread is not None:
            thread.join(timeout=3)
        self._gpu_thread = None
        for proc in self._workers:
            proc.terminate()
            proc.join(timeout=2)
        self._workers = []

    def _next_id(self) -> int:
        self._msg_id += 1
        return self._msg_id

    def _rpc(self, method: str, params: list, kind: str) -> None:
        msg_id = self._next_id()
        self._rpc_kind[msg_id] = kind
        self._send({"id": msg_id, "method": method, "params": params})

    def _send(self, payload: dict) -> None:
        raw = (json.dumps(payload) + "\n").encode("utf-8")
        if self._sock is not None:
            self._sock.sendall(raw)

    def _xmr_network_loop(self, worker: str, host: str, port: int) -> None:
        delay = 1.0
        while not self._stop.is_set():
            sock = None
            try:
                self.on_status(f"Spajam na {host}:{port} (XMR {self.mode})...")
                sock = socket.create_connection((host, port), timeout=20)
                sock.settimeout(0.2)
                self._sock = sock
                delay = 1.0
                self._rpc_kind = {}
                self.xmr_session = ""
                password = (self.coin or {}).get("password") or "x"
                msg_id = self._next_id()
                self._rpc_kind[msg_id] = "login"
                self._send(
                    {
                        "id": msg_id,
                        "jsonrpc": "2.0",
                        "method": "login",
                        "params": {"login": worker, "pass": password, "agent": "Aura/1.0"},
                    }
                )
                self.on_status("Rudarenje u tijeku")
                buffer = ""
                last_keep = time.perf_counter()
                while not self._stop.is_set():
                    self._xmr_drain_shares()
                    if self.xmr_session and time.perf_counter() - last_keep > 60:
                        kid = self._next_id()
                        self._rpc_kind[kid] = "keepalived"
                        self._send(
                            {
                                "id": kid,
                                "jsonrpc": "2.0",
                                "method": "keepalived",
                                "params": {"id": self.xmr_session},
                            }
                        )
                        last_keep = time.perf_counter()
                    try:
                        chunk = sock.recv(8192)
                    except socket.timeout:
                        continue
                    if not chunk:
                        raise ConnectionError("Pool je zatvorio vezu")
                    buffer += chunk.decode("utf-8", errors="replace")
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if line:
                            self._handle_xmr_message(line)
            except Exception as exc:
                if self._stop.is_set():
                    break
                self.on_status(f"Trazim bazen {host}:{port}... {exc}")
                self.on_log(str(exc))
                self._stop.wait(delay)
                delay = min(delay * 1.5, 20)
            finally:
                if sock is not None:
                    try:
                        sock.close()
                    except OSError:
                        pass
                if self._sock is sock:
                    self._sock = None
        if self._stop_flag is not None:
            self._stop_flag.value = 1

    def _xmr_drain_shares(self) -> None:
        if self._share_queue is None or not self.xmr_session:
            return
        try:
            while True:
                share = self._share_queue.get_nowait()
                msg_id = self._next_id()
                self._rpc_kind[msg_id] = "submit"
                self._send(
                    {
                        "id": msg_id,
                        "jsonrpc": "2.0",
                        "method": "submit",
                        "params": {
                            "id": self.xmr_session,
                            "job_id": share["job_id"],
                            "nonce": share["nonce"],
                            "result": share["result"],
                        },
                    }
                )
                self.on_log(f"Saljem XMR share job={share['job_id']} nonce={share['nonce']}")
        except queue.Empty:
            pass

    def _handle_xmr_message(self, line: str) -> None:
        self.on_log(line[:300])
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            return
        if msg.get("method") == "job":
            self._install_xmr_job(msg.get("params") or {})
            return
        if msg.get("id") is None:
            return
        kind = self._rpc_kind.pop(msg.get("id"), "")
        result = msg.get("result")
        error = msg.get("error")
        if kind == "login":
            if error or not isinstance(result, dict):
                self.on_log(f"XMR login fail: {error or result}")
                return
            self.xmr_session = str(result.get("id") or "")
            self.on_log(f"XMR login OK session={self.xmr_session}")
            job = result.get("job")
            if isinstance(job, dict):
                self._install_xmr_job(job)
            return
        if kind != "submit":
            return
        self.stats["total"] = int(self.stats["total"]) + 1
        if error or result is False:
            self.stats["rejected"] = int(self.stats["rejected"]) + 1
            self.on_log(f"Odbijeno: {error or result}")
        else:
            self.stats["accepted"] = int(self.stats["accepted"]) + 1
            self.on_log("Share prihvacen")
        self.on_stats(dict(self.stats))

    def _install_xmr_job(self, job: dict) -> None:
        if not job or self._job_blob is None:
            return
        blob = str(job.get("blob") or "")
        job_id = str(job.get("job_id") or "")
        target = str(job.get("target") or "")
        seed = str(job.get("seed_hash") or "")
        if not blob or not job_id or not target or not seed:
            return
        payload = json.dumps(
            {"blob": blob, "job_id": job_id, "target": target, "seed_hash": seed},
            separators=(",", ":"),
        ).encode("utf-8")
        if len(payload) >= BLOB_SIZE - 1:
            self.on_log("XMR job preskocen (prevelik)")
            return
        data = payload + b"\x00"
        with self._job_blob.get_lock():
            self._job_blob[: len(data)] = data
        self._job_generation.value += 1
        self.on_log(f"XMR job {job_id} target={target}")

    def _eth_network_loop(self, worker: str, host: str, port: int) -> None:
        delay = 1.0
        while not self._stop.is_set():
            sock = None
            try:
                code = (self.coin or {}).get("code", "ETH")
                algo = (self.coin or {}).get("algo", "")
                self.on_status(f"Spajam na {host}:{port} ({code} {algo})...")
                sock = socket.create_connection((host, port), timeout=20)
                sock.settimeout(0.2)
                self._sock = sock
                delay = 1.0
                self._rpc_kind = {}
                self.extranonce1 = ""
                password = (self.coin or {}).get("password") or "x"
                self._rpc("mining.subscribe", ["Aura/1.0", "EthereumStratum/1.0.0"], "subscribe")
                self._rpc("mining.authorize", [worker, password], "authorize")
                self.on_status("Rudarenje u tijeku")
                buffer = ""
                while not self._stop.is_set():
                    self._drain_shares(worker)
                    try:
                        chunk = sock.recv(8192)
                    except socket.timeout:
                        continue
                    if not chunk:
                        raise ConnectionError("Pool je zatvorio vezu")
                    buffer += chunk.decode("utf-8", errors="replace")
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if line:
                            self._handle_eth_message(line)
            except Exception as exc:
                if self._stop.is_set():
                    break
                self.on_status(f"Trazim bazen {host}:{port}... {exc}")
                self.on_log(str(exc))
                self._stop.wait(delay)
                delay = min(delay * 1.5, 20)
            finally:
                if sock is not None:
                    try:
                        sock.close()
                    except OSError:
                        pass
                if self._sock is sock:
                    self._sock = None
        if self._stop_flag is not None:
            self._stop_flag.value = 1

    def _eth_target(self) -> int:
        diff = float(self.difficulty or 1.0)
        if diff <= 0:
            diff = 1.0
        return max((1 << 256) // int(diff), 1)

    def _handle_eth_message(self, line: str) -> None:
        self.on_log(line[:300])
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            return
        method = msg.get("method")
        if method == "mining.set_difficulty":
            params = msg.get("params") or [1]
            try:
                self.difficulty = float(params[0] or 1)
            except (TypeError, ValueError):
                self.difficulty = 1.0
            self.on_log(f"Difficulty = {self.difficulty}")
            return
        if method == "mining.notify":
            self._install_eth_job(msg.get("params") or [])
            return
        if method == "eth_getWork" or method == "mining.set_target":
            params = msg.get("params") or []
            if method == "mining.set_target" and params:
                self.difficulty = 0
                self._eth_job_target = str(params[0])
            return
        if msg.get("id") is not None and ("result" in msg or "error" in msg):
            kind = self._rpc_kind.pop(msg.get("id"), "")
            result = msg.get("result")
            error = msg.get("error")
            if kind == "subscribe":
                extra = ""
                if isinstance(result, list) and len(result) >= 2:
                    extra = str(result[1] or "")
                    if isinstance(result[0], str):
                        extra = str(result[0])
                self.extranonce1 = extra
                self.on_log(f"ETH subscribe OK extra={self.extranonce1}")
                return
            if kind == "authorize":
                self.on_log("Authorize OK" if result else f"Authorize fail: {error or result}")
                return
            if kind != "submit":
                return
            self.stats["total"] = int(self.stats["total"]) + 1
            if error or result is False:
                self.stats["rejected"] = int(self.stats["rejected"]) + 1
                self.on_log(f"Odbijeno: {error or result}")
            else:
                self.stats["accepted"] = int(self.stats["accepted"]) + 1
                self.on_log("Share prihvacen")
            self.on_stats(dict(self.stats))

    def _install_eth_job(self, params: list) -> None:
        if not params or self._job_blob is None:
            return
        job_id = str(params[0])
        header = ""
        seed = ""
        height = 0
        target = None
        if len(params) >= 4 and not isinstance(params[3], bool) and str(params[3]).lower() not in ("true", "false"):
            header = str(params[1] or "")
            seed = str(params[2] or "")
            try:
                height = int(str(params[3]), 0)
            except (TypeError, ValueError):
                height = 0
            if len(params) >= 6 and isinstance(params[5], str) and len(params[5]) >= 8:
                target = params[5]
        elif len(params) >= 3:
            seed = str(params[1] or "")
            header = str(params[2] or "")
            if len(params) >= 5 and not isinstance(params[4], bool):
                try:
                    height = int(str(params[4]), 0)
                except (TypeError, ValueError):
                    height = 0
        if not job_id or not header:
            return
        payload = json.dumps(
            {
                "kind": "eth",
                "algo": (self.coin or {}).get("algo") or "",
                "job_id": job_id,
                "header": header.replace("0x", ""),
                "seed": seed.replace("0x", ""),
                "height": height,
                "target": target or self._eth_target(),
                "extra": self.extranonce1,
            },
            separators=(",", ":"),
        ).encode("utf-8")
        if len(payload) >= BLOB_SIZE - 1:
            self.on_log("ETH job preskocen (prevelik)")
            return
        data = payload + b"\x00"
        with self._job_blob.get_lock():
            self._job_blob[: len(data)] = data
        self._job_generation.value += 1
        self.on_log(f"ETH job {job_id} h={height}")

    def _network_loop(self, worker: str, host: str, port: int) -> None:
        delay = 1.0
        while not self._stop.is_set():
            sock = None
            try:
                mode = self.mode
                code = (self.coin or {}).get("code", "BTC")
                self.on_status(f"Spajam na {host}:{port} ({code} {mode})...")
                sock = socket.create_connection((host, port), timeout=20)
                sock.settimeout(0.2)
                self._sock = sock
                delay = 1.0
                self._rpc_kind = {}
                password = (self.coin or {}).get("password") or "x"
                self._rpc("mining.subscribe", ["Aura/1.0"], "subscribe")
                self._rpc("mining.authorize", [worker, password], "authorize")
                if (self.coin or {}).get("algo") == "sha256d":
                    self._rpc("mining.suggest_difficulty", [0.00001], "suggest")
                self.on_status("Rudarenje u tijeku")
                buffer = ""
                while not self._stop.is_set():
                    self._drain_shares(worker)
                    try:
                        chunk = sock.recv(8192)
                    except socket.timeout:
                        continue
                    if not chunk:
                        raise ConnectionError("Pool je zatvorio vezu")
                    buffer += chunk.decode("utf-8", errors="replace")
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if line:
                            self._handle_message(line)
            except Exception as exc:
                if self._stop.is_set():
                    break
                self.on_status(f"Trazim bazen {host}:{port}... {exc}")
                self.on_log(str(exc))
                self._stop.wait(delay)
                delay = min(delay * 1.5, 20)
            finally:
                if sock is not None:
                    try:
                        sock.close()
                    except OSError:
                        pass
                if self._sock is sock:
                    self._sock = None
        if self._stop_flag is not None:
            self._stop_flag.value = 1

    def _drain_shares(self, address: str) -> None:
        if self._share_queue is None:
            return
        try:
            while True:
                share = self._share_queue.get_nowait()
                if share.get("kind") == "eth":
                    params = [address, share["job_id"], share["nonce"]]
                    if share.get("mixhash"):
                        params.append(share["mixhash"])
                    self._rpc("mining.submit", params, "submit")
                    self.on_log(f"Saljem ETH share job={share['job_id']} nonce={share['nonce']}")
                    continue
                self._rpc(
                    "mining.submit",
                    [
                        address,
                        share["job_id"],
                        share["extranonce2"],
                        share["ntime"],
                        share["nonce"],
                    ],
                    "submit",
                )
                self.on_log(f"Saljem share job={share['job_id']} nonce={share['nonce']}")
        except queue.Empty:
            pass

    def _handle_message(self, line: str) -> None:
        self.on_log(line[:300])
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            return

        method = msg.get("method")
        if method == "mining.set_difficulty":
            params = msg.get("params") or [1]
            self.difficulty = float(params[0] or 1)
            self.on_log(f"Difficulty = {self.difficulty}")
            return
        if method == "mining.notify":
            self._install_job(msg.get("params") or [])
            return

        if msg.get("id") is not None and ("result" in msg or "error" in msg):
            kind = self._rpc_kind.pop(msg.get("id"), "")
            result = msg.get("result")
            error = msg.get("error")
            if kind == "subscribe" and isinstance(result, list) and len(result) >= 3:
                self.extranonce1 = result[1]
                self.extranonce2_size = int(result[2] or 4)
                self.on_log(f"Subscribe OK extranonce1={self.extranonce1}")
                return
            if kind == "authorize":
                self.on_log("Authorize OK" if result else f"Authorize fail: {error or result}")
                return
            if kind != "submit":
                return
            self.stats["total"] = int(self.stats["total"]) + 1
            if error or result is False:
                self.stats["rejected"] = int(self.stats["rejected"]) + 1
                self.on_log(f"Odbijeno: {error or result}")
            else:
                self.stats["accepted"] = int(self.stats["accepted"]) + 1
                self.on_log("Share prihvacen")
            self.on_stats(dict(self.stats))

    def _install_job(self, params: list) -> None:
        if len(params) < 9 or not self.extranonce1 or self._job_blob is None:
            return
        job_id, prevhash, coinb1, coinb2, merkle, version, nbits, ntime, _clean = params[:9]
        payload = json.dumps(
            {
                "job_id": job_id,
                "ntime": ntime,
                "coinb1": coinb1,
                "extranonce1": self.extranonce1,
                "coinb2": coinb2,
                "merkle": list(merkle),
                "version": version,
                "prevhash": prevhash,
                "nbits": nbits,
                "en2_size": self.extranonce2_size,
                "target": difficulty_to_target(self.difficulty, int(self.coin.get("diff1") or DIFF1_TARGET)),
                "algo": self.coin.get("algo") or "sha256d",
            },
            separators=(",", ":"),
        ).encode("utf-8")
        if len(payload) >= BLOB_SIZE - 1:
            self.on_log("Job preskocen (prevelik)")
            return
        data = payload + b"\x00"
        with self._job_blob.get_lock():
            self._job_blob[: len(data)] = data
        self._job_generation.value += 1
        self.on_log(f"Novi job {job_id}")

    def _meter_loop(self) -> None:
        last = time.perf_counter()
        last_hashes = 0
        while not self._stop.is_set():
            time.sleep(1.0)
            if self._hash_counter is None:
                continue
            now = time.perf_counter()
            hashes = int(self._hash_counter.value)
            delta = hashes - last_hashes
            elapsed = max(now - last, 0.001)
            last = now
            last_hashes = hashes
            rate = delta / elapsed
            self.stats["hashrate_hs"] = rate
            self.stats["hashrate"] = format_rate(rate)
            self.on_stats(dict(self.stats))