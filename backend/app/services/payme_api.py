"""PayMe Payments REST client (generate-sale) — urllib only."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .payme_settings import payme_api_base_url, payme_api_key, payme_seller_payme_id


class PayMeAPIError(Exception):
    def __init__(self, message: str, *, status: int | None = None, body: Any = None):
        super().__init__(message)
        self.status = status
        self.body = body


def payme_generate_sale(
    *,
    buyer_token: str,
    sale_price: int,
    transaction_id: str,
    buyer_email: str | None = None,
    timeout_sec: float = 60.0,
) -> dict[str, Any]:
    """POST {base}/generate-sale — buyer_token comes from PayMe Hosted Fields tokenize()."""
    base = payme_api_base_url().rstrip("/")
    url = f"{base}/generate-sale"
    key = payme_api_key()
    if not key:
        raise PayMeAPIError("PAYME_API_KEY missing")

    seller = payme_seller_payme_id()
    if not seller:
        raise PayMeAPIError("seller_payme_id missing (set PAYME_API_KEY or PAYME_SELLER_PAYME_ID)")

    payload: dict[str, Any] = {
        "seller_payme_id": seller,
        "sale_payment_method": [{"credit-card": {"token": buyer_token.strip()}}],
        "sale_price": int(sale_price),
        "transaction_id": transaction_id,
    }
    if buyer_email and "@" in buyer_email:
        payload["buyer_email"] = buyer_email.strip()

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"raw": raw[:2000]}
        raise PayMeAPIError(f"PayMe HTTP {e.code}", status=e.code, body=parsed) from e
    except urllib.error.URLError as e:
        raise PayMeAPIError(f"PayMe network error: {e}") from e

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise PayMeAPIError("PayMe returned non-JSON", body=raw[:2000]) from e


def payme_response_failed(data: dict[str, Any]) -> bool:
    if not isinstance(data, dict):
        return True
    if data.get("status_error_details"):
        return True
    sc = data.get("status_code")
    if sc is None:
        return False
    try:
        return int(sc) != 0
    except (TypeError, ValueError):
        return True


def payme_sale_reference(data: dict[str, Any]) -> str | None:
    if not isinstance(data, dict):
        return None
    for k in (
        "pay_me_sale_id",
        "sale_pay_me_id",
        "sale_id",
        "sale_pay_me_code",
        "payme_sale_id",
    ):
        v = data.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
        if isinstance(v, (int, float)):
            return str(v)
    nested = data.get("sale")
    if isinstance(nested, dict):
        return payme_sale_reference(nested)
    return None


def deep_find_transaction_id(obj: Any, prefix: str = "jc-") -> str | None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "transaction_id" and isinstance(v, str) and v.startswith(prefix):
                return v
            found = deep_find_transaction_id(v, prefix)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = deep_find_transaction_id(item, prefix)
            if found:
                return found
    return None


def webhook_payload_suggests_success(payload: Any) -> bool:
    """Best-effort until PayMe webhook schema is pinned in docs."""
    if not isinstance(payload, dict):
        return False
    ev = str(payload.get("event") or payload.get("type") or "").lower()
    if ev and any(x in ev for x in ("paid", "complete", "success", "capture", "sale")):
        if "fail" in ev or "reject" in ev or "chargeback" in ev:
            return False
        return True
    sale = payload.get("sale") or payload.get("data", {}).get("sale")
    if isinstance(sale, dict):
        st = str(sale.get("status") or sale.get("state") or "").lower()
        if st in ("paid", "completed", "successful", "success", "authorized", "captured"):
            return True
    blob = json.dumps(payload, ensure_ascii=False).lower()
    if "paid" in blob or "completed" in blob or "successful" in blob:
        if "fail" in blob or "reject" in blob:
            return False
        return True
    return False
