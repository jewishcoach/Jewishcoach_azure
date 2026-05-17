#!/usr/bin/env python3
"""
Parallel load smoke for Chat V2 (creates one conversation per worker, sends one message).

Modes
-----
1) Clerk JWT — set BEARER_TOKEN or TOKENS_FILE (production/staging).
2) Local demo auth — --demo-localhost requires backend ALLOW_DEMO_MODE=true AND
   ALLOW_DEMO_LOCALHOST=true; sends Origin (LOAD_TEST_DEMO_ORIGIN, default
   http://127.0.0.1:5173) and no Bearer token.

Environment (Clerk mode):
  BASE_URL, BEARER_TOKEN or TOKENS_FILE

Environment (demo-localhost):
  BASE_URL, LOAD_TEST_DEMO_ORIGIN (optional)

Per-worker X-Forwarded-For uses TEST-NET-3 addresses so SlowAPI's per-IP limits are less
likely to trip when many workers share one machine (depends on proxy behavior).

Usage:
  BASE_URL=https://api.example.com BEARER_TOKEN=eyJ... \\
    python3 scripts/load_test_chat_v2_parallel.py --workers 30

  BASE_URL=http://127.0.0.1:8000 \\
    python3 scripts/load_test_chat_v2_parallel.py --demo-localhost --workers 30
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request


def _load_tokens(path: str | None, single: str | None) -> list[str]:
    if path:
        with open(path, encoding="utf-8") as f:
            tokens = [ln.strip() for ln in f if ln.strip()]
        if not tokens:
            raise SystemExit(f"No tokens in {path}")
        return tokens
    if single:
        return [single.strip()]
    raise SystemExit("Set BEARER_TOKEN or TOKENS_FILE (or use --demo-localhost)")


def _request(
    method: str,
    url: str,
    *,
    token: str | None,
    demo_origin: str | None,
    payload: dict | None,
    timeout: float,
    spoof_ip: str | None,
) -> tuple[int, float, object]:
    t0 = time.perf_counter()
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    if demo_origin:
        req.add_header("Origin", demo_origin)
    if payload is not None:
        req.add_header("Content-Type", "application/json")
    if spoof_ip:
        req.add_header("X-Forwarded-For", spoof_ip)
    status = -1
    body_obj: object = None
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.getcode()
            raw = resp.read()
            if raw:
                try:
                    body_obj = json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError:
                    body_obj = raw.decode("utf-8", errors="replace")[:500]
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            body_obj = json.loads(e.read().decode("utf-8"))
        except Exception:
            body_obj = e.reason
    except Exception as e:
        status = -1
        body_obj = f"{type(e).__name__}: {e}"
    elapsed = time.perf_counter() - t0
    return status, elapsed, body_obj


def _worker_run(
    worker_id: int,
    base: str,
    tokens: list[str] | None,
    *,
    demo_origin: str | None,
    timeout: float,
    spoof_ip: bool,
    warmup: bool,
    message: str,
    language: str,
) -> dict:
    token: str | None = None
    if demo_origin:
        token = None
    else:
        assert tokens is not None
        token = tokens[worker_id % len(tokens)]

    fake_ip = f"203.0.113.{(worker_id % 250) + 1}" if spoof_ip else None
    out: dict = {"worker": worker_id, "fake_ip": fake_ip, "steps": []}

    if warmup:
        w_url = f"{base}/api/chat/v2/warmup?language={language}"
        st, elapsed, body = _request(
            "GET",
            w_url,
            token=None,
            demo_origin=None,
            payload=None,
            timeout=min(timeout, 60.0),
            spoof_ip=fake_ip,
        )
        out["steps"].append({"name": "warmup", "status": st, "elapsed": elapsed, "body": body})
        if st != 200:
            return out

    c_url = f"{base}/api/chat/conversations"
    st, elapsed, body = _request(
        "POST",
        c_url,
        token=token,
        demo_origin=demo_origin,
        payload={},
        timeout=min(timeout, 120.0),
        spoof_ip=fake_ip,
    )
    out["steps"].append({"name": "create_conversation", "status": st, "elapsed": elapsed})
    if st != 200 or not isinstance(body, dict) or "id" not in body:
        out["steps"][-1]["body"] = body
        return out
    conv_id = body["id"]

    m_url = f"{base}/api/chat/v2/message"
    st, elapsed, body = _request(
        "POST",
        m_url,
        token=token,
        demo_origin=demo_origin,
        payload={"message": message, "conversation_id": conv_id, "language": language},
        timeout=timeout,
        spoof_ip=fake_ip,
    )
    step_end = {"name": "v2_message", "status": st, "elapsed": elapsed, "conversation_id": conv_id}
    if st != 200:
        step_end["body"] = body
    else:
        step_end["coach_len"] = len((body or {}).get("coach_message") or "") if isinstance(body, dict) else 0
    out["steps"].append(step_end)
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Parallel Chat V2 load smoke")
    p.add_argument("--workers", type=int, default=30)
    p.add_argument("--timeout", type=float, default=180.0, help="Timeout for /message (seconds)")
    p.add_argument("--warmup", action="store_true", help="GET /api/chat/v2/warmup per worker first")
    p.add_argument(
        "--demo-localhost",
        action="store_true",
        help="No JWT; send Origin for ALLOW_DEMO_LOCALHOST + ALLOW_DEMO_MODE on the API",
    )
    p.add_argument(
        "--no-spoof-client-ip",
        action="store_true",
        help="Do not send X-Forwarded-For (expect SlowAPI 429 if many VUs share one egress IP)",
    )
    p.add_argument("--message", default="", help="User message (default random short Hebrew)")
    p.add_argument("--language", default="he")
    args = p.parse_args()

    base = os.environ.get("BASE_URL", "http://127.0.0.1:8000").rstrip("/")

    demo_origin: str | None = None
    tokens: list[str] | None = None
    if args.demo_localhost:
        demo_origin = os.environ.get("LOAD_TEST_DEMO_ORIGIN", "http://127.0.0.1:5173").strip()
        if not demo_origin:
            raise SystemExit("LOAD_TEST_DEMO_ORIGIN must be non-empty when using --demo-localhost")
    else:
        tokens = _load_tokens(os.environ.get("TOKENS_FILE"), os.environ.get("BEARER_TOKEN"))

    msg = (args.message or "").strip() or f"בדיקת עומס מספר {random.randint(1000, 9999)}"

    print(
        f"BASE_URL={base} workers={args.workers} "
        f"auth={'demo-localhost' if demo_origin else f'jwt_tokens={len(tokens or [])}'} "
        f"warmup={args.warmup} spoof_ip={not args.no_spoof_client_ip}",
        flush=True,
    )

    t0 = time.perf_counter()
    failures = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [
            ex.submit(
                _worker_run,
                wid,
                base,
                tokens,
                demo_origin=demo_origin,
                timeout=args.timeout,
                spoof_ip=not args.no_spoof_client_ip,
                warmup=args.warmup,
                message=msg,
                language=args.language,
            )
            for wid in range(args.workers)
        ]
        for fut in concurrent.futures.as_completed(futs):
            r = fut.result()
            last = r["steps"][-1] if r["steps"] else {}
            ok = last.get("status") == 200 and last.get("name") == "v2_message"
            if not ok:
                failures += 1
                print(f"FAIL worker={r['worker']} steps={json.dumps(r['steps'], default=str)[:800]}", file=sys.stderr)
            else:
                print(
                    f"OK worker={r['worker']} conv={last.get('conversation_id')} "
                    f"v2_message_ms={last.get('elapsed', 0)*1000:.0f}",
                    flush=True,
                )

    elapsed = time.perf_counter() - t0
    print(f"Done in {elapsed:.2f}s failures={failures}/{args.workers}", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
