import type { TFunction } from 'i18next';

function apiDetailErrorCode(detail: unknown): string | undefined {
  if (!detail || typeof detail !== 'object' || Array.isArray(detail)) return undefined;
  const err = (detail as { error?: unknown }).error;
  return typeof err === 'string' ? err : undefined;
}

/**
 * Map redeem-coupon API errors to safe user-facing copy.
 * Prefer opaque `{ error: string }` from API; never echo unknown raw bodies (enumeration).
 */
export function formatCouponRedeemError(detail: unknown, t: TFunction): string {
  const code = apiDetailErrorCode(detail);
  if (code === 'coupon_empty') {
    return t('billing.couponErrEmpty');
  }
  if (code === 'coupon_already_redeemed') {
    return t('billing.couponErrAlreadyRedeemed');
  }
  if (code === 'coupon_invalid') {
    return t('billing.couponErrInvalid');
  }

  let raw = '';
  if (typeof detail === 'string') {
    raw = detail.trim();
  } else if (Array.isArray(detail) && detail[0] && typeof (detail[0] as { msg?: string }).msg === 'string') {
    raw = String((detail[0] as { msg: string }).msg).trim();
  }

  if (raw === 'Enter a coupon code') {
    return t('billing.couponErrEmpty');
  }
  if (raw === 'You have already redeemed this coupon') {
    return t('billing.couponErrAlreadyRedeemed');
  }

  return t('billing.couponErrInvalid');
}
