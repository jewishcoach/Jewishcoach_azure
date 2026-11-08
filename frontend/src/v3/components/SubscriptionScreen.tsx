import { useCallback, useEffect, useState } from 'react';
import { X, Ticket, Loader2, Lock, Heart, Footprints, Clock, ChevronDown, ShieldCheck, PartyPopper } from 'lucide-react';
import { fetchWithAuthRetry } from '../services/api';
import { getApiBase } from '../../config';
import { PayMeCheckoutModal } from '../../components/PayMeCheckoutModal';
import { formatCouponRedeemError } from '../../lib/couponRedeemError';
import { useTranslation } from 'react-i18next';

// "המנוי שלי" (Nov 8). The paid plan is one payment that unlocks the coach without a limit — sold as "מאמן אישי,
// תמיד איתך" (the user's name for it). A marketing page: the value to the client first, the price and one button,
// then Basic and a coupon. Large type, two columns on a computer. Opened from the menu or by the limit window.

interface Plan { id: string; name_he: string; name_en: string; price: number; currency: string; messages_per_month: number }
interface Overview {
  current_plan: string;
  usage: { messages_used: number; messages_limit: number };
  available_plans: Plan[];
  has_active_coupon: boolean;
  coupon_code?: string | null;
  payme_checkout?: { merchant_public_key: string; test_mode: boolean; checkout_js_url?: string } | null;
  subscription?: { current_period_start?: string | null; created_at?: string | null } | null;
}

interface Props {
  open: boolean;
  reason?: 'menu' | 'quota';
  /** open with the coupon field unfolded ("יש לי קוד קופון" in the limit window) */
  couponFirst?: boolean;
  gender?: string | null;
  getToken: (opts?: { skipCache?: boolean }) => Promise<string | null>;
  onClose: (canContinue: boolean) => void;
}

const HEEBO = { fontFamily: "'Heebo', sans-serif" };
const INK = '#1f3444';
const SOFT = '#4a6070';
const PURPLE = '#9747ff';

