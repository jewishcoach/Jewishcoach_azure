import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { motion } from 'framer-motion';
import { Check, Sparkles, Zap, Crown, Gift, Loader2 } from 'lucide-react';

interface Plan {
  id: string;
  name_he: string;
  name_en: string;
  price: number;
  currency: string;
  messages_per_month: number;
  speech_minutes_per_month: number;
  features: { coaching_phases?: string; journal_access?: boolean; priority_support?: boolean };
}

interface Usage {
  messages_used: number;
  messages_limit: number;
  speech_minutes_used: number;
  speech_minutes_limit: number;
  plan: string;
  period_end: string;
}

interface BillingOverview {
  current_plan: string;
  usage: Usage;
  available_plans: Plan[];
  has_active_coupon: boolean;
  coupon_code?: string;
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const BillingPage = () => {
  const { getToken } = useAuth();
  const [overview, setOverview] = useState<BillingOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [couponCode, setCouponCode] = useState('');
  const [couponMessage, setCouponMessage] = useState<{type: 'success' | 'error', text: string} | null>(null);
  const loadBillingData = useCallback(async () => {
    try {
      const token = await getToken();
      const response = await fetch(`${API_URL}/api/billing/overview`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      const data = await response.json();
      setOverview(data);
    } catch (err) {
      console.error('Error loading billing data:', err);
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    loadBillingData();
  }, [loadBillingData]);

  const handleRedeemCoupon = async () => {
    if (!couponCode.trim()) return;
    
    try {
      const token = await getToken();
      const response = await fetch(`${API_URL}/api/billing/redeem-coupon`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ code: couponCode.toUpperCase() })
      });
      
      const data = await response.json();
      
      if (response.ok) {
        setCouponMessage({ type: 'success', text: data.message });
        setCouponCode('');
        setTimeout(() => loadBillingData(), 1000);
      } else {
        setCouponMessage({ type: 'error', text: data.detail });
      }
    } catch {
      setCouponMessage({ type: 'error', text: 'שגיאה בהפעלת הקופון' });
    }
  };

  const getPlanIcon = (planId: string) => {
    switch(planId) {
      case 'basic': return <Sparkles className="w-8 h-8" />;
      case 'premium': return <Zap className="w-8 h-8" />;
      case 'pro': return <Crown className="w-8 h-8" />;
      default: return null;
    }
  };

  const getPlanColor = (planId: string) => {
    switch(planId) {
      case 'basic': return 'border-gray-300 bg-gray-50';
      case 'premium': return 'border-accent bg-accent/5';
      case 'pro': return 'border-primary bg-primary/5';
      default: return '';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-purple-50">
        <div className="text-center">
          <Loader2 className="animate-spin h-12 w-12 text-accent mx-auto" />
          <p className="mt-4 text-gray-600">טוען נתוני חיוב...</p>
        </div>
      </div>
    );
  }

