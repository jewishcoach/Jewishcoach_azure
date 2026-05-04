"""Tests for inbound support identity resolution (ACS MAIL FROM vs Reply-To)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.support_mail_repo import normalize_customer_email  # noqa: E402
from app.services.support_inbound_pipeline import (  # noqa: E402
    extract_reply_to_from_dashboard_body,
    extract_reply_to_from_headers,
    resolve_inbound_customer_email,
)


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
