import { useCallback, useEffect, useState } from 'react';
import { X, Check, Sparkles, Ticket, Loader2, Lock, Infinity as InfinityIcon, RotateCcw, ChevronDown } from 'lucide-react';
import { fetchWithAuthRetry } from '../services/api';
import { getApiBase } from '../../config';
import { PayMeCheckoutModal } from '../../components/PayMeCheckoutModal';
import { formatCouponRedeemError } from '../../lib/couponRedeemError';
import { useTranslation } from 'react-i18next';

// "המנוי שלי" (Nov 8): V3 had no subscription screen — the limit window's upgrade button sent to /billing, which V3
// doesn't route, so the app just reloaded. Usage, "גישה מלאה" (one payment, unlimited from then on — no monthly
// charge), Basic, a coupon and the PayMe checkout. Opened from the menu, or by the limit window (reason "quota").

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
const MUTED = 'rgba(45,70,88,0.62)';
const PURPLE = '#9747ff';

export function SubscriptionScreen({ open, reason = 'menu', gender, getToken, onClose }: Props) {
  const { t } = useTranslation();
  const g = (m: string, f: string) => (gender === 'female' ? f : m);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);
  const [code, setCode] = useState('');
  const [couponOpen, setCouponOpen] = useState(false);
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
  const full = overview?.available_plans.find((p) => p.id === 'premium');
  const basic = overview?.available_plans.find((p) => p.id === 'basic');
  const hasFull = overview?.current_plan === 'premium';

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

  const heroTitle = reason === 'quota' && outOfMessages ? 'ההודעות שלך נגמרו'
    : hasFull || unlimited ? 'יש לך גישה מלאה' : 'המסע שלך, בקצב שלך';
  const heroText = reason === 'quota' && outOfMessages
    ? `השיחה שמורה בדיוק איפה שעצרת. כדי להמשיך — ${g('פתח', 'פתחי')} גישה מלאה או ${g('ממש', 'ממשי')} קוד קופון.`
    : hasFull || unlimited ? 'אפשר לכתוב, לחזור ולפתוח תהליכים חדשים — בלי הגבלה.'
    : 'כל הודעה שלך וכל כרטיס שממולא נספרים. כך זה נראה אצלך:';

  return (
    <div className="fixed inset-0 z-[75] bg-[#f6f4f0] overflow-y-auto" dir="rtl" style={HEEBO}>
      {/* the header colour flows into a soft band with the headline and the usage meter */}
      <div className="bg-gradient-to-b from-[#2d4658] to-[#3a4f7a] text-white pb-16">
        <header className="max-w-xl mx-auto px-4 h-[64px] flex items-center">
          <h1 className="text-base font-medium flex-1 opacity-90">המנוי שלי</h1>
          <button type="button" onClick={() => onClose(!outOfMessages)} className="p-2 rounded-lg hover:bg-white/10" aria-label="סגירה">
            <X size={20} />
          </button>
        </header>
        <div className="max-w-xl mx-auto px-5 pt-2 space-y-4">
          <div>
            <h2 className="text-[30px] leading-tight" style={{ fontFamily: "'Karantina', 'Heebo', sans-serif" }}>{heroTitle}</h2>
            <p className="text-sm mt-1 opacity-85 leading-relaxed">{heroText}</p>
          </div>
          {overview && !unlimited && (
            <div className="rounded-2xl bg-white/10 px-4 py-3">
              <div className="flex items-baseline justify-between text-sm">
                <span><span className="text-2xl font-semibold">{used}</span><span className="opacity-75"> / {limit} הודעות</span></span>
                <span className={outOfMessages ? 'text-amber-300 font-medium' : 'opacity-80'}>{outOfMessages ? 'לא נשארו הודעות' : `נשארו ${left}`}</span>
              </div>
              <div className="mt-2 h-2 rounded-full bg-white/20 overflow-hidden" role="progressbar" aria-valuenow={used} aria-valuemin={0} aria-valuemax={limit}>
                <div className="h-full rounded-full" style={{ width: `${pct}%`, background: pct >= 90 ? '#fbbf24' : '#03ffe6' }} />
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="max-w-xl mx-auto px-4 -mt-10 space-y-4 pb-16">
        {!overview ? (
          <div className="bg-white rounded-3xl p-10 text-center text-sm shadow-md" style={{ color: MUTED }}>
            {loadFailed
              ? <button type="button" onClick={() => void load()} className="underline">הטעינה נכשלה — לנסות שוב</button>
              : <Loader2 className="inline animate-spin" size={22} />}
          </div>
        ) : (
          <>
            {!hasFull && full && (
              <section className="rounded-3xl p-[2px] shadow-lg" style={{ background: `linear-gradient(135deg, ${PURPLE}, #03ffe6)` }}>
                <div className="rounded-[22px] bg-white p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="flex items-center gap-1.5 text-xs font-semibold" style={{ color: PURPLE }}>
                        <Sparkles size={14} /> המומלץ
                      </p>
                      <h3 className="text-2xl font-semibold mt-1" style={{ color: INK }}>{full.name_he}</h3>
                    </div>
                    <div className="text-left shrink-0">
                      <p className="text-[34px] leading-none font-semibold" style={{ color: INK }}>{full.price}<span className="text-xl"> ₪</span></p>
                      <p className="text-xs mt-1.5 font-medium px-2 py-0.5 rounded-full inline-block" style={{ background: 'rgba(3,255,230,0.2)', color: INK }}>
                        תשלום חד פעמי
                      </p>
                    </div>
                  </div>

                  <ul className="mt-5 space-y-3">
                    {[
                      { icon: InfinityIcon, title: 'הודעות ללא הגבלה', text: 'תהליכים שלמים, בלי לעצור באמצע' },
                      { icon: RotateCcw, title: 'תהליכים חדשים בכל זמן', text: 'לחזור, להעמיק, לעבוד על אירוע נוסף' },
                      { icon: Check, title: 'בלי מנוי חודשי', text: 'משלמים פעם אחת — בלי חיוב חוזר' },
                    ].map(({ icon: Icon, title, text }) => (
                      <li key={title} className="flex gap-3">
                        <span className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0" style={{ background: 'rgba(151,71,255,0.10)' }}>
                          <Icon size={18} style={{ color: PURPLE }} />
                        </span>
                        <span>
                          <span className="block text-sm font-semibold" style={{ color: INK }}>{title}</span>
                          <span className="block text-xs" style={{ color: MUTED }}>{text}</span>
                        </span>
                      </li>
                    ))}
                  </ul>

                  <button type="button" onClick={() => setCheckoutPlan(full)}
                    className="mt-6 w-full h-[54px] rounded-2xl text-white text-base font-semibold transition-transform active:scale-[0.98] shadow-[0_10px_20px_-8px_rgba(151,71,255,0.6)]"
                    style={{ background: `linear-gradient(135deg, ${PURPLE} 0%, #6b2fd6 100%)` }}>
                    {g('פתח גישה מלאה', 'פתחי גישה מלאה')} · {full.price} ₪
                  </button>
                  <p className="text-[11px] text-center mt-2 flex items-center justify-center gap-1" style={{ color: MUTED }}>
                    <Lock size={11} /> תשלום מאובטח בכרטיס אשראי דרך PayMe
                  </p>
                </div>
              </section>
            )}

            {!hasFull && basic && (
              <div className="rounded-2xl px-4 py-3 border border-[#e0ddd8] bg-white/60 flex items-center justify-between">
                <p className="text-sm" style={{ color: INK }}>
                  <span className="font-semibold">{basic.name_he}</span>
                  <span style={{ color: MUTED }}> · {basic.messages_per_month} הודעות · המסלול שלך עכשיו</span>
                </p>
                <span className="text-sm font-medium" style={{ color: MUTED }}>חינם</span>
              </div>
            )}

            <section className="rounded-2xl bg-white shadow-sm">
              <button type="button" onClick={() => setCouponOpen((v) => !v)}
                className="w-full flex items-center gap-2 px-4 py-3.5 text-sm font-medium" style={{ color: INK }} aria-expanded={couponOpen}>
                <Ticket size={16} style={{ color: PURPLE }} />
                <span className="flex-1 text-right">יש לך קוד קופון?</span>
                <ChevronDown size={16} className={`transition-transform ${couponOpen ? 'rotate-180' : ''}`} style={{ color: MUTED }} />
              </button>
              {couponOpen && (
                <div className="px-4 pb-4 space-y-2">
                  <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); void redeem(); }}>
                    <input value={code} onChange={(e) => setCode(e.target.value)} placeholder="קוד הקופון" dir="ltr" autoFocus
                      className="flex-1 min-w-0 h-[46px] px-3 rounded-xl border border-[#e0ddd8] text-sm text-center tracking-widest uppercase focus:outline-none focus:border-[#9747ff]" />
                    <button type="submit" disabled={couponBusy || !code.trim()}
                      className="h-[46px] px-5 rounded-xl text-white text-sm font-medium disabled:opacity-40" style={{ background: INK }}>
                      {couponBusy ? '...' : 'מימוש'}
                    </button>
                  </form>
                  {couponMsg && <p className={`text-sm ${couponMsg.ok ? 'text-[#009081]' : 'text-red-600'}`}>{couponMsg.text}</p>}
                </div>
              )}
            </section>

            {reason === 'quota' && !outOfMessages && (
              <button type="button" onClick={() => onClose(true)}
                className="w-full h-[52px] rounded-2xl text-white text-base font-medium" style={{ background: INK }}>
                {g('חזור לשיחה', 'חזרי לשיחה')}
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
