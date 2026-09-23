# -*- coding: utf-8 -*-
"""Aura Motor — OpenCL SHA-256d GPU scanner (desktop ASIC-style hasher)."""
from __future__ import annotations

import time
from typing import List, Sequence, Tuple

import numpy as np

try:
    import pyopencl as cl
except Exception as exc:  # pragma: no cover
    cl = None
    _IMPORT_ERR = exc
else:
    _IMPORT_ERR = None

# Compact OpenCL SHA-256d for 80-byte headers (prefix76 + nonce LE)
_KERNEL = r"""
#define ROTR(x,n) (((x)>>(n))|((x)<<(32-(n))))
#define Ch(x,y,z) (((x)&(y))^(~(x)&(z)))
#define Maj(x,y,z) (((x)&(y))^((x)&(z))^((y)&(z)))
#define S0(x) (ROTR((x),2)^ROTR((x),13)^ROTR((x),22))
#define S1(x) (ROTR((x),6)^ROTR((x),11)^ROTR((x),25))
#define s0(x) (ROTR((x),7)^ROTR((x),18)^((x)>>3))
#define s1(x) (ROTR((x),17)^ROTR((x),19)^((x)>>10))

__constant uint K[64]={
0x428a2f98U,0x71374491U,0xb5c0fbcfU,0xe9b5dba5U,0x3956c25bU,0x59f111f1U,0x923f82a4U,0xab1c5ed5U,
0xd807aa98U,0x12835b01U,0x243185beU,0x550c7dc3U,0x72be5d74U,0x80deb1feU,0x9bdc06a7U,0xc19bf174U,
0xe49b69c1U,0xefbe4786U,0x0fc19dc6U,0x240ca1ccU,0x2de92c6fU,0x4a7484aaU,0x5cb0a9dcU,0x76f988daU,
0x983e5152U,0xa831c66dU,0xb00327c8U,0xbf597fc7U,0xc6e00bf3U,0xd5a79147U,0x06ca6351U,0x14292967U,
0x27b70a85U,0x2e1b2138U,0x4d2c6dfcU,0x53380d13U,0x650a7354U,0x766a0abbU,0x81c2c92eU,0x92722c85U,
0xa2bfe8a1U,0xa81a664bU,0xc24b8b70U,0xc76c51a3U,0xd192e819U,0xd6990624U,0xf40e3585U,0x106aa070U,
0x19a4c116U,0x1e376c08U,0x2748774cU,0x34b0bcb5U,0x391c0cb3U,0x4ed8aa4aU,0x5b9cca4fU,0x682e6ff3U,
0x748f82eeU,0x78a5636fU,0x84c87814U,0x8cc70208U,0x90befffaU,0xa4506cebU,0xbef9a3f7U,0xc67178f2U};

void sha256_transform(uint *state, const uint *block){
  uint w[64];
  for(int i=0;i<16;i++) w[i]=block[i];
  for(int i=16;i<64;i++) w[i]=s1(w[i-2])+w[i-7]+s0(w[i-15])+w[i-16];
  uint a=state[0],b=state[1],c=state[2],d=state[3],e=state[4],f=state[5],g=state[6],h=state[7];
  for(int i=0;i<64;i++){
    uint t1=h+S1(e)+Ch(e,f,g)+K[i]+w[i];
    uint t2=S0(a)+Maj(a,b,c);
    h=g; g=f; f=e; e=d+t1; d=c; c=b; b=a; a=t1+t2;
  }
  state[0]+=a; state[1]+=b; state[2]+=c; state[3]+=d;
  state[4]+=e; state[5]+=f; state[6]+=g; state[7]+=h;
}

uint bswap(uint x){ return (x>>24)|((x>>8)&0xff00)|((x<<8)&0xff0000)|(x<<24); }

__kernel void scan_sha256d(
  __global const uchar *prefix76,
  const uint nonce_base,
  const uint batch,
  __global const uchar *target_be,
  __global uint *out_nonces,
  __global uint *out_count,
  const uint max_out
){
  uint gid = get_global_id(0);
  if(gid >= batch) return;
  uint nonce = nonce_base + gid;

  uint st[8]={0x6a09e667U,0xbb67ae85U,0x3c6ef372U,0xa54ff53aU,0x510e527fU,0x9b05688cU,0x1f83d9abU,0x5be0cd19U};
  uint blk[16];
  // first 64 bytes of header as BE words
  for(int i=0;i<16;i++){
    int j=i*4;
    blk[i]=((uint)prefix76[j]<<24)|((uint)prefix76[j+1]<<16)|((uint)prefix76[j+2]<<8)|((uint)prefix76[j+3]);
  }
  sha256_transform(st, blk);

  // second block: last 12 bytes + nonce LE + padding, bitlen 640
  uchar tail[64];
  for(int i=0;i<64;i++) tail[i]=0;
  for(int i=0;i<12;i++) tail[i]=prefix76[64+i];
  tail[12]=(uchar)(nonce & 0xff);
  tail[13]=(uchar)((nonce>>8)&0xff);
  tail[14]=(uchar)((nonce>>16)&0xff);
  tail[15]=(uchar)((nonce>>24)&0xff);
  tail[16]=0x80;
  tail[62]=0x02; tail[63]=0x80;
  for(int i=0;i<16;i++){
    int j=i*4;
    blk[i]=((uint)tail[j]<<24)|((uint)tail[j+1]<<16)|((uint)tail[j+2]<<8)|((uint)tail[j+3]);
  }
  sha256_transform(st, blk);

  uchar dig[32];
  for(int i=0;i<8;i++){
    uint v=st[i];
    dig[i*4]=(uchar)((v>>24)&0xff);
    dig[i*4+1]=(uchar)((v>>16)&0xff);
    dig[i*4+2]=(uchar)((v>>8)&0xff);
    dig[i*4+3]=(uchar)(v&0xff);
  }

  uint st2[8]={0x6a09e667U,0xbb67ae85U,0x3c6ef372U,0xa54ff53aU,0x510e527fU,0x9b05688cU,0x1f83d9abU,0x5be0cd19U};
  for(int i=0;i<64;i++) tail[i]=0;
  for(int i=0;i<32;i++) tail[i]=dig[i];
  tail[32]=0x80;
  tail[62]=0x01; // 256 bits
  for(int i=0;i<16;i++){
    int j=i*4;
    blk[i]=((uint)tail[j]<<24)|((uint)tail[j+1]<<16)|((uint)tail[j+2]<<8)|((uint)tail[j+3]);
  }
  sha256_transform(st2, blk);

  uchar out[32];
  for(int i=0;i<8;i++){
    uint v=st2[i];
    out[i*4]=(uchar)((v>>24)&0xff);
    out[i*4+1]=(uchar)((v>>16)&0xff);
    out[i*4+2]=(uchar)((v>>8)&0xff);
    out[i*4+3]=(uchar)(v&0xff);
  }

  // little(digest) <= big(target)
  int ok = 1;
  for(int i=0;i<32;i++){
    uchar da = out[31-i];
    uchar tb = target_be[i];
    if(da < tb){ ok=1; break; }
    if(da > tb){ ok=0; break; }
  }
  if(ok){
    uint slot = atomic_inc(out_count);
    if(slot < max_out) out_nonces[slot]=nonce;
  }
}
"""

