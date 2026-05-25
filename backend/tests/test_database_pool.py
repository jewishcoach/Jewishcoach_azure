"""Postgres pool defaults — conservative for Azure B1ms connection limits."""

from __future__ import annotations

from unittest.mock import patch

from app.database import _postgres_engine_kwargs


def test_postgres_pool_defaults_are_conservative():
    with patch.dict("os.environ", {}, clear=True):
        kwargs = _postgres_engine_kwargs()
    assert kwargs["pool_size"] == 3
    assert kwargs["max_overflow"] == 5
    assert kwargs["pool_pre_ping"] is True
