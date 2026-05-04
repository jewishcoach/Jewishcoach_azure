"""Tests for support inbox → User matching (Gmail variants, normalization)."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import app.models  # noqa: F401
from app.database import Base, engine
from app.models import User
from app.services.support_mail_repo import (
    append_support_email_log,
    fetch_support_email_thread_for_llm,
    match_user_by_support_email,
    normalize_customer_email,
    _candidate_lookup_emails,
)
from sqlalchemy.orm import sessionmaker


class TestNormalizeCustomerEmail:
    def test_strips_zero_width_and_lowercases(self):
        raw = "Foo\u200b.Bar@Example.COM "
        assert normalize_customer_email(raw) == "foo.bar@example.com"


class TestCandidateLookupEmails:
    def test_gmail_plus_aliases(self):
        c = _candidate_lookup_emails("ishi+news@gmail.com")
        assert "ishi@gmail.com" in c
        assert "ishi+news@gmail.com" in c

    def test_gmail_dots_and_domains(self):
        c = _candidate_lookup_emails("i.sh.ai@gmail.com")
        assert "ishai@gmail.com" in c
        assert "i.sh.ai@googlemail.com" in c


class TestMatchUserBySupportEmail:
    def setup_method(self):
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)
        self.db = self.Session()

    def teardown_method(self):
        self.db.close()
        Base.metadata.drop_all(bind=engine)

    def test_exact_match(self):
        u = User(clerk_id="c1", email="hello@test.com", created_at=datetime.now(timezone.utc))
        self.db.add(u)
        self.db.commit()

        found = match_user_by_support_email(self.db, "Hello@Test.COM")
        assert found is not None
        assert found.id == u.id

    def test_gmail_plus_matches_registered_without_plus(self):
        u = User(clerk_id="c2", email="me@gmail.com", created_at=datetime.now(timezone.utc))
        self.db.add(u)
        self.db.commit()

        found = match_user_by_support_email(self.db, "me+lists@gmail.com")
        assert found is not None
        assert found.clerk_id == "c2"

    def test_clerk_fallback_upgrades_placeholder(self):
        u = User(
            clerk_id="user_real_clerk",
            email="user_real_clerk@clerk.temp",
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(u)
        self.db.commit()

        with patch(
            "app.services.support_mail_repo._clerk_user_ids_for_email",
            return_value=["user_real_clerk"],
        ):
            found = match_user_by_support_email(self.db, "real@example.com")

        assert found is not None
        assert found.clerk_id == "user_real_clerk"
        self.db.refresh(found)
        assert found.email == "real@example.com"


class TestFetchSupportEmailThreadForLlm:
    def setup_method(self):
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)
        self.db = self.Session()

    def teardown_method(self):
        self.db.close()
        Base.metadata.drop_all(bind=engine)

    def test_chronological_and_exclude_current(self):
        cust = "thread@test.com"
        append_support_email_log(
            self.db,
            customer_email=cust,
            direction="inbound",
            channel="x",
            subject="s1",
            body="first",
        )
        append_support_email_log(
            self.db,
            customer_email=cust,
            direction="outbound",
            channel="y",
            subject="s2",
            body="second",
        )
        r3 = append_support_email_log(
            self.db,
            customer_email=cust,
            direction="inbound",
            channel="z",
            subject="s3",
            body="third",
        )

        thread = fetch_support_email_thread_for_llm(self.db, cust, exclude_log_id=r3.id)
        assert len(thread) == 2
        assert thread[0]["body"] == "first"
        assert thread[1]["body"] == "second"

        full = fetch_support_email_thread_for_llm(self.db, cust)
        assert len(full) == 3
        assert full[-1]["body"] == "third"
