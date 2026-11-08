import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { X, RefreshCw, AlertTriangle, CheckCircle2, Lock } from 'lucide-react';
import { fetchJourney, DashboardAccessError } from '../services/api';
import type { JourneyData, JourneyWhere } from '../services/api';

// "ניהול" (Nov 5): where users are in the process and where they stop — numbers only, never the conversation
// text (privacy policy). Admin account + its own password (App Service ADMIN_DASHBOARD_PASSWORD), kept for the
// browser tab only.

const STEP_NAMES: Record<string, string> = {
  S0: 'הודעה ראשונה', S1: 'פתיחה', S2: 'אירוע', S3: 'רגש', S4: 'מחשבה', S5: 'מעשה', S6: 'רצוי', S7: 'פער', S8: 'דפוס',
  S9: 'פרדיגמה', S10: 'עמדה', S11: 'מאזן', S12: 'כמ"ז', S13: 'בחירה', S14: 'תמונת עתיד', S15: 'בקשה לאימון',
};
const CARD_NAMES: Record<string, string> = {
  event_form: 'אירוע', emotion_selector: 'רגשות', action_field: 'מעשה', matzui_summary: 'סיכום המצוי',
  comparison_card: 'רצוי', gap_card: 'פער', sentence_builder: 'פרדיגמה', balance_scale: 'מאזן',
  kamaz_discovery: 'הבזקי מקור וטבע', trait_card_builder: 'כרטיס כמ"ז', declaration_card: 'בחירה', commitment_card: 'בקשה לאימון',
};
const PW_KEY = 'jc_admin_dashboard_pw';
const HEEBO = { fontFamily: "'Heebo', sans-serif" };
const INK = '#2d4658';
const MUTED = 'rgba(45,70,88,0.6)';
const BAR = '#9747ff';
const WARN = '#b45309';

const stepLabel = (s: string) => `${STEP_NAMES[s] ?? s} (${s})`;
function whereLabel(w: JourneyWhere | undefined | null): string {
  if (!w) return '—';
  if (w.kind === 'completed') return 'סיים ✓';
  if (w.kind === 'stage_intro') return `שאלות פתיחה לשלב (${stepLabel(w.step)})`;
  if (w.kind === 'card') return `מחכה לכרטיס ${CARD_NAMES[w.card ?? ''] ?? w.card}`;
  return `בשיחה — ${stepLabel(w.step)}`;
}
function ago(iso: string | null | undefined): string {
  if (!iso) return '—';
  const min = Math.round((Date.now() - new Date(iso.endsWith('Z') ? iso : `${iso}Z`).getTime()) / 60000);
  if (min < 60) return `לפני ${Math.max(min, 0)} דק'`;
  if (min < 48 * 60) return `לפני ${Math.round(min / 60)} שע'`;
  return `לפני ${Math.round(min / 1440)} ימים`;
}

interface Props {
  open: boolean;
  onClose: () => void;
  getToken: (opts?: { skipCache?: boolean }) => Promise<string | null>;
}