  if (!overview) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-purple-50">
        <div className="text-center p-8 bg-white rounded-xl shadow-lg">
          <p className="text-red-600 font-bold">שגיאה בטעינת נתוני חיוב</p>
          <button 
            onClick={loadBillingData}
            className="mt-4 px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent-dark"
          >
            נסה שוב
          </button>
        </div>
      </div>
    );
  }

  const usage = overview.usage;
  const messagesPercent = usage.messages_limit === -1 ? 0 : (usage.messages_used / usage.messages_limit) * 100;
  const speechPercent = usage.speech_minutes_limit === -1 ? 0 : (usage.speech_minutes_used / usage.speech_minutes_limit) * 100;

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 p-8" dir="rtl">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-primary mb-2">המנוי שלי</h1>
          <p className="text-gray-600">נהל את המנוי והשימוש שלך</p>
        </div>

        {/* Coupon Badge */}
        {overview.has_active_coupon && (
          <motion.div
            className="mb-8 p-4 bg-gradient-to-r from-primary to-accent rounded-xl text-white text-center"
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <Gift className="w-6 h-6 inline-block ml-2" />
            <span className="font-bold">יש לך קופון פעיל: {overview.coupon_code}</span>
          </motion.div>
        )}

        {/* Usage Stats */}
        <div className="grid md:grid-cols-2 gap-6 mb-12">
          {/* Messages Usage */}
          <motion.div
            className="bg-white rounded-2xl p-6 shadow-lg"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <h3 className="text-lg font-bold mb-4">שימוש בהודעות</h3>
            <div className="mb-2">
              <div className="flex justify-between text-sm mb-1">
                <span>{usage.messages_used}</span>
                <span>{usage.messages_limit === -1 ? '∞' : usage.messages_limit}</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-accent h-2 rounded-full transition-all"
                  style={{ width: `${usage.messages_limit === -1 ? 0 : Math.min(messagesPercent, 100)}%` }}
                />
              </div>
            </div>
            {usage.messages_limit !== -1 && (
              <p className="text-sm text-gray-600 mt-2">
                נותרו {usage.messages_limit - usage.messages_used} הודעות עד סוף התקופה
              </p>
            )}
            {usage.messages_limit === -1 && (
              <p className="text-sm text-primary font-bold mt-2">
                ✨ הודעות ללא הגבלה
              </p>
            )}
          </motion.div>

          {/* Speech Usage */}
          <motion.div
            className="bg-white rounded-2xl p-6 shadow-lg"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <h3 className="text-lg font-bold mb-4">זמן דיבור</h3>
            <div className="mb-2">
              <div className="flex justify-between text-sm mb-1">
                <span>{usage.speech_minutes_used} דקות</span>
                <span>{usage.speech_minutes_limit === -1 ? '∞' : `${usage.speech_minutes_limit} דקות`}</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-primary h-2 rounded-full transition-all"
                  style={{ width: `${usage.speech_minutes_limit === -1 ? 0 : Math.min(speechPercent, 100)}%` }}
                />
              </div>
            </div>
            {usage.speech_minutes_limit !== -1 && (
              <p className="text-sm text-gray-600 mt-2">
                נותרו {usage.speech_minutes_limit - usage.speech_minutes_used} דקות עד סוף התקופה
              </p>
            )}
            {usage.speech_minutes_limit === -1 && (
              <p className="text-sm text-primary font-bold mt-2">
                ✨ זמן דיבור ללא הגבלה
              </p>
            )}
          </motion.div>
        </div>

        {/* Coupon Redemption */}
        {!overview.has_active_coupon && (
          <motion.div
            className="bg-white rounded-2xl p-6 shadow-lg mb-12"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
              <Gift className="w-5 h-5" />
              יש לך קוד קופון?
            </h3>
            <div className="flex gap-2">
              <input
                type="text"
                value={couponCode}
                onChange={(e) => setCouponCode(e.target.value.toUpperCase())}
                placeholder="הקלד קוד קופון (למשל: BSD100)"
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-accent focus:border-transparent"
                dir="ltr"
              />
              <button
                onClick={handleRedeemCoupon}
                className="px-6 py-2 bg-accent text-white rounded-lg hover:bg-accent-dark transition-colors font-bold"
              >
                הפעל
              </button>
            </div>
            {couponMessage && (
              <div className={`mt-3 p-3 rounded-lg ${
                couponMessage.type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
              }`}>
                {couponMessage.text}
              </div>
            )}
          </motion.div>
        )}

        {/* Plans */}
        <div>
          <h2 className="text-2xl font-bold text-center mb-8">החבילות שלנו</h2>
          <div className="grid md:grid-cols-3 gap-6">
            {overview.available_plans.map((plan, index) => {
              const isCurrent = plan.id === overview.current_plan;
              return (
                <motion.div
                  key={plan.id}
                  className={`relative rounded-2xl p-6 border-2 ${getPlanColor(plan.id)} ${
                    isCurrent ? 'ring-4 ring-accent shadow-xl' : 'shadow-lg'
                  }`}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                >
                  {isCurrent && (
                    <div className="absolute -top-3 left-1/2 transform -translate-x-1/2 bg-accent text-white px-4 py-1 rounded-full text-sm font-bold">
                      החבילה הנוכחית
                    </div>
                  )}
                  
                  <div className="text-center mb-4">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-white shadow-md mb-3">
                      {getPlanIcon(plan.id)}
                    </div>
                    <h3 className="text-2xl font-bold">{plan.name_he}</h3>
                    <div className="mt-2">
                      <span className="text-3xl font-bold">₪{plan.price}</span>
                      {plan.price > 0 && <span className="text-gray-600">/חודש</span>}
                    </div>
                  </div>

                  <ul className="space-y-2 mb-6">
                    <li className="flex items-start gap-2">
                      <Check className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                      <span>
                        {plan.messages_per_month === -1 ? 'הודעות ללא הגבלה' : `${plan.messages_per_month} הודעות/חודש`}
                      </span>
                    </li>
                    <li className="flex items-start gap-2">
                      <Check className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                      <span>
                        {plan.speech_minutes_per_month === -1 ? 'דיבור ללא הגבלה' : 
                         plan.speech_minutes_per_month === 0 ? 'ללא זמן דיבור' :
                         `${plan.speech_minutes_per_month} דקות דיבור`}
                      </span>
                    </li>
                    <li className="flex items-start gap-2">
                      <Check className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                      <span>
                        {plan.features.coaching_phases === 'all' ? 'גישה לכל 9 שלבי האימון' : 'שלבי אימון בסיסיים'}
                      </span>
                    </li>
                    {plan.features.journal_access && (
                      <li className="flex items-start gap-2">
                        <Check className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                        <span>יומן אישי</span>
                      </li>
                    )}
                    {plan.features.priority_support && (
                      <li className="flex items-start gap-2">
                        <Check className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                        <span>תמיכה עדיפות</span>
                      </li>
                    )}
                  </ul>

                  {!isCurrent && plan.price > 0 && (
                    <button className="w-full py-3 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors font-bold">
                      שדרג עכשיו
                    </button>
                  )}
                </motion.div>
              );
            })}
          </div>
        </div>

        {/* Info Box */}
        <div className="mt-12 p-6 bg-blue-50 rounded-xl text-center">
          <p className="text-gray-700">
            💡 <strong>טיפ:</strong> משתמשים עם הקוד <code className="bg-white px-2 py-1 rounded">BSD100</code> מקבלים גישה חינמית לצמיתות לחבילת PRO!
          </p>
        </div>
      </div>
    </div>
  );
};

