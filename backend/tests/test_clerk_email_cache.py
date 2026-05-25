"""Tests for Clerk email lookup negative cache (403 backoff)."""

from __future__ import annotations

import json
import time
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from app.dependencies import (
    _fetch_clerk_primary_email,
    clear_clerk_email_caches,
)


@pytest.fixture(autouse=True)
def _reset_clerk_caches():
    clear_clerk_email_caches()
    yield
    clear_clerk_email_caches()


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        url="https://api.clerk.com/v1/users/user_abc",
        code=code,
        msg="Forbidden",
        hdrs=None,
        fp=None,
    )


def test_clerk_403_is_cached_and_skips_repeat_calls():
    clerk_id = "user_forbidden_403"
    with patch.dict("os.environ", {"CLERK_SECRET_KEY": "sk_test_fake"}):
        with patch("urllib.request.urlopen") as mock_open:
            mock_open.side_effect = _http_error(403)
            assert _fetch_clerk_primary_email(clerk_id) is None
            assert _fetch_clerk_primary_email(clerk_id) is None
            assert mock_open.call_count == 1


def test_clerk_success_caches_email():
    clerk_id = "user_ok_email"
    body = {
        "primary_email_address_id": "idn_1",
        "email_addresses": [{"id": "idn_1", "email_address": "real@example.com"}],
    }
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(body).encode()
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch.dict("os.environ", {"CLERK_SECRET_KEY": "sk_test_fake"}):
        with patch("urllib.request.urlopen", return_value=mock_resp):
            assert _fetch_clerk_primary_email(clerk_id) == "real@example.com"
            assert _fetch_clerk_primary_email(clerk_id) == "real@example.com"


def test_clerk_negative_cache_expires(monkeypatch):
    clerk_id = "user_expiry"
    now = {"t": 1000.0}
    monkeypatch.setattr("app.dependencies.time.monotonic", lambda: now["t"])

    with patch.dict("os.environ", {"CLERK_SECRET_KEY": "sk_test_fake", "CLERK_NEGATIVE_CACHE_SEC": "60"}):
        with patch("urllib.request.urlopen") as mock_open:
            mock_open.side_effect = _http_error(500)
            assert _fetch_clerk_primary_email(clerk_id) is None
            now["t"] = 1061.0
            mock_open.side_effect = _http_error(500)
            assert _fetch_clerk_primary_email(clerk_id) is None
            assert mock_open.call_count == 2
