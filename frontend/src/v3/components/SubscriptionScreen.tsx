import { useCallback, useEffect, useState } from 'react';
import { X, Check, Sparkles, Ticket, Loader2 } from 'lucide-react';
import { fetchWithAuthRetry } from '../services/api';
import { getApiBase } from '../../config';
import { PayMeCheckoutModal } from '../../components/PayMeCheckoutModal';
import { formatCouponRedeemError } from '../../lib/couponRedeemError';
import { useTranslation } from 'react-i18next';

// "המנוי שלי" (Nov 8): V3 had no subscription screen — the limit window's upgrade button sent to /billing, which V3
// doesn't route, so the app just reloaded. Usage, the two plans, a coupon and the PayMe checkout, in V3's style.
// Opened from the menu, or by the limit window (reason "quota": the conversation is kept, continue after).

interface Plan { id: string; name_he: string; name_en: string; price: number; currency: string; messages_per_month: number }
interface Overview {
  current_plan: string;
  usage: { messages_used: number; messages_limit: number };
  available_plans: Plan[];
  has_active_coupon: boolean;
  coupon_code?: string | null;
  payme_checkout?: { merchant_public_key: string; test_mode: boolean; checkout_js_url?: string } | null;
}

interface Props {
  open: boolean;
  reason?: 'menu' | 'quota';
  gender?: string | null;
  getToken: (opts?: { skipCache?: boolean }) => Promise<string | null>;
  onClose: (canContinue: boolean) => void;
}

const HEEBO = { fontFamily: "'Heebo', sans-serif" };
const INK = '#2d4658';
const MUTED = 'rgba(45,70,88,0.6)';

