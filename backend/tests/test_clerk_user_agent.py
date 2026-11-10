"""Clerk's API (behind Cloudflare) refuses the default Python-urllib user agent with 403/1010 — every email lookup
failed until Nov 10. The lookup must send its own User-Agent."""
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import app.dependencies as deps


def test_clerk_lookup_sends_a_user_agent(monkeypatch):
    seen = {}

    class Resp(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake_urlopen(req, timeout=0):
        seen["ua"] = req.get_header("User-agent")
        return Resp(json.dumps({"primary_email_address_id": "e1",
                                "email_addresses": [{"id": "e1", "email_address": "real@gmail.com"}]}).encode())

    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_x")
    monkeypatch.setattr(deps.urllib.request, "urlopen", fake_urlopen)
    deps._CLERK_PRIMARY_EMAIL_CACHE.pop("user_ua_test", None)
    deps._CLERK_NEGATIVE_CACHE.pop("user_ua_test", None)
    assert deps.resolve_email_from_db_and_clerk("user_ua_test", "user_ua_test@clerk.temp") == "real@gmail.com"
    assert seen["ua"] and "Python-urllib" not in seen["ua"]
