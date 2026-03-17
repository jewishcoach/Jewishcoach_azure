import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { useTranslation } from 'react-i18next';
import { Check, Loader2, MessageSquare, CreditCard } from 'lucide-react';
import { getApiBase } from '../config';

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
}

const API_BASE = getApiBase();

export const BillingPage = () => {
  const { getToken } = useAuth();
  const { t, i18n } = useTranslation();
  const [overview, setOverview] = useState<BillingOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [couponCode, setCouponCode] = useState('');
  const [couponMessage, setCouponMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [couponLoading, setCouponLoading] = useState(false);
  const [showUpgradeNote, setShowUpgradeNote] = useState(false);

  const loadBillingData = useCallback(async () => {
    try {
      const token = await getToken();
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
    loadBillingData();
  }, [loadBillingData]);

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
        body: JSON.stringify({ code: couponCode.toUpperCase() }),
      });
      const data = await response.json();
      if (response.ok) {
        setCouponMessage({ type: 'success', text: data.message || t('billing.couponSuccess') });
        setCouponCode('');
        setTimeout(() => loadBillingData(), 800);
      } else {
        setCouponMessage({ type: 'error', text: Array.isArray(data.detail) ? data.detail[0]?.msg || data.detail : data.detail || t('billing.couponError') });
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
      <div className="flex-1 w-full bg-[#0F172A] flex items-center justify-center min-h-0" dir="rtl">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-10 h-10 text-[#94a3b8] animate-spin" />
          <p className="text-[#94a3b8] text-sm font-medium" style={{ fontFamily: 'Heebo, Inter, sans-serif' }}>
            {i18n.language === 'he' ? 'טוען...' : 'Loading...'}
          </p>
        </div>
      </div>
    );
  }

  if (!overview) {
    return (
      <div className="flex-1 w-full bg-[#0F172A] flex items-center justify-center min-h-0 p-8" dir="rtl">
        <div className="bg-white/[0.03] rounded-lg p-8 border border-white/[0.06] max-w-md text-center">
          <p className="text-[#94a3b8] font-medium mb-4">
            {i18n.language === 'he' ? 'שגיאה בטעינת נתונים' : 'Error loading data'}
          </p>
          <button
            onClick={loadBillingData}
            className="px-5 py-2.5 rounded-lg bg-white/10 text-[#F5F5F0] text-sm font-medium hover:bg-white/15 transition-colors"
          >
            {i18n.language === 'he' ? 'נסה שוב' : 'Try again'}
          </button>
        </div>
      </div>
    );
  }

  const usage = overview.usage;
  const messagesPercent = usage.messages_limit === -1 ? 0 : Math.min((usage.messages_used / usage.messages_limit) * 100, 100);

  return (
    <div className="flex-1 w-full bg-[#0F172A] overflow-y-auto custom-scrollbar" dir="rtl">
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
              {i18n.language === 'he' ? 'קופון פעיל:' : 'Active coupon:'} <span className="font-medium">{overview.coupon_code}</span>
            </span>
          </div>
        )}

        {/* Usage - Messages only */}
        <div className="mb-8">
          <div className="bg-white/[0.03] rounded-lg p-5 border border-white/[0.06]">
            <div className="flex items-center justify-between mb-3">
              <span className="text-[#94a3b8] text-sm font-medium">{i18n.language === 'he' ? 'שימוש בהודעות' : 'Messages used'}</span>
              <span className="text-[#F5F5F0] text-sm">
                {usage.messages_used} / {usage.messages_limit === -1 ? '∞' : usage.messages_limit}
              </span>
            </div>
            <div className="w-full h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
              <div
                className="h-full bg-[#64748b] rounded-full transition-all duration-500"
                style={{ width: `${usage.messages_limit === -1 ? 0 : messagesPercent}%` }}
              />
            </div>
            {usage.messages_limit !== -1 && (
              <p className="text-[#64748b] text-xs mt-2">
                {i18n.language === 'he' ? `נותרו ${usage.messages_limit - usage.messages_used} הודעות` : `${usage.messages_limit - usage.messages_used} remaining`}
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
          <div className="grid md:grid-cols-3 gap-4">
            {overview.available_plans.map((plan) => {
              const isCurrent = plan.id === overview.current_plan;
              return (
                <div
                  key={plan.id}
                  className={`rounded-lg p-5 border ${
                    isCurrent ? 'bg-white/[0.06] border-[#64748b]/50' : 'bg-white/[0.02] border-white/[0.06]'
                  }`}
                >
                  {isCurrent && (
                    <span className="text-[#64748b] text-xs font-medium">
                      {t('billing.currentBadge')}
                    </span>
                  )}
                  <h3 className="text-lg font-medium text-[#F5F5F0] mt-1">{plan.name_he}</h3>
                  <div className="mt-2 mb-4">
                    <span className="text-2xl font-semibold text-[#F5F5F0]">
                      {plan.price === 0 ? (i18n.language === 'he' ? 'חינם' : 'Free') : `₪${plan.price}`}
                    </span>
                    {plan.price > 0 && <span className="text-[#94a3b8] text-sm mr-1">{t('billing.perMonth')}</span>}
                  </div>
                  <ul className="space-y-2 mb-5">
                    <li className="flex items-center gap-2 text-[#94a3b8] text-sm">
                      <Check className="w-4 h-4 text-[#64748b] flex-shrink-0" />
                      {plan.messages_per_month === -1
                        ? `${t('billing.unlimited')} ${i18n.language === 'he' ? 'הודעות' : 'messages'}`
                        : `${plan.messages_per_month} ${t('billing.messagesPerMonthShort')}`}
                    </li>
                    <li className="flex items-center gap-2 text-[#94a3b8] text-sm">
                      <Check className="w-4 h-4 text-[#64748b] flex-shrink-0" />
                      {getFeatureText(plan)}
                    </li>
                    {plan.features?.journal_access && (
                      <li className="flex items-center gap-2 text-[#94a3b8] text-sm">
                        <Check className="w-4 h-4 text-[#64748b] flex-shrink-0" />
                        {i18n.language === 'he' ? 'יומן אישי' : 'Personal journal'}
                      </li>
                    )}
                    {plan.features?.priority_support && (
                      <li className="flex items-center gap-2 text-[#94a3b8] text-sm">
                        <Check className="w-4 h-4 text-[#64748b] flex-shrink-0" />
                        {t('billing.personalSupport')}
                      </li>
                    )}
                  </ul>
                  {!isCurrent && plan.price > 0 && (
                    <button
                      onClick={() => setShowUpgradeNote(true)}
                      className="w-full py-2.5 rounded-lg bg-white/10 text-[#F5F5F0] text-sm font-medium hover:bg-white/15 transition-colors"
                    >
                      {i18n.language === 'he' ? 'שדרג עכשיו' : 'Upgrade now'}
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
                {i18n.language === 'he' ? 'פרטי תשלום' : 'Payment details'}
              </h3>
              <p className="text-[#94a3b8] text-sm">
                {i18n.language === 'he'
                  ? 'חיבור כרטיס אשראי ותשלום מאובטח יעלה בקרוב. בינתיים ניתן להשתמש בקוד קופון למעלה.'
                  : 'Credit card connection and secure payment coming soon. You can use a coupon code above for now.'}
              </p>
            </div>
          </div>
        </div>

        {/* Upgrade note modal */}
        {showUpgradeNote && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60" onClick={() => setShowUpgradeNote(false)}>
            <div className="bg-[#1e293b] rounded-lg p-6 max-w-sm border border-white/10" onClick={(e) => e.stopPropagation()}>
              <h3 className="text-lg font-medium text-[#F5F5F0] mb-2">
                {i18n.language === 'he' ? 'שדרוג חבילה' : 'Upgrade plan'}
              </h3>
              <p className="text-[#94a3b8] text-sm mb-4">
                {i18n.language === 'he'
                  ? 'טופס חיבור כרטיס אשראי יעלה בקרוב. בינתיים ניתן להשתמש בקוד BSD100 לקבלת גישה חינמית ל-PRO.'
                  : 'Credit card form coming soon. You can use code BSD100 for free PRO access in the meantime.'}
              </p>
              <button
                onClick={() => setShowUpgradeNote(false)}
                className="w-full py-2 rounded-lg bg-white/10 text-[#F5F5F0] text-sm font-medium hover:bg-white/15"
              >
                {i18n.language === 'he' ? 'הבנתי' : 'Got it'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
