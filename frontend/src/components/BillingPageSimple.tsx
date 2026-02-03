import { useState } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { useTranslation } from 'react-i18next';
import { Gift, Sparkles, Check, Crown, Zap } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const BillingPageSimple = () => {
  const { getToken } = useAuth();
  const { t } = useTranslation();
  const [couponCode, setCouponCode] = useState('');
  const [couponMessage, setCouponMessage] = useState<{type: 'success' | 'error', text: string} | null>(null);
  const [loading, setLoading] = useState(false);

  const handleRedeemCoupon = async () => {
    if (!couponCode.trim()) return;
    
    setLoading(true);
    setCouponMessage(null);
    
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
        setCouponMessage({ type: 'success', text: data.message || t('billing.couponSuccess') });
        setCouponCode('');
      } else {
        setCouponMessage({ type: 'error', text: data.detail || t('billing.couponError') });
      }
    } catch (error) {
      console.error('Coupon error:', error);
      setCouponMessage({ type: 'error', text: t('billing.couponServerError') });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 w-full bg-gradient-to-br from-blue-50 via-white to-purple-50 overflow-y-auto" dir="rtl">
      <div className="max-w-6xl mx-auto p-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-primary mb-2">{t('billing.title')}</h1>
          <p className="text-gray-600">{t('billing.subtitle')}</p>
        </div>

        {/* Coupon Section */}
        <div className="bg-white rounded-2xl p-8 shadow-lg mb-8 max-w-2xl mx-auto">
          <h3 className="text-2xl font-bold mb-4 flex items-center gap-2">
            <Gift className="w-6 h-6 text-accent" />
            {t('billing.couponTitle')}
          </h3>
          <p className="text-gray-600 mb-4">
            הזן את קוד הקופון <strong className="text-accent">BSD100</strong> כדי לקבל גישה חינמית לצמיתות לחבילת PRO!
          </p>
          <div className="flex gap-2">
            <input
              type="text"
              value={couponCode}
              onChange={(e) => setCouponCode(e.target.value.toUpperCase())}
              placeholder={t('billing.couponPlaceholder')}
              className="flex-1 px-4 py-3 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-accent focus:border-accent text-lg"
              dir="ltr"
              disabled={loading}
            />
            <button
              onClick={handleRedeemCoupon}
              disabled={loading || !couponCode.trim()}
              className="px-8 py-3 bg-accent text-white rounded-lg hover:bg-accent-dark transition-colors font-bold text-lg disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? t('billing.couponActivating') : t('billing.couponActivate')}
            </button>
          </div>
          {couponMessage && (
            <div className={`mt-4 p-4 rounded-lg ${
              couponMessage.type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
            }`}>
              <p className="font-bold">{couponMessage.text}</p>
              {couponMessage.type === 'success' && (
                <p className="text-sm mt-2">🎉 יש לך כעת גישה מלאה לכל הפיצ'רים!</p>
              )}
            </div>
          )}
        </div>

        {/* Plans Grid */}
        <div className="grid md:grid-cols-3 gap-6 mb-8">
          {/* Basic Plan */}
          <div className="bg-white rounded-2xl p-6 shadow-lg border-2 border-gray-200">
            <div className="text-center mb-6">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gray-100 mb-3">
                <Sparkles className="w-8 h-8 text-gray-600" />
              </div>
              <h3 className="text-2xl font-bold">בסיסי</h3>
              <div className="mt-2">
                <span className="text-4xl font-bold">חינם</span>
              </div>
            </div>
            <ul className="space-y-3 mb-6">
              <li className="flex items-start gap-2">
                <Check className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                <span>10 הודעות/חודש</span>
              </li>
              <li className="flex items-start gap-2">
                <Check className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                <span>ללא זמן דיבור</span>
              </li>
              <li className="flex items-start gap-2">
                <Check className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                <span>שלבי אימון בסיסיים</span>
              </li>
            </ul>
          </div>

          {/* Premium Plan */}
          <div className="bg-white rounded-2xl p-6 shadow-lg border-2 border-accent">
            <div className="text-center mb-6">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-accent/10 mb-3">
                <Zap className="w-8 h-8 text-accent" />
              </div>
              <h3 className="text-2xl font-bold">פרמיום</h3>
              <div className="mt-2">
                <span className="text-4xl font-bold">₪89</span>
                <span className="text-gray-600">/חודש</span>
              </div>
            </div>
            <ul className="space-y-3 mb-6">
              <li className="flex items-start gap-2">
                <Check className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                <span>100 הודעות/חודש</span>
              </li>
              <li className="flex items-start gap-2">
                <Check className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                <span>30 דקות דיבור</span>
              </li>
              <li className="flex items-start gap-2">
                <Check className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                <span>כל 9 שלבי האימון</span>
              </li>
              <li className="flex items-start gap-2">
                <Check className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                <span>יומן אישי</span>
              </li>
            </ul>
          </div>

          {/* Pro Plan */}
          <div className="bg-gradient-to-br from-primary to-accent text-white rounded-2xl p-6 shadow-xl transform scale-105">
            <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-yellow-400 text-primary px-4 py-1 rounded-full text-sm font-bold">
              מומלץ ביותר
            </div>
            <div className="text-center mb-6">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-white/20 mb-3">
                <Crown className="w-8 h-8" />
              </div>
              <h3 className="text-2xl font-bold">PRO</h3>
              <div className="mt-2">
                <span className="text-4xl font-bold">₪249</span>
                <span>/חודש</span>
              </div>
            </div>
            <ul className="space-y-3 mb-6">
              <li className="flex items-start gap-2">
                <Check className="w-5 h-5 flex-shrink-0 mt-0.5" />
                <span>הודעות ללא הגבלה</span>
              </li>
              <li className="flex items-start gap-2">
                <Check className="w-5 h-5 flex-shrink-0 mt-0.5" />
                <span>דיבור ללא הגבלה</span>
              </li>
              <li className="flex items-start gap-2">
                <Check className="w-5 h-5 flex-shrink-0 mt-0.5" />
                <span>כל הפיצ'רים</span>
              </li>
              <li className="flex items-start gap-2">
                <Check className="w-5 h-5 flex-shrink-0 mt-0.5" />
                <span>תמיכה עדיפות</span>
              </li>
            </ul>
            <div className="bg-white/20 rounded-lg p-3 text-center">
              <p className="text-sm font-bold">🎁 חינם עם BSD100!</p>
            </div>
          </div>
        </div>

        {/* Info Box */}
        <div className="bg-blue-50 rounded-xl p-6 text-center border-2 border-blue-200">
          <p className="text-lg">
            💡 <strong>טיפ:</strong> הזן את הקוד <code className="bg-white px-3 py-1 rounded font-mono text-accent font-bold">BSD100</code> למעלה כדי לקבל גישה חינמית לצמיתות לחבילת PRO!
          </p>
        </div>
      </div>
    </div>
  );
};