export function SubscriptionScreen({ open, reason = 'menu', couponFirst = false, gender, getToken, onClose }: Props) {
  const { t } = useTranslation();
  const g = (m: string, f: string) => (gender === 'female' ? f : m);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);
  const [code, setCode] = useState('');
  const [couponOpen, setCouponOpen] = useState(couponFirst);
  const [couponBusy, setCouponBusy] = useState(false);
  const [couponMsg, setCouponMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [checkoutPlan, setCheckoutPlan] = useState<Plan | null>(null);
  // after a successful payment the PayMe window just closed — say thank you and that the coach is open now
  const [justPaid, setJustPaid] = useState(false);

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
  useEffect(() => { if (open && couponFirst) setCouponOpen(true); }, [open, couponFirst]);

  if (!open) return null;

  const used = overview?.usage.messages_used ?? 0;
  const limit = overview?.usage.messages_limit ?? 0;
  const unlimited = limit === -1;
  const left = unlimited ? Infinity : Math.max(0, limit - used);
  const pct = unlimited || !limit ? 0 : Math.min(100, Math.round((100 * used) / limit));
  const outOfMessages = !unlimited && limit > 0 && left === 0;
  const coach = overview?.available_plans.find((p) => p.id === 'premium');
  const basic = overview?.available_plans.find((p) => p.id === 'basic');
  const hasCoach = overview?.current_plan === 'premium';
  const quota = reason === 'quota' && outOfMessages;

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

  const benefits = [
    { icon: Footprints, title: 'תהליך שלם, עד הבחירה החדשה', text: 'בלי מגבלת הודעות שעוצרת אותך באמצע הדרך' },
    { icon: Clock, title: `${g('חוזר', 'חוזרת')} מתי שנוח לך`, text: 'אירוע חדש, יום קשה, הצעד הבא — המאמן כאן, בכל שעה' },
    { icon: Heart, title: 'תשלום אחד וזהו', text: 'בלי מנוי ובלי חיוב חוזר' },
  ];

  return (
    <div className="fixed inset-0 z-[75] bg-[#f6f4f0] overflow-y-auto" dir="rtl" style={HEEBO}>
      <header className="sticky top-0 z-10 bg-[#2d4658] text-white">
        <div className="max-w-5xl mx-auto px-4 md:px-8 h-[64px] flex items-center">
          <h1 className="text-lg font-medium flex-1">המנוי שלי</h1>
          <button type="button" onClick={() => onClose(!outOfMessages)} className="p-2 rounded-lg hover:bg-white/10" aria-label="סגירה">
            <X size={22} />
          </button>
        </div>
      </header>

      {!overview ? (
        <div className="max-w-md mx-auto mt-16 bg-white rounded-3xl p-10 text-center text-base shadow-md" style={{ color: SOFT }}>
          {loadFailed
            ? <button type="button" onClick={() => void load()} className="underline">הטעינה נכשלה — לנסות שוב</button>
            : <Loader2 className="inline animate-spin" size={24} />}
        </div>
      ) : hasCoach ? (
        <ActiveCoach overview={overview} justPaid={justPaid} gender={gender} benefits={benefits}
          onBack={() => onClose(true)} />
      ) : (
        <div className="max-w-5xl mx-auto px-4 md:px-8 py-8 md:py-14 grid gap-6 md:gap-x-10 md:gap-y-6 md:grid-cols-[1.1fr_1fr] md:grid-rows-[auto_1fr] md:items-start">
          {/* the pitch — headline first; on the phone the offer comes right after it, before the benefits */}
          <div className="space-y-6 order-1 md:order-none md:col-start-1 md:row-start-1">
            {quota && (
              <p className="inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-sm font-semibold"
                style={{ background: 'rgba(217,119,6,0.12)', color: '#92400e' }}>
                ההודעות שלך נגמרו — השיחה שמורה בדיוק איפה שעצרת
              </p>
            )}
            {unlimited && !hasCoach && (
              <p className="inline-flex rounded-full px-4 py-1.5 text-sm" style={{ background: 'rgba(3,255,230,0.18)', color: INK }}>
                לחשבון שלך אין מגבלת הודעות — כך המסך נראה למשתמשים
              </p>
            )}
            <div>
              <h2 className="text-[34px] md:text-[46px] leading-[1.15] font-bold" style={{ color: INK }}>
                מאמן אישי,<br /><span style={{ color: PURPLE }}>תמיד איתך</span>
              </h2>
              <p className="mt-4 text-lg md:text-xl leading-relaxed" style={{ color: SOFT }}>
                בני ממשיך ללוות אותך בכל תהליך — מהרגע שקרה ועד הבחירה החדשה שלך. בלי לעצור באמצע, בלי לחכות לפגישה.
              </p>
            </div>
          </div>

          <ul className="space-y-4 order-3 md:order-none md:col-start-1 md:row-start-2">
              {benefits.map(({ icon: Icon, title, text }) => (
                <li key={title} className="flex gap-4 items-start">
                  <span className="w-11 h-11 rounded-2xl flex items-center justify-center shrink-0" style={{ background: 'rgba(151,71,255,0.12)' }}>
                    <Icon size={22} style={{ color: PURPLE }} />
                  </span>
                  <span>
                    <span className="block text-lg font-semibold" style={{ color: INK }}>{title}</span>
                    <span className="block text-base" style={{ color: SOFT }}>{text}</span>
                  </span>
                </li>
              ))}
          </ul>

          {/* the offer */}
          <div className="space-y-4 order-2 md:order-none md:col-start-2 md:row-start-1 md:row-span-2">
            {hasCoach ? (
              <section className="rounded-3xl bg-white p-6 shadow-lg text-center space-y-2">
                <ShieldCheck size={34} className="mx-auto" style={{ color: '#009081' }} />
                <h3 className="text-2xl font-bold" style={{ color: INK }}>המאמן האישי שלך פעיל</h3>
                <p className="text-base" style={{ color: SOFT }}>אפשר לכתוב, לחזור ולפתוח תהליכים חדשים — בלי הגבלה.</p>
              </section>
            ) : coach && (
              <section className="rounded-3xl p-[2px] shadow-xl" style={{ background: `linear-gradient(135deg, ${PURPLE}, #03ffe6)` }}>
                <div className="rounded-[22px] bg-white p-6 md:p-7">
                  <p className="text-base font-semibold" style={{ color: PURPLE }}>{coach.name_he}</p>
                  <p className="mt-2 flex items-baseline gap-2" style={{ color: INK }}>
                    <span className="text-[52px] leading-none font-bold">{coach.price} ₪</span>
                  </p>
                  <p className="mt-1 text-base font-medium" style={{ color: SOFT }}>תשלום חד פעמי · בלי מנוי</p>
                  <button type="button" onClick={() => setCheckoutPlan(coach)}
                    className="mt-6 w-full h-[58px] rounded-2xl text-white text-lg font-bold transition-transform active:scale-[0.98] shadow-[0_12px_24px_-10px_rgba(151,71,255,0.7)]"
                    style={{ background: `linear-gradient(135deg, ${PURPLE} 0%, #6b2fd6 100%)` }}>
                    {quota ? 'להמשיך עם המאמן שלי' : 'אני רוצה מאמן אישי'}
                  </button>
                  <p className="mt-3 text-sm flex items-center justify-center gap-1.5" style={{ color: SOFT }}>
                    <Lock size={14} /> תשלום מאובטח בכרטיס אשראי דרך PayMe
                  </p>
                  <p className="mt-1 text-sm flex items-center justify-center gap-1.5" style={{ color: SOFT }}>
                    <ShieldCheck size={14} /> השיחות שלך נשארות פרטיות
                  </p>
                </div>
              </section>
            )}

            {!hasCoach && basic && !unlimited && (
              <div className="rounded-2xl bg-white px-5 py-4 shadow-sm">
                <div className="flex items-baseline justify-between">
                  <p className="text-base font-semibold" style={{ color: INK }}>המסלול החינמי שלך</p>
                  <p className="text-base" style={{ color: outOfMessages ? '#b45309' : SOFT }}>
                    {outOfMessages ? 'לא נשארו הודעות' : `נשארו ${left} מתוך ${limit}`}
                  </p>
                </div>
                <div className="mt-3 h-2.5 rounded-full bg-[#ece8e2] overflow-hidden" role="progressbar" aria-valuenow={used} aria-valuemin={0} aria-valuemax={limit}>
                  <div className="h-full rounded-full" style={{ width: `${pct}%`, background: pct >= 90 ? '#d97706' : PURPLE }} />
                </div>
                <p className="mt-2 text-sm" style={{ color: SOFT }}>כל הודעה שלך וכל כרטיס שממולא נספרים</p>
              </div>
            )}

            <section className="rounded-2xl bg-white shadow-sm">
              <button type="button" onClick={() => setCouponOpen((v) => !v)}
                className="w-full flex items-center gap-2 px-5 py-4 text-base font-medium" style={{ color: INK }} aria-expanded={couponOpen}>
                <Ticket size={18} style={{ color: PURPLE }} />
                <span className="flex-1 text-right">יש לך קוד קופון?</span>
                <ChevronDown size={18} className={`transition-transform ${couponOpen ? 'rotate-180' : ''}`} style={{ color: SOFT }} />
              </button>
              {couponOpen && (
                <div className="px-5 pb-5 space-y-2">
                  <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); void redeem(); }}>
                    <input value={code} onChange={(e) => setCode(e.target.value)} placeholder="קוד הקופון" dir="ltr" autoFocus
                      className="flex-1 min-w-0 h-[50px] px-3 rounded-xl border border-[#d8d3cc] text-base text-center tracking-widest uppercase focus:outline-none focus:border-[#9747ff]" />
                    <button type="submit" disabled={couponBusy || !code.trim()}
                      className="h-[50px] px-6 rounded-xl text-white text-base font-semibold disabled:opacity-40" style={{ background: '#2d4658' }}>
                      {couponBusy ? '...' : 'מימוש'}
                    </button>
                  </form>
                  {couponMsg && <p className={`text-base ${couponMsg.ok ? 'text-[#009081]' : 'text-red-600'}`}>{couponMsg.text}</p>}
                </div>
              )}
            </section>

            {reason === 'quota' && !outOfMessages && (
              <button type="button" onClick={() => onClose(true)}
                className="w-full h-[54px] rounded-2xl text-white text-lg font-semibold" style={{ background: '#2d4658' }}>
                {g('חזור לשיחה', 'חזרי לשיחה')}
              </button>
            )}
          </div>
        </div>
      )}

      {checkoutPlan && (
        <PayMeCheckoutModal
          open
          plan={checkoutPlan}
          payMeCheckoutFromOverview={overview?.payme_checkout ?? null}
          getToken={getToken}
          onClose={() => setCheckoutPlan(null)}
          onCompleted={() => { setCheckoutPlan(null); setJustPaid(true); void load(); }}
        />
      )}
    </div>
  );
}

