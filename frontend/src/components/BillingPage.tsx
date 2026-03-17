import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { Check, Sparkles, Zap, Crown, Gift, Loader2, MessageSquare, Mic } from 'lucide-react';

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

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const GOLD_GRADIENT = 'linear-gradient(135deg, #BF953F, #FCF6BA, #B38728)';

export const BillingPage = () => {
  const { getToken } = useAuth();
  const { t, i18n } = useTranslation();
  const [overview, setOverview] = useState<BillingOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [couponCode, setCouponCode] = useState('');
  const [couponMessage, setCouponMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [couponLoading, setCouponLoading] = useState(false);

  const loadBillingData = useCallback(async () => {
    try {
      const token = await getToken();
      const response = await fetch(`${API_URL}/api/billing/overview`, {
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
      const response = await fetch(`${API_URL}/api/billing/redeem-coupon`, {
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

  const getPlanIcon = (planId: string) => {
    switch (planId) {
      case 'basic':
        return <Sparkles className="w-7 h-7 text-[#F5F5F0]/90" />;
      case 'premium':
        return <Zap className="w-7 h-7 text-[#FCF6BA]" />;
      case 'pro':
        return <Crown className="w-7 h-7 text-[#FCF6BA]" />;
      default:
        return null;
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
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex flex-col items-center gap-4"
        >
          <Loader2 className="w-12 h-12 text-[#FCF6BA] animate-spin" />
          <p className="text-[#F5F5F0]/70 font-light" style={{ fontFamily: 'Heebo, Inter, sans-serif' }}>
            {i18n.language === 'he' ? 'טוען נתוני חיוב...' : 'Loading billing data...'}
          </p>
        </motion.div>
      </div>
    );
  }

  if (!overview) {
    return (
      <div className="flex-1 w-full bg-[#0F172A] flex items-center justify-center min-h-0 p-8" dir="rtl">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white/[0.04] rounded-2xl p-8 border border-white/[0.08] max-w-md text-center"
        >
          <p className="text-red-300 font-medium mb-4">
            {i18n.language === 'he' ? 'שגיאה בטעינת נתוני חיוב' : 'Error loading billing data'}
          </p>
          <button
            onClick={loadBillingData}
            className="px-6 py-3 rounded-xl font-medium transition-colors"
            style={{ background: GOLD_GRADIENT, color: '#020617' }}
          >
            {i18n.language === 'he' ? 'נסה שוב' : 'Try again'}
          </button>
        </motion.div>
      </div>
    );
  }

  const usage = overview.usage;
  const messagesPercent = usage.messages_limit === -1 ? 0 : Math.min((usage.messages_used / usage.messages_limit) * 100, 100);
  const speechPercent = usage.speech_minutes_limit === -1 ? 0 : Math.min((usage.speech_minutes_used / usage.speech_minutes_limit) * 100, 100);

  return (
    <div className="flex-1 w-full bg-[#0F172A] overflow-y-auto custom-scrollbar" dir="rtl">
      <div className="max-w-6xl mx-auto p-6 md:p-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-10"
        >
          <h1
            className="text-3xl md:text-4xl font-bold text-[#F5F5F0] mb-2"
            style={{ fontFamily: 'Cormorant Garamond, Georgia, serif' }}
          >
            {t('billing.title')}
          </h1>
          <p className="text-[#F5F5F0]/70 text-lg" style={{ fontFamily: 'Heebo, Inter, sans-serif' }}>
            {t('billing.subtitle')}
          </p>
        </motion.div>

        {/* Active Coupon Badge */}
        {overview.has_active_coupon && (
          <motion.div
            initial={{ opacity: 0, y: -15 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-8 p-4 rounded-2xl border border-[#FCF6BA]/30 text-center"
            style={{ background: 'linear-gradient(135deg, rgba(191,149,63,0.15), rgba(252,246,186,0.08))' }}
          >
            <Gift className="w-5 h-5 inline-block ml-2 text-[#FCF6BA]" />
            <span className="font-bold text-[#F5F5F0]">
              {i18n.language === 'he' ? 'קופון פעיל:' : 'Active coupon:'} {overview.coupon_code}
            </span>
          </motion.div>
        )}

        {/* Usage Stats */}
        <div className="grid md:grid-cols-2 gap-5 mb-10">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.05 }}
            className="bg-white/[0.04] rounded-2xl p-6 border border-white/[0.08]"
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-[#FCF6BA]/10 flex items-center justify-center">
                <MessageSquare className="w-5 h-5 text-[#FCF6BA]" />
              </div>
              <h3 className="text-lg font-semibold text-[#F5F5F0]" style={{ fontFamily: 'Heebo, sans-serif' }}>
                {i18n.language === 'he' ? 'שימוש בהודעות' : 'Messages used'}
              </h3>
            </div>
            <div className="flex justify-between text-sm mb-2">
              <span className="text-[#F5F5F0]/80">{usage.messages_used}</span>
              <span className="text-[#F5F5F0]/60">{usage.messages_limit === -1 ? '∞' : usage.messages_limit}</span>
            </div>
            <div className="w-full h-2 bg-white/[0.06] rounded-full overflow-hidden">
              <motion.div
                className="h-full rounded-full"
                style={{ background: GOLD_GRADIENT }}
                initial={{ width: 0 }}
                animate={{ width: `${usage.messages_limit === -1 ? 0 : messagesPercent}%` }}
                transition={{ duration: 0.6, ease: 'easeOut' }}
              />
            </div>
            {usage.messages_limit !== -1 && (
              <p className="text-sm text-[#F5F5F0]/60 mt-2">
                {i18n.language === 'he'
                  ? `נותרו ${usage.messages_limit - usage.messages_used} הודעות`
                  : `${usage.messages_limit - usage.messages_used} remaining`}
              </p>
            )}
            {usage.messages_limit === -1 && (
              <p className="text-sm text-[#FCF6BA] font-medium mt-2">✨ {t('billing.unlimited')}</p>
            )}
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-white/[0.04] rounded-2xl p-6 border border-white/[0.08]"
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-[#FCF6BA]/10 flex items-center justify-center">
                <Mic className="w-5 h-5 text-[#FCF6BA]" />
              </div>
              <h3 className="text-lg font-semibold text-[#F5F5F0]" style={{ fontFamily: 'Heebo, sans-serif' }}>
                {i18n.language === 'he' ? 'זמן דיבור' : 'Speech time'}
              </h3>
            </div>
            <div className="flex justify-between text-sm mb-2">
              <span className="text-[#F5F5F0]/80">{usage.speech_minutes_used} {i18n.language === 'he' ? 'דק׳' : 'min'}</span>
              <span className="text-[#F5F5F0]/60">
                {usage.speech_minutes_limit === -1 ? '∞' : `${usage.speech_minutes_limit} ${i18n.language === 'he' ? 'דק׳' : 'min'}`}
              </span>
            </div>
            <div className="w-full h-2 bg-white/[0.06] rounded-full overflow-hidden">
              <motion.div
                className="h-full rounded-full"
                style={{ background: GOLD_GRADIENT }}
                initial={{ width: 0 }}
                animate={{ width: `${usage.speech_minutes_limit === -1 ? 0 : speechPercent}%` }}
                transition={{ duration: 0.6, ease: 'easeOut' }}
              />
            </div>
            {usage.speech_minutes_limit !== -1 && usage.speech_minutes_limit > 0 && (
              <p className="text-sm text-[#F5F5F0]/60 mt-2">
                {i18n.language === 'he'
                  ? `נותרו ${usage.speech_minutes_limit - usage.speech_minutes_used} דקות`
                  : `${usage.speech_minutes_limit - usage.speech_minutes_used} min remaining`}
              </p>
            )}
            {usage.speech_minutes_limit === 0 && (
              <p className="text-sm text-[#F5F5F0]/60 mt-2">{t('billing.noSpeech')}</p>
            )}
            {usage.speech_minutes_limit === -1 && (
              <p className="text-sm text-[#FCF6BA] font-medium mt-2">✨ {t('billing.unlimited')}</p>
            )}
          </motion.div>
        </div>

        {/* Coupon Redemption */}
        {!overview.has_active_coupon && (
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="bg-white/[0.04] rounded-2xl p-6 md:p-8 border border-white/[0.08] mb-10 max-w-2xl mx-auto"
          >
            <h3 className="text-xl font-bold mb-3 flex items-center gap-2 text-[#F5F5F0]">
              <Gift className="w-6 h-6 text-[#FCF6BA]" />
              {t('billing.couponTitle')}
            </h3>
            <p className="text-[#F5F5F0]/80 mb-4 text-sm">
              {i18n.language === 'he'
                ? 'הזן את הקוד BSD100 לקבלת גישה חינמית לצמיתות לחבילת PRO'
                : 'Enter code BSD100 for free lifetime PRO access'}
            </p>
            <div className="flex gap-3">
              <input
                type="text"
                value={couponCode}
                onChange={(e) => setCouponCode(e.target.value.toUpperCase())}
                placeholder={t('billing.couponPlaceholder')}
                className="flex-1 px-4 py-3 rounded-xl border border-white/10 bg-white/[0.04] text-[#F5F5F0] placeholder-[#F5F5F0]/40 focus:ring-2 focus:ring-[#FCF6BA]/30 focus:border-[#FCF6BA]/40 outline-none transition-all"
                dir="ltr"
                disabled={couponLoading}
              />
              <button
                onClick={handleRedeemCoupon}
                disabled={couponLoading || !couponCode.trim()}
                className="px-6 py-3 rounded-xl font-bold disabled:opacity-50 disabled:cursor-not-allowed transition-all hover:opacity-95"
                style={{ background: GOLD_GRADIENT, color: '#020617' }}
              >
                {couponLoading ? t('billing.couponActivating') : t('billing.couponActivate')}
              </button>
            </div>
            {couponMessage && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className={`mt-4 p-4 rounded-xl ${
                  couponMessage.type === 'success'
                    ? 'bg-[#FCF6BA]/15 text-[#FCF6BA] border border-[#FCF6BA]/30'
                    : 'bg-red-500/15 text-red-300 border border-red-500/30'
                }`}
              >
                <p className="font-medium">{couponMessage.text}</p>
                {couponMessage.type === 'success' && (
                  <p className="text-sm mt-1 opacity-90">{t('billing.successAccess')}</p>
                )}
              </motion.div>
            )}
          </motion.div>
        )}

        {/* Plans */}
        <div className="mb-10">
          <h2
            className="text-2xl font-bold text-center mb-8 text-[#F5F5F0]"
            style={{ fontFamily: 'Cormorant Garamond, Georgia, serif' }}
          >
            {t('billing.plansTitle')}
          </h2>
          <div className="grid md:grid-cols-3 gap-6">
            {overview.available_plans.map((plan, index) => {
              const isCurrent = plan.id === overview.current_plan;
              const isPro = plan.id === 'pro';
              return (
                <motion.div
                  key={plan.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 + index * 0.08 }}
                  className={`relative rounded-2xl p-6 border transition-all ${
                    isPro
                      ? 'bg-gradient-to-br from-[#0f172a] via-[#1e293b] to-[#0f172a] border-[#FCF6BA]/40 shadow-lg shadow-[#FCF6BA]/5'
                      : isCurrent
                        ? 'bg-white/[0.06] border-[#FCF6BA]/30'
                        : 'bg-white/[0.04] border-white/[0.08] hover:border-white/[0.12]'
                  }`}
                >
                  {isPro && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full text-sm font-bold bg-[#FCF6BA] text-[#020617]">
                      {i18n.language === 'he' ? 'מומלץ' : 'Recommended'}
                    </div>
                  )}
                  {isCurrent && !isPro && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full text-sm font-bold bg-[#FCF6BA]/20 text-[#FCF6BA] border border-[#FCF6BA]/40">
                      {t('billing.currentBadge')}
                    </div>
                  )}

                  <div className="text-center mb-6">
                    <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-white/10 mb-4">
                      {getPlanIcon(plan.id)}
                    </div>
                    <h3 className="text-2xl font-bold text-[#F5F5F0]">{plan.name_he}</h3>
                    <div className="mt-2">
                      <span className="text-3xl font-bold text-[#F5F5F0]">
                        {plan.price === 0 ? (i18n.language === 'he' ? 'חינם' : 'Free') : `₪${plan.price}`}
                      </span>
                      {plan.price > 0 && <span className="text-[#F5F5F0]/60">{t('billing.perMonth')}</span>}
                    </div>
                  </div>

                  <ul className="space-y-3 mb-6">
                    <li className="flex items-start gap-2 text-[#F5F5F0]/90">
                      <Check className="w-5 h-5 text-[#FCF6BA] flex-shrink-0 mt-0.5" />
                      <span>
                        {plan.messages_per_month === -1
                          ? `${t('billing.unlimited')} ${i18n.language === 'he' ? 'הודעות' : 'messages'}`
                          : `${plan.messages_per_month} ${t('billing.messagesPerMonthShort')}`}
                      </span>
                    </li>
                    <li className="flex items-start gap-2 text-[#F5F5F0]/90">
                      <Check className="w-5 h-5 text-[#FCF6BA] flex-shrink-0 mt-0.5" />
                      <span>
                        {plan.speech_minutes_per_month === -1
                          ? `${t('billing.unlimited')} ${t('billing.speechMinutesShort')}`
                          : plan.speech_minutes_per_month === 0
                            ? t('billing.noSpeech')
                            : `${plan.speech_minutes_per_month} ${t('billing.speechMinutesShort')}`}
                      </span>
                    </li>
                    <li className="flex items-start gap-2 text-[#F5F5F0]/90">
                      <Check className="w-5 h-5 text-[#FCF6BA] flex-shrink-0 mt-0.5" />
                      <span>{getFeatureText(plan)}</span>
                    </li>
                    {plan.features?.journal_access && (
                      <li className="flex items-start gap-2 text-[#F5F5F0]/90">
                        <Check className="w-5 h-5 text-[#FCF6BA] flex-shrink-0 mt-0.5" />
                        <span>{i18n.language === 'he' ? 'יומן אישי' : 'Personal journal'}</span>
                      </li>
                    )}
                    {plan.features?.priority_support && (
                      <li className="flex items-start gap-2 text-[#F5F5F0]/90">
                        <Check className="w-5 h-5 text-[#FCF6BA] flex-shrink-0 mt-0.5" />
                        <span>{t('billing.personalSupport')}</span>
                      </li>
                    )}
                  </ul>

                  {!isCurrent && plan.price > 0 && (
                    <button
                      className="w-full py-3 rounded-xl font-bold transition-all hover:opacity-95"
                      style={{ background: GOLD_GRADIENT, color: '#020617' }}
                    >
                      {i18n.language === 'he' ? 'שדרג עכשיו' : 'Upgrade now'}
                    </button>
                  )}
                </motion.div>
              );
            })}
          </div>
        </div>

        {/* Tip */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="bg-[#FCF6BA]/10 rounded-2xl p-6 text-center border border-[#FCF6BA]/20"
        >
          <p className="text-[#F5F5F0]/90">
            💡 <strong>{t('billing.tipTitle')}</strong>{' '}
            <code className="bg-white/10 px-3 py-1 rounded-lg font-mono text-[#FCF6BA] font-bold">BSD100</code>{' '}
            {t('billing.tipText')}
          </p>
        </motion.div>
      </div>
    </div>
  );
};