export function SubscriptionScreen({ open, reason = 'menu', gender, getToken, onClose }: Props) {
  const { t } = useTranslation();
  const fem = gender === 'female';
  const g = (m: string, f: string) => (fem ? f : m);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);
  const [code, setCode] = useState('');
  const [couponBusy, setCouponBusy] = useState(false);
  const [couponMsg, setCouponMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [checkoutPlan, setCheckoutPlan] = useState<Plan | null>(null);

  const load = useCallback(async () => {
    setLoadFailed(false);
    try {
      const res = await fetchWithAuthRetry(`${getApiBase()}/billing/overview`, getToken);
      if (!res.ok) throw new Error(String(res.status));
      setOverview(await res.json());
    } catch {
      setLoadFailed(true);
    }
  }, [getToken]);

  useEffect(() => { if (open) void load(); }, [open, load]);

  if (!open) return null;

  const used = overview?.usage.messages_used ?? 0;
  const limit = overview?.usage.messages_limit ?? 0;
  const unlimited = limit === -1;
  const left = unlimited ? Infinity : Math.max(0, limit - used);
  const pct = unlimited || !limit ? 0 : Math.min(100, Math.round((100 * used) / limit));
  const outOfMessages = !unlimited && limit > 0 && left === 0;
  const premium = overview?.available_plans.find((p) => p.id === 'premium');
  const basic = overview?.available_plans.find((p) => p.id === 'basic');
  const onPremium = overview?.current_plan === 'premium';

  const redeem = async () => {
    if (!code.trim() || couponBusy) return;
    setCouponBusy(true);
    setCouponMsg(null);
    try {
      const res = await fetchWithAuthRetry(`${getApiBase()}/billing/redeem-coupon`, getToken, {
        method: 'POST', body: JSON.stringify({ code: code.trim() }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        setCouponMsg({ ok: true, text: data.message || 'הקופון הופעל ✓' });
        setCode('');
        void load();
      } else {
        setCouponMsg({ ok: false, text: formatCouponRedeemError(data.detail, t) });
      }
    } catch {
      setCouponMsg({ ok: false, text: 'אין חיבור לשרת. אפשר לנסות שוב.' });
    } finally {
      setCouponBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[75] bg-[#f6f4f0] overflow-y-auto" dir="rtl" style={HEEBO}>
      <header className="sticky top-0 z-10 bg-[#2d4658] text-white px-4 h-[64px] flex items-center gap-3">
        <h1 className="text-lg font-semibold flex-1">המנוי שלי</h1>
        <button type="button" onClick={() => onClose(!outOfMessages)} className="p-2 rounded-lg hover:bg-white/10" aria-label="סגירה">
          <X size={20} />
        </button>
      </header>

      <div className="max-w-lg mx-auto p-4 space-y-4 pb-16">
        {reason === 'quota' && outOfMessages && (
          <div className="rounded-2xl p-4 text-white" style={{ background: 'linear-gradient(135deg, #9747ff 0%, #6b2fd6 100%)' }}>
            <p className="text-base font-semibold">ההודעות שלך נגמרו</p>
            <p className="text-sm mt-1 leading-relaxed opacity-90">
              השיחה שלך שמורה בדיוק איפה שעצרת. כדי להמשיך — {g('הצטרף', 'הצטרפי')} לפרמיום או {g('ממש', 'ממשי')} קוד קופון.
            </p>
          </div>
        )}

        {!overview ? (
          <div className="bg-white rounded-2xl p-8 text-center text-sm" style={{ color: MUTED }}>
            {loadFailed
              ? <button type="button" onClick={() => void load()} className="underline">הטעינה נכשלה — לנסות שוב</button>
              : <Loader2 className="inline animate-spin" size={20} />}
          </div>
        ) : (
          <>
            {/* usage */}
            <section className="bg-white rounded-2xl p-4 shadow-sm space-y-3">
              <div className="flex items-baseline justify-between">
                <h2 className="text-sm font-semibold" style={{ color: INK }}>השימוש שלך</h2>
                <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: 'rgba(3,255,230,0.18)', color: INK }}>
                  {onPremium ? 'פרמיום' : overview.has_active_coupon ? `קופון ${overview.coupon_code ?? ''}`.trim() : 'בסיסי'}
                </span>
              </div>
              {unlimited ? (
                <p className="text-2xl font-semibold" style={{ color: INK }}>הודעות ללא הגבלה</p>
              ) : (
                <>
                  <p className="text-sm" style={{ color: INK }}>
                    <span className="text-3xl font-semibold">{used}</span>
                    <span style={{ color: MUTED }}> מתוך {limit} הודעות</span>
                  </p>
                  <div className="h-2.5 rounded-full bg-[#efece7] overflow-hidden" role="progressbar" aria-valuenow={used} aria-valuemin={0} aria-valuemax={limit}>
                    <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: pct >= 90 ? '#d97706' : '#9747ff' }} />
                  </div>
                  <p className="text-xs" style={{ color: outOfMessages ? '#b45309' : MUTED }}>
                    {outOfMessages ? 'לא נשארו הודעות' : `נשארו ${left} הודעות`} · כל הודעה שלך וכל כרטיס שממולא נספרים
                  </p>
                </>
              )}
            </section>

            {/* plans */}
            {!onPremium && premium && (
              <section className="space-y-3">
                <div className="bg-white rounded-2xl p-4 shadow-sm border-2 border-[#9747ff] relative">
                  <span className="absolute -top-3 right-4 text-[11px] font-semibold text-white bg-[#9747ff] px-2 py-0.5 rounded-full">מומלץ</span>
                  <div className="flex items-baseline justify-between">
                    <h3 className="text-lg font-semibold flex items-center gap-1.5" style={{ color: INK }}>
                      <Sparkles size={18} className="text-[#9747ff]" /> פרמיום
                    </h3>
                    <p style={{ color: INK }}><span className="text-2xl font-semibold">{premium.price} ₪</span><span className="text-xs" style={{ color: MUTED }}> לחודש</span></p>
                  </div>
                  <ul className="mt-3 space-y-1.5 text-sm" style={{ color: INK }}>
                    {['הודעות ללא הגבלה — תהליכים שלמים, בלי לעצור באמצע', 'אפשר לפתוח תהליך חדש בכל זמן'].map((f) => (
                      <li key={f} className="flex gap-2"><Check size={16} className="text-[#009081] shrink-0 mt-0.5" />{f}</li>
                    ))}
                  </ul>
                  <button type="button" onClick={() => setCheckoutPlan(premium)}
                    className="mt-4 w-full h-[50px] rounded-xl bg-[#9747ff] hover:bg-[#8035e6] text-white text-base font-medium transition-colors drop-shadow-[0px_6px_2px_rgba(0,0,0,0.10)]">
                    {g('הצטרף לפרמיום', 'הצטרפי לפרמיום')}
                  </button>
                  <p className="text-[11px] text-center mt-2" style={{ color: MUTED }}>תשלום מאובטח בכרטיס אשראי דרך PayMe</p>
                </div>

                {basic && (
                  <div className="bg-white/70 rounded-2xl p-4 border border-[#e0ddd8] flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-semibold" style={{ color: INK }}>בסיסי <span className="text-xs font-normal" style={{ color: MUTED }}>· המסלול שלך</span></h3>
                      <p className="text-xs mt-0.5" style={{ color: MUTED }}>{basic.messages_per_month} הודעות בסך הכול</p>
                    </div>
                    <span className="text-sm font-semibold" style={{ color: INK }}>חינם</span>
                  </div>
                )}
              </section>
            )}

            {/* coupon */}
            <section className="bg-white rounded-2xl p-4 shadow-sm space-y-3">
              <h2 className="text-sm font-semibold flex items-center gap-1.5" style={{ color: INK }}><Ticket size={16} className="text-[#9747ff]" /> יש לך קוד קופון?</h2>
              <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); void redeem(); }}>
                <input value={code} onChange={(e) => setCode(e.target.value)} placeholder="קוד הקופון" dir="ltr"
                  className="flex-1 min-w-0 h-[44px] px-3 rounded-xl border border-[#e0ddd8] text-sm text-center tracking-wider uppercase focus:outline-none focus:border-[#9747ff]" />
                <button type="submit" disabled={couponBusy || !code.trim()}
                  className="h-[44px] px-5 rounded-xl border border-[#9747ff] text-[#9747ff] text-sm font-medium hover:bg-[#9747ff]/5 disabled:opacity-50">
                  {couponBusy ? '...' : 'מימוש'}
                </button>
              </form>
              {couponMsg && <p className={`text-sm ${couponMsg.ok ? 'text-[#009081]' : 'text-red-600'}`}>{couponMsg.text}</p>}
            </section>

            {reason === 'quota' && !outOfMessages && (
              <button type="button" onClick={() => onClose(true)}
                className="w-full h-[50px] rounded-xl bg-[#2d4658] text-white text-base font-medium">
                {g('חזור לשיחה', 'חזרי לשיחה')} ←
              </button>
            )}
          </>
        )}
      </div>

      {checkoutPlan && (
        <PayMeCheckoutModal
          open
          plan={checkoutPlan}
          payMeCheckoutFromOverview={overview?.payme_checkout ?? null}
          getToken={getToken}
          onClose={() => setCheckoutPlan(null)}
          onCompleted={() => { setCheckoutPlan(null); void load(); }}
        />
      )}
    </div>
  );
}