// The paid plan is on: the thank-you right after paying, or a calm "active since" for whoever opens the screen later.
function ActiveCoach({ overview, justPaid, benefits, onBack }: {
  overview: Overview;
  justPaid: boolean;
  gender?: string | null;
  benefits: { icon: typeof Heart; title: string; text: string }[];
  onBack: () => void;
}) {
  const since = overview.subscription?.current_period_start || overview.subscription?.created_at;
  const sinceText = since ? new Date(since.endsWith('Z') || since.includes('+') ? since : `${since}Z`).toLocaleDateString('he-IL') : null;
  const limit = overview.usage.messages_limit;
  return (
    <div className="max-w-xl mx-auto px-4 py-10 md:py-16 text-center space-y-6">
      <div className="mx-auto w-20 h-20 rounded-3xl flex items-center justify-center"
        style={{ background: justPaid ? 'linear-gradient(135deg, #9747ff, #03ffe6)' : 'rgba(0,144,129,0.12)' }}>
        {justPaid ? <PartyPopper size={38} className="text-white" /> : <ShieldCheck size={38} style={{ color: '#009081' }} />}
      </div>
      <div>
        <h2 className="text-[30px] md:text-[40px] leading-tight font-bold" style={{ color: INK }}>
          {justPaid ? 'תודה! המאמן האישי שלך פעיל' : 'המאמן האישי שלך פעיל'}
        </h2>
        <p className="mt-3 text-lg leading-relaxed" style={{ color: SOFT }}>
          {justPaid
            ? `מעכשיו אפשר לכתוב, לחזור ולפתוח תהליכים חדשים — בלי הגבלה. השיחה שלך מחכה בדיוק איפה שעצרת.`
            : `${overview.has_active_coupon ? `דרך קופון ${overview.coupon_code ?? ''}`.trim() : 'מאמן אישי, תמיד איתך'}${sinceText ? ` · פעיל מאז ${sinceText}` : ''}`}
        </p>
      </div>
      <ul className="space-y-4 text-right rounded-3xl bg-white p-6 shadow-sm">
        {benefits.map(({ icon: Icon, title, text }) => (
          <li key={title} className="flex gap-4 items-start">
            <span className="w-11 h-11 rounded-2xl flex items-center justify-center shrink-0" style={{ background: 'rgba(151,71,255,0.12)' }}>
              <Icon size={22} style={{ color: PURPLE }} />
            </span>
            <span>
              <span className="block text-lg font-semibold" style={{ color: INK }}>{title}</span>
              <span className="block text-base" style={{ color: SOFT }}>{text}</span>
            </span>
          </li>
        ))}
      </ul>
      {limit !== -1 && (
        <p className="text-base" style={{ color: SOFT }}>{`נשארו ${Math.max(0, limit - overview.usage.messages_used)} מתוך ${limit} הודעות בקופון`}</p>
      )}
      <button type="button" onClick={onBack}
        className="w-full h-[56px] rounded-2xl text-white text-lg font-semibold" style={{ background: `linear-gradient(135deg, ${PURPLE} 0%, #6b2fd6 100%)` }}>
        חזרה לשיחה
      </button>
    </div>
  );
}
