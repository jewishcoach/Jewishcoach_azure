"""Tests for inbound support identity resolution (ACS MAIL FROM vs Reply-To)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import app.models  # noqa: F401
from app.database import Base, engine  # noqa: E402
from app.services.support_mail_repo import (  # noqa: E402
    append_support_email_log,
    normalize_customer_email,
)
from app.services.support_inbound_pipeline import (  # noqa: E402
    extract_dashboard_ticket_body_from_html,
    extract_reply_to_from_dashboard_body,
    extract_reply_to_from_headers,
    find_recent_dashboard_contact_duplicate_row,
    normalize_inbound_dashboard_ticket_body,
    resolve_inbound_customer_email,
    strip_dashboard_contact_plain_envelope,
)
from sqlalchemy.orm import sessionmaker  # noqa: E402


class TestExtractReplyToHeaders:
    def test_simple_reply_to(self):
        h = "Reply-To: Jane <jane@example.com>\n"
        assert extract_reply_to_from_headers(h) == "jane@example.com"

    def test_multiple_addresses_first_wins(self):
        h = "Reply-To: first@example.com, Second <second@example.org>\n"
        assert extract_reply_to_from_headers(h) == "first@example.com"


class TestExtractDashboardReplyTo:
    def test_html_template(self):
        html = '<body><p><strong>Reply-To:</strong> user+tags@gmail.com</p></body>'
        assert extract_reply_to_from_dashboard_body(None, html) == normalize_customer_email(
            "user+tags@gmail.com"
        )

    def test_plain_reply_line(self):
        text = "Subject: hi\nReply-To: u@example.com\n\nHello"
        assert extract_reply_to_from_dashboard_body(text, None) == "u@example.com"


class TestResolveInboundCustomerEmail:
    @pytest.fixture
    def support_mb(self):
        with patch.dict("os.environ", {"SUPPORT_INBOUND_MAILBOX": "support@jewishcoacher.com"}, clear=False):
            yield

    def test_acs_relay_prefers_reply_to_header(self, support_mb):
        em, skip, src = resolve_inbound_customer_email(
            from_field="norelay <donotreply@g.us1.azurecomm.net>",
            headers_raw="Reply-To: Customer <cust@gmail.com>\n",
            text_part="Reply-To: other@gmail.com",
            html_part=None,
        )
        assert skip is None
        assert em == "cust@gmail.com"
        assert src == "reply_to_header"

    def test_acs_relay_falls_back_to_dashboard_body_when_no_headers(self, support_mb):
        html = '<html><p><strong>Reply-To:</strong> user@gmail.com</p>'
        em, skip, src = resolve_inbound_customer_email(
            from_field="donotreply@abc.us1.azurecomm.net",
            headers_raw=None,
            text_part=None,
            html_part=html,
        )
        assert skip is None
        assert em == "user@gmail.com"
        assert src == "dashboard_body_reply_to"

    def test_normal_sender_unchanged(self, support_mb):
        em, skip, src = resolve_inbound_customer_email(
            from_field="Bob <bob@example.net>",
            headers_raw="Reply-To: support@jewishcoacher.com\n",
            text_part=None,
            html_part=None,
        )
        assert skip is None
        assert em == "bob@example.net"
        assert src == "from"

    def test_relay_without_customer_hints_skipped(self, support_mb):
        em, skip, src = resolve_inbound_customer_email(
            from_field="donotreply@x.us1.azurecomm.net",
            headers_raw=None,
            text_part="no reply-to line here",
            html_part=None,
        )
        assert em is None
        assert skip == "relay_sender_no_customer_reply_to"
        assert src == "skipped"

    def test_configured_email_sender_matches_relay(self, support_mb):
        with patch.dict(
            "os.environ",
            {"EMAIL_SENDER": "Reminders <hello@verified.example.com>", "SUPPORT_INBOUND_MAILBOX": "support@jewishcoacher.com"},
            clear=False,
        ):
            em, skip, src = resolve_inbound_customer_email(
                from_field="hello@verified.example.com",
                headers_raw="Reply-To: me@client.org\n",
                text_part=None,
                html_part=None,
            )
        assert skip is None
        assert em == "me@client.org"
        assert src == "reply_to_header"


class TestStripDashboardPlainEnvelope:
    def test_multiline_legacy_plain(self):
        raw = (
            "From user id: 8\n"
            "Clerk id: user_abc\n"
            "Reply-To: x@example.com\n"
            "Subject: what up?\n\n"
            "you didnt wrote back yet\n"
        )
        cleaned, stripped = strip_dashboard_contact_plain_envelope(raw)
        assert stripped
        assert cleaned == "you didnt wrote back yet"

    def test_collapsed_single_line(self):
        raw = "From user id: 8 Clerk id: user_x Reply-To: a@b.com Subject: hi hello there"
        cleaned, stripped = strip_dashboard_contact_plain_envelope(raw)
        assert stripped
        assert cleaned == "hello there"


class TestExtractDashboardTicketHtmlPre:
    def test_pre_body_only(self):
        html = (
            "<body><p><strong>From user id:</strong> 8</p>"
            "<pre style=\"x\">line1\nline2</pre></body>"
        )
        assert extract_dashboard_ticket_body_from_html(html) == "line1\nline2"

    def test_non_dashboard_returns_none(self):
        assert extract_dashboard_ticket_body_from_html("<pre>only</pre>") is None


class TestNormalizeInboundDashboardBody:
    def test_prefers_html_pre_over_plain_noise(self):
        html = '<html><body><p><strong>From user id:</strong> 1</p><pre>User says hi</pre></body></html>'
        plain = "From user id: 1\nClerk id: x\nReply-To: y@z\nSubject: s\n\nignored"
        body, meta = normalize_inbound_dashboard_ticket_body(html, fallback_plain=plain)
        assert body == "User says hi"
        assert meta["dashboard_ticket_parse"] == "html_pre"


class TestDuplicateDashboardEcho:
    def setup_method(self):
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)
        self.db = self.Session()

    def teardown_method(self):
        self.db.close()
        Base.metadata.drop_all(bind=engine)

    def test_finder_returns_matching_row(self):
        append_support_email_log(
            self.db,
            customer_email="cust@example.com",
            direction="inbound",
            channel="user_dashboard",
            subject="[Jewish Coach app] hi",
            body="same text",
        )
        row = find_recent_dashboard_contact_duplicate_row(
            self.db,
            customer_email="cust@example.com",
            subject="[Jewish Coach app] hi",
            body="same text",
        )
        assert row is not None
        assert row.body == "same text"

    def test_finder_none_when_body_differs(self):
        append_support_email_log(
            self.db,
            customer_email="cust@example.com",
            direction="inbound",
            channel="user_dashboard",
            subject="[Jewish Coach app] hi",
            body="first",
        )
        assert (
            find_recent_dashboard_contact_duplicate_row(
                self.db,
                customer_email="cust@example.com",
                subject="[Jewish Coach app] hi",
                body="second",
            )
            is None
        )
