"""Load test for the local message model: N simultaneous kids' checks (+ optional Guard traffic) on this machine.

    uv run --no-sync python tools/loadtest_semantic.py                 # 200 kids' checks, one worker per core
    uv run --no-sync python tools/loadtest_semantic.py --workers 2 --guard 400   # ~2 vCPU VPS + busy servers

Uses the real model (data/models, downloaded on first run) and the loaded rule set's head. Reports latency of
each kid's check from submit to result (p50/p95/max), busy notes, Guard messages shed, and process memory.
"""

from __future__ import annotations

import argparse
import asyncio
import ctypes
import os
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from guildward.intel import semantic

TEXTS = [
    "how old r u", "gg wp that was close", "add me on snap its easier", "my car is outside ur school",
    "only u and me can see this chat", "send pics of ur build", "where are u from?", "free nitro claim here",
    "dont tell ur parents we talk ok", "vi ses vid spawn om fem", "hur gammal e du", "skicka en bild på dig",
    "anyone up for duos tonight", "you're so mature for your age honestly", "i can pick you up after school",
    "lol my brother just rage quit", "if you dont answer i'll post the screenshots", "can u help with math hw",
    "i'll buy you the battle pass if you call me", "verify your account or it gets deleted in 24h",
    "what grade are you in btw? you seem older", "join vc we're doing the raid", "jag swishar dig 200 kr om du "
    "ringer mig", "this stays between us, promise?", "that boss fight took forever, finally beat it",
]


def rss_mb() -> float:
    """Resident memory of this process, in MB."""
    if sys.platform == "win32":
        class PMC(ctypes.Structure):
            _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong)] + [
                (n, ctypes.c_size_t) for n in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                                               "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage",
                                               "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
        c = PMC()
        c.cb = ctypes.sizeof(c)
        k32, psapi = ctypes.WinDLL("kernel32"), ctypes.WinDLL("psapi")
        k32.GetCurrentProcess.restype = ctypes.c_void_p
        psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(PMC), ctypes.c_ulong]
        psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(c), c.cb)
        return c.WorkingSetSize / 1e6
    with open("/proc/self/status") as f:
        return next(int(x.split()[1]) for x in f if x.startswith("VmRSS")) / 1e3


async def run(n: int, guard: int, workers: int) -> None:
    before = rss_mb()
    svc = semantic.install(semantic.Service(workers=workers))
    svc.start()
    while not svc.ready:
        if svc.stats.state == "failed":
            raise SystemExit(f"model failed to load: {svc.stats.detail}")
        await asyncio.sleep(0.05)
    loaded = rss_mb()
    await semantic.kid_check(["warm"])

    lat: list[float] = []
    busy = 0

    async def kid(i: int) -> None:
        nonlocal busy
        t0 = time.perf_counter()

        async def note(_place: int) -> None:
            nonlocal busy
            busy += 1

        res = await semantic.kid_check([TEXTS[i % len(TEXTS)]], on_wait=note)
        assert res.status == "ok", res.status
        lat.append((time.perf_counter() - t0) * 1000)

    t0 = time.perf_counter()
    guard_task = asyncio.gather(*(semantic.guard_check([TEXTS[i % len(TEXTS)]]) for i in range(guard)))
    await asyncio.gather(*(kid(i) for i in range(n)))
    kids_done = time.perf_counter() - t0
    await guard_task
    total = time.perf_counter() - t0
    peak = rss_mb()
    svc.stop()
    q = statistics.quantiles(lat, n=20)
    print(f"cores {os.cpu_count()}, workers {workers}; {n} simultaneous kids' checks + {guard} Guard messages")
    print(f"kids' checks: p50 {statistics.median(lat):.0f} ms, p95 {q[18]:.0f} ms, max {max(lat):.0f} ms; "
          f"all done in {kids_done:.2f} s; busy notes {busy}")
    print(f"guard: {guard - svc.stats.shed} classified, {svc.stats.shed} shed; everything done in {total:.2f} s")
    print(f"memory: {before:.0f} MB before, {loaded:.0f} MB with model loaded, {peak:.0f} MB after the burst "
          f"(model adds ~{peak - before:.0f} MB)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=200)
    ap.add_argument("--guard", type=int, default=0, help="Guard background messages fired at the same time")
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    a = ap.parse_args()
    asyncio.run(run(a.n, a.guard, a.workers))


if __name__ == "__main__":
    main()
