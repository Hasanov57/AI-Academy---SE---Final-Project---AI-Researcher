"""Compare sequential and concurrent source fetching with caches bypassed."""

from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from researcher.bootstrap import build_runtime
from researcher.config import Settings
from researcher.models import DEFAULT_SOURCES


async def measure(offline: bool, runs: int) -> None:
    """Print raw timings and a median speedup for identical workloads."""
    settings = Settings(
        storage_backend="memory" if offline else "postgres",
        arxiv_min_interval_seconds=0 if offline else 1,
    )
    runtime = await build_runtime(settings, offline=offline)
    question = "How do transformer-based language models handle long context windows?"
    sequential: list[float] = []
    concurrent: list[float] = []
    try:
        for _ in range(runs):
            started = time.perf_counter()
            await runtime.orchestrator.fetch_all(
                question, DEFAULT_SOURCES, no_cache=True, concurrent=False
            )
            sequential.append(time.perf_counter() - started)

            started = time.perf_counter()
            await runtime.orchestrator.fetch_all(
                question, DEFAULT_SOURCES, no_cache=True, concurrent=True
            )
            concurrent.append(time.perf_counter() - started)
    finally:
        await runtime.close()

    sequential_median = statistics.median(sequential)
    concurrent_median = statistics.median(concurrent)
    print("run  sequential_s  concurrent_s")
    for index, (seq, con) in enumerate(zip(sequential, concurrent, strict=True), start=1):
        print(f"{index:>3}  {seq:>12.3f}  {con:>12.3f}")
    print(f"median sequential: {sequential_median:.3f} s")
    print(f"median concurrent: {concurrent_median:.3f} s")
    print(f"speedup: {sequential_median / concurrent_median:.2f}x")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be at least 1")
    asyncio.run(measure(args.offline, args.runs))


if __name__ == "__main__":
    main()
