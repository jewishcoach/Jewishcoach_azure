import type { TFunction } from 'i18next';

/**
 * FastAPI returns `detail` as a string (or validation array). Map known redeem-coupon
 * messages to i18n keys for Hebrew/English UX.
 */
export function formatCouponRedeemError(detail: unknown, t: TFunction): string {
  let raw = '';
  if (typeof detail === 'string') {
    raw = detail;
  } else if (Array.isArray(detail) && detail[0] && typeof (detail[0] as { msg?: string }).msg === 'string') {
    raw = (detail[0] as { msg: string }).msg;
  }

  const keyByDetail: Record<string, string> = {
    'Coupon not found or inactive': 'billing.couponErrNotFound',
    'Coupon code not found': 'billing.couponErrNotFound',
    'Coupon is no longer active': 'billing.couponErrInactive',
    'Enter a coupon code': 'billing.couponErrEmpty',
    'Coupon has expired': 'billing.couponErrExpired',
    'Coupon usage limit reached': 'billing.couponErrLimitReached',
    'You have already redeemed this coupon': 'billing.couponErrAlreadyRedeemed',
  };

  const key = keyByDetail[raw];
  if (key) return t(key);
  return raw || t('billing.couponError');
}
