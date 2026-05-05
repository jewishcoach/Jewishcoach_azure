import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { useTranslation } from 'react-i18next';
import { Check, Loader2, CreditCard } from 'lucide-react';
import { getApiBase } from '../config';
import { formatCouponRedeemError } from '../lib/couponRedeemError';
import { PayMeCheckoutModal } from './PayMeCheckoutModal';

interface Plan {
  id: string;
  name_he: string;
  name_en: string;
  price: number;
  currency: string;
  messages_per_month: number;
  speech_minutes_per_month: number;
  features: {
    coaching_phases?: string | string[];
    journal_access?: boolean;
    priority_support?: boolean;
    advanced_tools?: boolean;
  };
}

interface Usage {
  messages_used: number;
  messages_limit: number;
  speech_minutes_used: number;
  speech_minutes_limit: number;
  plan: string;
  period_start?: string;
  period_end?: string;
}

interface BillingOverview {
  current_plan: string;
  usage: Usage;
  available_plans: Plan[];
  has_active_coupon: boolean;
  coupon_code?: string;
  payme_checkout?: {
    merchant_public_key: string;
    test_mode: boolean;
    checkout_js_url?: string;
  } | null;
}

const API_BASE = getApiBase();

export const BillingPage = () => {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const { t, i18n } = useTranslation();
  const [overview, setOverview] = useState<BillingOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [couponCode, setCouponCode] = useState('');
  const [couponMessage, setCouponMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [couponLoading, setCouponLoading] = useState(false);
  const [checkoutPlan, setCheckoutPlan] = useState<Plan | null>(null);
  const [payMeSession, setPayMeSession] = useState(0);

  const loadBillingData = useCallback(async () => {
    try {
      const token = await getToken();
      if (!token) return;
      const response = await fetch(`${API_BASE}/billing/overview`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await response.json();
      if (response.ok && data?.usage && Array.isArray(data?.available_plans)) {
        setOverview(data);
      } else {
        setOverview(null);
      }
    } catch (err) {
      console.error('Error loading billing data:', err);
      setOverview(null);
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) {
      setLoading(false);
      return;
    }
    loadBillingData();
  }, [loadBillingData, isLoaded, isSignedIn]);

  const handleRedeemCoupon = async () => {
    if (!couponCode.trim()) return;
    setCouponLoading(true);
    setCouponMessage(null);
    try {
      const token = await getToken();
      const response = await fetch(`${API_BASE}/billing/redeem-coupon`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ code: couponCode.trim() }),
      });
      const data = await response.json();
      if (response.ok) {
        setCouponMessage({ type: 'success', text: data.message || t('billing.couponSuccess') });
        setCouponCode('');
        setTimeout(() => loadBillingData(), 800);
      } else {
        setCouponMessage({ type: 'error', text: formatCouponRedeemError(data.detail, t) });
      }
    } catch {
      setCouponMessage({ type: 'error', text: t('billing.couponServerError') });
    } finally {
      setCouponLoading(false);
    }
  };

  const getFeatureText = (plan: Plan) => {
    const phases = plan.features?.coaching_phases;
    const isAll = phases === 'all' || (Array.isArray(phases) && phases.length > 5);
    return isAll ? t('billing.allStages') : t('billing.basicStages');
  };

  if (loading) {
    return (
      <div className="flex-1 w-full bg-[#0F172A] flex items-center justify-center min-h-0" dir={i18n.dir()}>
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-10 h-10 text-[#94a3b8] animate-spin" />
          <p className="text-[#94a3b8] text-sm font-medium" style={{ fontFamily: 'Heebo, Inter, sans-serif' }}>
            {t('chat.loading')}
          </p>
        </div>
      </div>
    );
  }

  if (!overview) {
    return (
      <div className="flex-1 w-full bg-[#0F172A] flex items-center justify-center min-h-0 p-8" dir={i18n.dir()}>
        <div className="bg-white/[0.03] rounded-lg p-8 border border-white/[0.06] max-w-md text-center">
          <p className="text-[#94a3b8] font-medium mb-4">
            {t('error.loadData')}
          </p>
          <button
            onClick={loadBillingData}
            className="px-5 py-2.5 rounded-lg bg-white/10 text-[#F5F5F0] text-sm font-medium hover:bg-white/15 transition-colors"
          >
            {t('error.tryAgain')}
          </button>
        </div>
      </div>
    );
  }

  const usage = overview.usage;
  const messagesPercent = usage.messages_limit === -1 ? 0 : Math.min((usage.messages_used / usage.messages_limit) * 100, 100);

  return (
    <div className="flex-1 w-full bg-[#0F172A] overflow-y-auto custom-scrollbar" dir={i18n.dir()}>
      <div className="max-w-4xl mx-auto p-6 md:p-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-semibold text-[#F5F5F0] mb-1" style={{ fontFamily: 'Heebo, sans-serif' }}>
            {t('billing.title')}
          </h1>
          <p className="text-[#94a3b8] text-sm">{t('billing.subtitle')}</p>
        </div>

        {/* Active Coupon */}
        {overview.has_active_coupon && (
          <div className="mb-6 py-3 px-4 rounded-lg bg-white/[0.03] border border-white/[0.06]">
            <span className="text-[#F5F5F0] text-sm">
              {t('billing.activeCoupon')} <span className="font-medium">{overview.coupon_code}</span>
            </span>
          </div>
        )}

        {/* Usage - Messages only */}
        <div className="mb-8">
          <div className="bg-white/[0.03] rounded-lg p-5 border border-white/[0.06]">
            <div className="flex items-center justify-between mb-3">
              <span className="text-[#94a3b8] text-sm font-medium">{t('billing.messagesUsed')}</span>
              <span className="text-[#F5F5F0] text-sm tabular-nums" dir="ltr" translate="no">
                {usage.messages_used} / {usage.messages_limit === -1 ? '∞' : usage.messages_limit}
              </span>
            </div>
            <div className="w-full h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500 bg-gradient-to-r from-emerald-700 via-teal-500 to-emerald-400"
                style={{ width: `${usage.messages_limit === -1 ? 0 : messagesPercent}%` }}
              />
            </div>
            {usage.messages_limit !== -1 && (
              <p className="text-[#64748b] text-xs mt-2">
                {t('billing.remaining', { count: usage.messages_limit - usage.messages_used })}
              </p>
            )}
          </div>
        </div>

        {/* Coupon Redemption */}
        {!overview.has_active_coupon && (
          <div className="mb-8">
            <div className="bg-white/[0.03] rounded-lg p-5 border border-white/[0.06]">
              <h3 className="text-sm font-medium text-[#F5F5F0] mb-3">{t('billing.couponTitle')}</h3>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={couponCode}
                  onChange={(e) => setCouponCode(e.target.value.toUpperCase())}
                  placeholder={t('billing.couponPlaceholder')}
                  className="flex-1 px-3 py-2 rounded-lg border border-white/10 bg-white/[0.03] text-[#F5F5F0] text-sm placeholder-[#64748b] focus:outline-none focus:ring-1 focus:ring-white/20"
                  dir="ltr"
                  disabled={couponLoading}
                />
                <button
                  onClick={handleRedeemCoupon}
                  disabled={couponLoading || !couponCode.trim()}
                  className="px-4 py-2 rounded-lg bg-white/10 text-[#F5F5F0] text-sm font-medium hover:bg-white/15 disabled:opacity-50 transition-colors"
                >
                  {couponLoading ? t('billing.couponActivating') : t('billing.couponActivate')}
                </button>
              </div>
              {couponMessage && (
                <div className={`mt-3 p-3 rounded-lg text-sm ${couponMessage.type === 'success' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}`}>
                  {couponMessage.text}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Plans */}
        <div className="mb-8">
          <h2 className="text-lg font-medium text-[#F5F5F0] mb-6">{t('billing.plansTitle')}</h2>
          <div className="grid md:grid-cols-2 gap-4">
            {overview.available_plans.map((plan) => {
              const isCurrent = plan.id === overview.current_plan;
              const isPaidUpgrade = !isCurrent && plan.price > 0;
              const premiumHighlight = isPaidUpgrade && plan.id === 'premium';
              return (
                <div
                  key={plan.id}
                  className={`rounded-xl p-5 border transition-shadow ${
                    isCurrent
                      ? 'bg-white/[0.06] border-[#64748b]/50'
                      : premiumHighlight
                        ? 'border-[#FCF6BA]/35 bg-gradient-to-br from-[#1e293b]/95 via-[#0f172a] to-[#0f172a] shadow-[0_12px_40px_-12px_rgba(179,135,40,0.35)]'
                        : 'bg-white/[0.02] border-white/[0.06]'
                  }`}
                >
                  {isCurrent && (
                    <span className="text-[#64748b] text-xs font-medium">
                      {t('billing.currentBadge')}
                    </span>
                  )}
                  {premiumHighlight && (
                    <span className="inline-block mt-1 text-[11px] font-semibold uppercase tracking-wide text-[#FCF6BA]/90">
                      {t('billing.recommendedPlan')}
                    </span>
                  )}
                  <h3 className="text-lg font-medium text-[#F5F5F0] mt-1">{i18n.language === 'he' ? plan.name_he : plan.name_en}</h3>
                  <div className="mt-2 mb-4">
                    <span className="text-2xl font-semibold text-[#F5F5F0]">
                      {plan.price === 0 ? t('billing.free') : `₪${plan.price}`}
                    </span>
                    {plan.price > 0 && (
                      <span className="text-[#94a3b8] text-sm mr-1">{t('billing.oneTime')}</span>
                    )}
                  </div>
                  <ul className="space-y-2 mb-5">
                    <li className="flex items-center gap-2 text-[#94a3b8] text-sm">
                      <Check
                        className={`w-4 h-4 flex-shrink-0 ${premiumHighlight ? 'text-[#B38728]' : 'text-[#64748b]'}`}
                      />
                      {plan.messages_per_month === -1
                        ? `${t('billing.unlimited')} · ${t('billing.messagesPerMonthShort')}`
                        : `${plan.messages_per_month} ${t('billing.messagesPerMonthShort')}`}
                    </li>
                    <li className="flex items-center gap-2 text-[#94a3b8] text-sm">
                      <Check
                        className={`w-4 h-4 flex-shrink-0 ${premiumHighlight ? 'text-[#B38728]' : 'text-[#64748b]'}`}
                      />
                      {getFeatureText(plan)}
                    </li>
                    {plan.features?.journal_access && (
                      <li className="flex items-center gap-2 text-[#94a3b8] text-sm">
                        <Check
                          className={`w-4 h-4 flex-shrink-0 ${premiumHighlight ? 'text-[#B38728]' : 'text-[#64748b]'}`}
                        />
                        {t('billing.personalJournal')}
                      </li>
                    )}
                    {(plan.features?.priority_support || plan.features?.advanced_tools) && (
                      <li className="flex items-center gap-2 text-[#94a3b8] text-sm">
                        <Check
                          className={`w-4 h-4 flex-shrink-0 ${premiumHighlight ? 'text-[#B38728]' : 'text-[#64748b]'}`}
                        />
                        {t('billing.deepInsights')}
                      </li>
                    )}
                  </ul>
                  {isPaidUpgrade && (
                    <button
                      type="button"
                      onClick={() => {
                        setCheckoutPlan(plan);
                        setPayMeSession((s) => s + 1);
                      }}
                      className="group w-full py-3 rounded-xl text-sm font-semibold text-[#0f172a] shadow-lg shadow-amber-950/25 transition-all hover:brightness-105 hover:shadow-xl hover:shadow-amber-950/30 active:scale-[0.99] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#FCF6BA]/70 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0f172a]"
                      style={{
                        background: 'linear-gradient(135deg, #BF953F 0%, #FCF6BA 42%, #B38728 100%)',
                      }}
                    >
                      {t('billing.upgradeNow')}
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Payment / Credit Card Section */}
        <div className="bg-white/[0.03] rounded-lg p-6 border border-white/[0.06]">
          <div className="flex items-start gap-3">
            <CreditCard className="w-5 h-5 text-[#64748b] flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="text-sm font-medium text-[#F5F5F0] mb-1">
                {t('billing.paymentDetails')}
              </h3>
              <p className="text-[#94a3b8] text-sm">
                {t('billing.paymentPayMeHint')}
              </p>
            </div>
          </div>
        </div>

        {checkoutPlan && (
          <PayMeCheckoutModal
            key={payMeSession}
            open
            plan={checkoutPlan}
            payMeCheckoutFromOverview={overview?.payme_checkout ?? null}
            getToken={getToken}
            onClose={() => setCheckoutPlan(null)}
            onCompleted={() => void loadBillingData()}
          />
        )}
      </div>
    </div>
  );
};
