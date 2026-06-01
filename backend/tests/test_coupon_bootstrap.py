"""Default coupon bootstrap and message limits."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.coupon_bootstrap import (
    DEFAULT_COUPONS,
    SHELA001_DESCRIPTION,
    _CouponSpec,
    _ensure_coupon,
    ensure_default_coupons,
)
from app.schemas.billing import effective_messages_per_month


def test_default_coupon_codes():
    codes = {spec.code for spec in DEFAULT_COUPONS}
    assert codes == {"BSD100", "SHELA000", "SHELA001", "NOAM000"}


def test_shela001_has_2000_message_limit():
    shela = next(s for s in DEFAULT_COUPONS if s.code == "SHELA001")
    assert shela.messages_limit == 2000
    assert shela.description == SHELA001_DESCRIPTION


def test_single_use_coupons_limited_to_one_global_redemption():
    for code in ("SHELA000", "SHELA001", "NOAM000"):
        assert next(s for s in DEFAULT_COUPONS if s.code == code).max_uses == 1
    assert next(s for s in DEFAULT_COUPONS if s.code == "BSD100").max_uses is None


def test_effective_messages_respects_coupon_cap_on_premium():
    assert (
        effective_messages_per_month(
            email="a@b.com",
            plan_key="premium",
            coupon_messages_limit=2000,
        )
        == 2000
    )


def test_ensure_coupon_creates_shela001_with_limit():
    db = MagicMock()
    query = MagicMock()
    filter_q = MagicMock()
    filter_q.first.return_value = None
    query.filter.return_value = filter_q
    db.query.return_value = query

    spec = next(s for s in DEFAULT_COUPONS if s.code == "SHELA001")
    _ensure_coupon(db, spec)

    added = db.add.call_args[0][0]
    assert added.code == "SHELA001"
    assert added.messages_limit == 2000


def test_ensure_default_coupons_iterates_all_specs():
    db = MagicMock()
    with patch("app.services.coupon_bootstrap._ensure_coupon") as mock_ensure:
        ensure_default_coupons(db)
    assert mock_ensure.call_count == len(DEFAULT_COUPONS)
    called_codes = {call.args[1].code for call in mock_ensure.call_args_list}
    assert called_codes == {"BSD100", "SHELA000", "SHELA001", "NOAM000"}
