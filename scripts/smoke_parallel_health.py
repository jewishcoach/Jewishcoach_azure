#!/usr/bin/env python3
"""
Smoke load: many parallel HTTP GETs to /health (stdlib only).

Usage:
  BASE_URL=https://your-api.example.com python3 scripts/smoke_parallel_health.py --workers 30 --per-worker 5

Does NOT authenticate — good for gateway + app + DB ping without burning LLM quota.
For chat endpoints you need k6/Locust + tokens + separate conversation ids per VU.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import os
import sys
import time
import urllib.error
import urllib.request


def fetch(url: str, timeout: float) -> tuple[int, float, str | None]:
    t0 = time.perf_counter()
    err: str | None = None
    status = -1
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.getcode()
    except urllib.error.HTTPError as e:
        status = e.code
        err = str(e)
    except Exception as e:
        err = type(e).__name__ + ": " + str(e)
    elapsed = time.perf_counter() - t0
    return status, elapsed, err


def main() -> int:
    p = argparse.ArgumentParser(description="Parallel /health smoke requests")
    p.add_argument("--workers", type=int, default=30, help="Concurrent workers (default 30)")
    p.add_argument("--per-worker", type=int, default=1, help="Sequential requests per worker")
    p.add_argument("--timeout", type=float, default=45.0, help="Per-request timeout seconds")
    args = p.parse_args()

    base = os.environ.get("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    url = f"{base}/health"

    tasks: list[tuple[str, float]] = [(url, args.timeout)] * (args.workers * args.per_worker)

    print(f"URL={url} workers={args.workers} per_worker={args.per_worker} total_requests={len(tasks)}")

    t0 = time.perf_counter()
    failures = 0
    statuses: dict[int, int] = {}

    def run_one(item: tuple[str, float]) -> tuple[int, float, str | None]:
        return fetch(item[0], item[1])

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        for status, elapsed, err in ex.map(run_one, tasks):
            statuses[status] = statuses.get(status, 0) + 1
            if err or status != 200:
                failures += 1
                if err:
                    print(f"FAIL status={status} elapsed={elapsed:.3f}s err={err}", file=sys.stderr)

    total_time = time.perf_counter() - t0
    print(f"Done in {total_time:.2f}s status_histogram={statuses} failures={failures}/{len(tasks)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