_GPUS: list["GpuHasher"] = []
_INIT = False


class GpuHasher:
    def __init__(self, device_index: int, device, context, queue, kernel):
        self.device_index = device_index
        self.device_name = device.name.strip()
        self._ctx = context
        self._queue = queue
        self._kernel = kernel
        self.local_size = 256
        self.nper = 1
        self.batch_size = 1024 * 256
        self.tuned_rate = 1.0e7  # placeholder until bench
        self._intensity = 4
        self._bench()

    def _bench(self) -> None:
        prefix = np.zeros(76, dtype=np.uint8)
        target = np.full(32, 0xFF, dtype=np.uint8)  # easy target — count throughput only
        # Use impossible target for pure hash rate (no atomics flood)
        target[:] = 0
        target[0] = 0x00
        t0 = time.perf_counter()
        hashed = 0
        for _ in range(3):
            n, _found, h = self.scan(prefix, 0, self.batch_size, target)
            hashed += h
        dt = max(time.perf_counter() - t0, 1e-6)
        self.tuned_rate = hashed / dt

    def set_intensity(self, level: int) -> str:
        level = max(1, min(8, int(level)))
        self._intensity = level
        self.batch_size = (1024 * 64) << (level - 1)
        self._bench()
        mh = self.tuned_rate / 1e6
        return f"Aura OpenCL GPU{self.device_index} intensity={level} · {mh:.1f} MH/s"

    def scan(self, prefix_arr, nonce, batch, target_arr) -> Tuple[int, list, int]:
        if cl is None:
            raise RuntimeError(f"pyopencl missing: {_IMPORT_ERR}")
        prefix = np.ascontiguousarray(prefix_arr, dtype=np.uint8).ravel()[:76]
        target = np.ascontiguousarray(target_arr, dtype=np.uint8).ravel()[:32]
        batch = int(batch)
        max_out = 32
        mf = cl.mem_flags
        pref_buf = cl.Buffer(self._ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=prefix)
        targ_buf = cl.Buffer(self._ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=target)
        out_buf = cl.Buffer(self._ctx, mf.WRITE_ONLY, size=4 * max_out)
        cnt_buf = cl.Buffer(self._ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=np.zeros(1, dtype=np.uint32))
        self._kernel.set_args(pref_buf, np.uint32(nonce), np.uint32(batch), targ_buf, out_buf, cnt_buf, np.uint32(max_out))
        gsize = ((batch + self.local_size - 1) // self.local_size) * self.local_size
        cl.enqueue_nd_range_kernel(self._queue, self._kernel, (gsize,), (self.local_size,))
        cnt = np.zeros(1, dtype=np.uint32)
        cl.enqueue_copy(self._queue, cnt, cnt_buf)
        found_n = int(min(int(cnt[0]), max_out))
        found = []
        if found_n:
            arr = np.zeros(max_out, dtype=np.uint32)
            cl.enqueue_copy(self._queue, arr, out_buf)
            found = [int(x) for x in arr[:found_n]]
        self._queue.finish()
        return found_n, found, batch


def _ensure() -> None:
    global _INIT, _GPUS
    if _INIT:
        return
    _INIT = True
    if cl is None:
        raise RuntimeError(f"Aura Motor: pyopencl nije dostupan ({_IMPORT_ERR})")
    platforms = cl.get_platforms()
    devices = []
    for p in platforms:
        try:
            devices.extend(p.get_devices(device_type=cl.device_type.GPU))
        except Exception:
            pass
    if not devices:
        for p in platforms:
            try:
                devices.extend(p.get_devices(device_type=cl.device_type.ALL))
            except Exception:
                pass
    if not devices:
        raise RuntimeError("Aura Motor: nema OpenCL GPU uređaja")
    _GPUS = []
    for i, dev in enumerate(devices):
        ctx = cl.Context([dev])
        queue = cl.CommandQueue(ctx)
        prg = cl.Program(ctx, _KERNEL).build()
        _GPUS.append(GpuHasher(i, dev, ctx, queue, prg.scan_sha256d))


def get_gpu(index: int = 0) -> GpuHasher:
    _ensure()
    if not _GPUS:
        raise RuntimeError("Aura Motor: nema GPU")
    return _GPUS[int(index) % len(_GPUS)]


def list_gpu_names() -> List[str]:
    try:
        _ensure()
    except Exception:
        return []
    return [g.device_name for g in _GPUS]


def max_all_gpus() -> List[str]:
    _ensure()
    return [g.set_intensity(8) for g in _GPUS]


def bump_all_gpus(direction: int = 1) -> List[str]:
    _ensure()
    notes = []
    for g in _GPUS:
        g.set_intensity(g._intensity + (1 if int(direction) > 0 else -1))
        notes.append(g.set_intensity(g._intensity))
    return notes