export function AdminDashboard({ open, onClose, getToken }: Props) {
  const [password, setPassword] = useState(() => sessionStorage.getItem(PW_KEY) || '');
  const [typed, setTyped] = useState('');
  const [days, setDays] = useState(30);
  const [data, setData] = useState<JourneyData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async (pw: string, d: number) => {
    setLoading(true);
    setError(null);
    try {
      const j = await fetchJourney(getToken, pw, d);
      sessionStorage.setItem(PW_KEY, pw);
      setPassword(pw);
      setData(j);
    } catch (e) {
      if (e instanceof DashboardAccessError) {
        sessionStorage.removeItem(PW_KEY);
        setPassword('');
        setData(null);
        setError(e.code === 'wrong_password' ? 'הסיסמה שגויה' : e.code === 'not_set' ? 'עוד לא הוגדרה סיסמה לדשבורד בשרת' : 'אין הרשאת מנהל');
      } else {
        setError('הטעינה נכשלה. אפשר לנסות שוב.');
      }
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    if (open && password && !data) void load(password, days);
  }, [open, password, data, days, load]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[80] bg-[#f6f4f0] overflow-y-auto" dir="rtl" style={HEEBO}>
      <header className="sticky top-0 z-10 bg-[#2d4658] text-white px-4 py-3 flex items-center gap-3">
        <h1 className="text-lg font-semibold flex-1">ניהול — מסע המשתמשים</h1>
        {password && (
          <>
            <select value={days} onChange={(e) => { const d = Number(e.target.value); setDays(d); void load(password, d); }}
              className="bg-white/10 rounded-lg px-2 py-1 text-sm" aria-label="תקופה">
              <option value={7} className="text-black">7 ימים</option>
              <option value={30} className="text-black">30 ימים</option>
              <option value={90} className="text-black">90 ימים</option>
              <option value={0} className="text-black">הכול</option>
            </select>
            <button type="button" onClick={() => load(password, days)} className="p-2 rounded-lg hover:bg-white/10" aria-label="רענון" title="רענון">
              <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
            </button>
          </>
        )}
        <button type="button" onClick={onClose} className="p-2 rounded-lg hover:bg-white/10" aria-label="סגירה"><X size={20} /></button>
      </header>

      {!password ? (
        <form className="max-w-sm mx-auto mt-16 bg-white rounded-2xl p-6 space-y-4 shadow-sm"
          onSubmit={(e) => { e.preventDefault(); if (typed.trim()) void load(typed.trim(), days); }}>
          <div className="flex items-center gap-2 text-[#2d4658]"><Lock size={18} /><h2 className="font-semibold">סיסמת הדשבורד</h2></div>
          <input type="password" value={typed} onChange={(e) => setTyped(e.target.value)} autoFocus autoComplete="current-password"
            className="w-full h-[44px] px-3 rounded-xl border border-[#e0ddd8] text-sm text-right focus:outline-none focus:border-[#9747ff]" />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button type="submit" disabled={loading} className="w-full h-[44px] rounded-xl bg-[#9747ff] text-white text-sm font-medium disabled:opacity-60">
            {loading ? '...' : 'כניסה'}
          </button>
        </form>
      ) : !data ? (
        <p className="text-center mt-16 text-sm" style={{ color: MUTED }}>{error ?? 'טוען...'}</p>
      ) : (
        <Body data={data} />
      )}
    </div>
  );
}

function Tile({ label, value, note }: { label: string; value: string | number; note?: string }) {
  return (
    <div className="bg-white rounded-xl p-3 shadow-sm">
      <p className="text-xs" style={{ color: MUTED }}>{label}</p>
      <p className="text-2xl font-semibold mt-1" style={{ color: INK }}>{value}</p>
      {note && <p className="text-[11px] mt-0.5" style={{ color: MUTED }}>{note}</p>}
    </div>
  );
}

function Section({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <section className="bg-white rounded-2xl p-4 shadow-sm space-y-3">
      <div>
        <h2 className="text-base font-semibold" style={{ color: INK }}>{title}</h2>
        {hint && <p className="text-xs mt-0.5" style={{ color: MUTED }}>{hint}</p>}
      </div>
      {children}
    </section>
  );
}

const TH = 'px-2 py-2 text-right text-[11px] font-semibold whitespace-nowrap';
const TD = 'px-2 py-2 text-right text-xs whitespace-nowrap';

function Body({ data }: { data: JourneyData }) {
  const o = data.overview;
  const maxReached = Math.max(1, ...data.steps.map((s) => s.reached));
  return (
    <div className="max-w-6xl mx-auto p-4 space-y-4 pb-16">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Tile label="משתמשים" value={o.users_total} note={`${o.users_new} חדשים בתקופה`} />
        <Tile label="פעילים" value={o.active_24h} note={`ב-24 שעות · ${o.active_7d} ב-7 ימים`} />
        <Tile label="שיחות שהתחילו" value={o.conversations} note={o.couple_conversations ? `${o.couple_conversations} זוגיות` : undefined} />
        <Tile label="סיימו תהליך" value={o.completed} note={o.completion_rate != null ? `${o.completion_rate}% מהשיחות` : undefined} />
        <Tile label="נעצרו באמצע" value={o.stalled} note={`בלי פעילות ${data.thresholds.stall_hours} שעות`} />
        <Tile label="תורות עד סיום (חציון)" value={o.median_turns_to_complete ?? '—'} />
      </div>

      <Section title="כמה הגיעו לכל שלב" hint="כל פס = מספר השיחות שהגיעו לשלב לפחות. ⚠ = כמה נעצרו בשלב הזה (בלי פעילות יממה).">
        <div className="space-y-1.5">
          {data.steps.map((s) => (
            <div key={s.step} className="flex items-center gap-2" title={`${stepLabel(s.step)}: הגיעו ${s.reached}, נמצאים עכשיו ${s.here_now}, נעצרו ${s.stalled_here}`}>
              <span className="w-28 shrink-0 text-xs" style={{ color: INK }}>{stepLabel(s.step)}</span>
              <div className="flex-1 h-5 bg-[#f1eee9] rounded">
                <div className="h-5 rounded" style={{ width: `${(100 * s.reached) / maxReached}%`, background: BAR, minWidth: s.reached ? 4 : 0 }} />
              </div>
              <span className="w-10 shrink-0 text-xs font-semibold text-left" style={{ color: INK }}>{s.reached}</span>
              <span className="w-14 shrink-0 text-[11px]" style={{ color: s.stalled_here ? WARN : MUTED }}>
                {s.stalled_here ? <><AlertTriangle size={11} className="inline -mt-0.5" /> {s.stalled_here} נעצרו</> : ''}
              </span>
            </div>
          ))}
        </div>
      </Section>

      <Section title="איפה נתקעים" hint={`לולאה = ${data.thresholds.loop_turns} תורות או יותר בשלב אחד. זמן תגובה = כמה שניות לקח למאמן לענות.`}>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead><tr className="border-b border-[#e0ddd8]" style={{ color: MUTED }}>
              <th className={TH}>שלב</th><th className={TH}>נמצאים עכשיו</th><th className={TH}>נעצרו</th>
              <th className={TH}>תורות (ממוצע)</th><th className={TH}>תורות (90%)</th><th className={TH}>לולאות</th>
              <th className={TH}>דקות בשלב (חציון)</th><th className={TH}>זמן תגובה (חציון / 90%)</th>
            </tr></thead>
            <tbody>
              {data.steps.map((s) => (
                <tr key={s.step} className="border-b border-[#f1eee9]" style={{ color: INK }}>
                  <td className={TD}>{stepLabel(s.step)}</td>
                  <td className={TD}>{s.here_now || '—'}</td>
                  <td className={TD} style={s.stalled_here ? { color: WARN, fontWeight: 600 } : undefined}>{s.stalled_here || '—'}</td>
                  <td className={TD}>{s.avg_turns ?? '—'}</td>
                  <td className={TD}>{s.p90_turns ?? '—'}</td>
                  <td className={TD} style={s.loops ? { color: WARN, fontWeight: 600 } : undefined}>{s.loops ? `⚠ ${s.loops}` : '—'}</td>
                  <td className={TD}>{s.median_minutes ?? '—'}</td>
                  <td className={TD}>{s.latency_p50 != null ? `${s.latency_p50} / ${s.latency_p90} שנ'` : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section title="משתמשים" hint="ממוין לפי פעילות אחרונה. 'איפה עכשיו' = השיחה האחרונה שלו.">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead><tr className="border-b border-[#e0ddd8]" style={{ color: MUTED }}>
              <th className={TH}>משתמש</th><th className={TH}>מנוי</th><th className={TH}>שיחות</th><th className={TH}>הודעות</th>
              <th className={TH}>איפה עכשיו</th><th className={TH}>פעילות אחרונה</th><th className={TH}>נרשם</th>
            </tr></thead>
            <tbody>
              {data.users.map((u) => (
                <tr key={u.id} className="border-b border-[#f1eee9]" style={{ color: INK }}>
                  <td className={TD}>{u.name || u.email || `#${u.id}`}{u.name && u.email ? <span style={{ color: MUTED }}> · {u.email}</span> : null}</td>
                  <td className={TD}>{u.plan}</td>
                  <td className={TD}>{u.conversations}</td>
                  <td className={TD}>{u.messages_used}{u.messages_limit === -1 ? '' : ` / ${u.messages_limit}`}</td>
                  <td className={TD}>
                    {u.latest?.status === 'stalled' && <AlertTriangle size={11} className="inline -mt-0.5 ml-1" style={{ color: WARN }} />}
                    {u.latest?.status === 'completed' && <CheckCircle2 size={11} className="inline -mt-0.5 ml-1 text-[#009081]" />}
                    {u.latest ? whereLabel(u.latest.where) : '—'}
                  </td>
                  <td className={TD}>{ago(u.last_active)}</td>
                  <td className={TD}>{u.created_at ? new Date(`${u.created_at}Z`).toLocaleDateString('he-IL') : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section title="שיחות אחרונות" hint="'הכי הרבה תורות' מראה באיזה שלב השיחה בילתה הכי הרבה תורות — סימן לתקיעה.">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead><tr className="border-b border-[#e0ddd8]" style={{ color: MUTED }}>
              <th className={TH}>שיחה</th><th className={TH}>משתמש</th><th className={TH}>מצב</th><th className={TH}>איפה</th>
              <th className={TH}>תורות</th><th className={TH}>הכי הרבה תורות</th><th className={TH}>פעילות אחרונה</th>
            </tr></thead>
            <tbody>
              {data.conversations.map((c) => {
                const u = data.users.find((x) => x.id === c.user_id);
                return (
                  <tr key={c.id} className="border-b border-[#f1eee9]" style={{ color: INK }}>
                    <td className={TD}>#{c.id}{c.couple ? ' ♥' : ''}</td>
                    <td className={TD}>{u?.name || u?.email || `#${c.user_id}`}</td>
                    <td className={TD} style={c.status === 'stalled' ? { color: WARN, fontWeight: 600 } : undefined}>
                      {c.status === 'completed' ? 'סיים ✓' : c.status === 'stalled' ? '⚠ נעצר' : 'פעיל'}
                    </td>
                    <td className={TD}>{whereLabel(c.where)}</td>
                    <td className={TD}>{c.user_turns}</td>
                    <td className={TD} style={c.most_turns >= data.thresholds.loop_turns ? { color: WARN, fontWeight: 600 } : undefined}>
                      {c.most_turns ? `${stepLabel(c.most_turns_step)} · ${c.most_turns}` : '—'}
                    </td>
                    <td className={TD}>{ago(c.last_active)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Section>

      <p className="text-[11px] text-center" style={{ color: MUTED }}>
        מספרים בלבד — בלי תוכן השיחות. נוצר {new Date(`${data.generated_at}Z`).toLocaleString('he-IL')}.
      </p>
    </div>
  );
}
