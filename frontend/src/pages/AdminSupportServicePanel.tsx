import React, { useCallback, useEffect, useState } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { apiClient } from '../services/api';
import { getApiBase } from '../config';

interface SupportSettings {
  personality_text: string;
  terms_and_boundaries_text: string;
  methodology_context_text: string;
  auto_reply_enabled: boolean;
  updated_at: string | null;
  /** מה שהשרת באמת משתמש בו אחרי SUPPORT_AUTO_REPLY_ENABLED */
  auto_reply_effective?: boolean;
  support_auto_reply_env?: string | null;
  /** בשרת: האם מוגדר EMAIL_CONNECTION_STRING או SENDGRID_API_KEY */
  transactional_email_configured?: boolean;
  transactional_email_via?: 'acs' | 'sendgrid' | 'none';
}

interface SupportLogRow {
  id: number;
  user_id: number | null;
  user_display_name: string | null;
  customer_email: string;
  direction: string;
  channel: string;
  subject: string | null;
  body: string;
  meta: Record<string, unknown>;
  created_at: string | null;
}

/** SQLite/JSON sometimes stores send_ok as 0/1 instead of boolean */
function coerceOutboundSendOk(meta: Record<string, unknown> | undefined): boolean | undefined {
  if (!meta || !('send_ok' in meta)) return undefined;
  const v = meta.send_ok;
  if (v === true || v === 1 || v === '1' || v === 'true') return true;
  if (v === false || v === 0 || v === '0' || v === 'false') return false;
  return undefined;
}

export const AdminSupportServicePanel: React.FC = () => {
  const { getToken } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [settings, setSettings] = useState<SupportSettings>({
    personality_text: '',
    terms_and_boundaries_text: '',
    methodology_context_text: '',
    auto_reply_enabled: false,
    updated_at: null,
  });
  const [settingsBusy, setSettingsBusy] = useState(false);

  const [filterEmail, setFilterEmail] = useState('');
  const [filterUserId, setFilterUserId] = useState('');
  const [filterDirection, setFilterDirection] = useState<'all' | 'inbound' | 'outbound' | 'draft'>('all');
  const [logs, setLogs] = useState<SupportLogRow[]>([]);
  const [logsTotal, setLogsTotal] = useState(0);
  const [logsBusy, setLogsBusy] = useState(false);

  const [custEmail, setCustEmail] = useState('');
  const [incoming, setIncoming] = useState('');
  const [lang, setLang] = useState('he');
  const [recordInbound, setRecordInbound] = useState(true);
  const [recordDraft, setRecordDraft] = useState(true);
  const [draftBusy, setDraftBusy] = useState(false);
  const [draftSubject, setDraftSubject] = useState('');
  const [draftBody, setDraftBody] = useState('');
  const [draftNotes, setDraftNotes] = useState('');
  const [snapshotJson, setSnapshotJson] = useState('');

  const [outSubject, setOutSubject] = useState('');
  const [outBody, setOutBody] = useState('');
  const [outBusy, setOutBusy] = useState(false);

  const authFetch = useCallback(async () => {
    const token = await getToken();
    if (token) apiClient.setToken(token);
  }, [getToken]);

  const reloadLogs = useCallback(async () => {
    setLogsBusy(true);
    setError(null);
    try {
      await authFetch();
      const uid = filterUserId.trim() ? parseInt(filterUserId.trim(), 10) : undefined;
      const params: {
        user_id?: number;
        customer_email?: string;
        direction?: string;
        limit?: number;
      } = { limit: 150 };
      if (uid !== undefined && Number.isFinite(uid)) params.user_id = uid;
      const em = filterEmail.trim();
      if (em) params.customer_email = em;
      if (filterDirection !== 'all') params.direction = filterDirection;

      const data = (await apiClient.listSupportServiceLogs(params)) as {
        total: number;
        logs: SupportLogRow[];
      };
      setLogsTotal(data.total);
      setLogs(data.logs || []);
    } catch (e: unknown) {
      console.error(e);
      setError(e instanceof Error ? e.message : 'Failed to load support logs');
      setLogs([]);
    } finally {
      setLogsBusy(false);
    }
  }, [authFetch, filterEmail, filterUserId, filterDirection]);

  /** טעינת תיעוד אוטומטית אחרי טעינת ההגדרות. לשינוי סינון — לחץ «רענן תיעוד». */
  useEffect(() => {
    if (!loading) {
      void reloadLogs();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- לא לגשת ל-API על כל תו בשדה הסינון
  }, [loading]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        await authFetch();
        const raw = (await apiClient.getSupportServiceSettings()) as Partial<SupportSettings>;
        if (!cancelled) {
          const viaOk =
            raw.transactional_email_via === 'acs' ||
            raw.transactional_email_via === 'sendgrid' ||
            raw.transactional_email_via === 'none';
          const hasEmailStatus =
            typeof raw.transactional_email_configured === 'boolean' && viaOk;

          setSettings({
            personality_text: raw.personality_text ?? '',
            terms_and_boundaries_text: raw.terms_and_boundaries_text ?? '',
            methodology_context_text: raw.methodology_context_text ?? '',
            auto_reply_enabled: Boolean(raw.auto_reply_enabled),
            updated_at: raw.updated_at ?? null,
            auto_reply_effective:
              typeof raw.auto_reply_effective === 'boolean' ? raw.auto_reply_effective : undefined,
            support_auto_reply_env:
              typeof raw.support_auto_reply_env === 'string'
                ? raw.support_auto_reply_env
                : raw.support_auto_reply_env === null
                  ? null
                  : undefined,
            transactional_email_configured: hasEmailStatus
              ? raw.transactional_email_configured
              : undefined,
            transactional_email_via: hasEmailStatus ? raw.transactional_email_via : undefined,
          });
        }
      } catch (e: unknown) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load settings');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [authFetch]);

  const saveSettings = async () => {
    setSettingsBusy(true);
    setError(null);
    try {
      await authFetch();
      const s = (await apiClient.patchSupportServiceSettings({
        personality_text: settings.personality_text,
        terms_and_boundaries_text: settings.terms_and_boundaries_text,
        methodology_context_text: settings.methodology_context_text,
        auto_reply_enabled: settings.auto_reply_enabled,
      })) as Partial<SupportSettings>;
      setSettings((prev) => ({
        ...prev,
        personality_text: s.personality_text ?? prev.personality_text,
        terms_and_boundaries_text: s.terms_and_boundaries_text ?? prev.terms_and_boundaries_text,
        methodology_context_text: s.methodology_context_text ?? prev.methodology_context_text,
        auto_reply_enabled:
          typeof s.auto_reply_enabled === 'boolean' ? s.auto_reply_enabled : prev.auto_reply_enabled,
        updated_at: s.updated_at ?? prev.updated_at,
        auto_reply_effective:
          typeof s.auto_reply_effective === 'boolean' ? s.auto_reply_effective : prev.auto_reply_effective,
        support_auto_reply_env:
          typeof s.support_auto_reply_env === 'string'
            ? s.support_auto_reply_env
            : s.support_auto_reply_env === null
              ? null
              : prev.support_auto_reply_env,
        transactional_email_configured:
          typeof s.transactional_email_configured === 'boolean'
            ? s.transactional_email_configured
            : prev.transactional_email_configured,
        transactional_email_via: s.transactional_email_via ?? prev.transactional_email_via,
      }));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Save failed');
    } finally {
      setSettingsBusy(false);
    }
  };

  const runDraft = async () => {
    setDraftBusy(true);
    setError(null);
    setDraftSubject('');
    setDraftBody('');
    setDraftNotes('');
    setSnapshotJson('');
    try {
      await authFetch();
      const res = (await apiClient.supportServiceDraftReply({
        customer_email: custEmail.trim(),
        incoming_message: incoming,
        language: lang,
        record_inbound: recordInbound,
        record_draft: recordDraft,
      })) as {
        customer_snapshot: unknown;
        draft: { subject?: string; body_plain?: string; internal_notes?: string | null };
      };
      setSnapshotJson(JSON.stringify(res.customer_snapshot, null, 2));
      const d = res.draft || {};
      setDraftSubject((d.subject || '').trim());
      setDraftBody((d.body_plain || '').trim());
      setDraftNotes((d.internal_notes || '').trim());
      await reloadLogs();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Draft failed');
    } finally {
      setDraftBusy(false);
    }
  };

  const logOutboundSent = async () => {
    if (!custEmail.trim()) {
      setError('נא למלא מייל לקוח לפני תיעוד תשובה יוצאת.');
      return;
    }
    setOutBusy(true);
    setError(null);
    try {
      await authFetch();
      await apiClient.supportServiceLogOutbound({
        customer_email: custEmail.trim(),
        subject: outSubject.trim() || null,
        body: outBody.trim(),
      });
      setOutSubject('');
      setOutBody('');
      await reloadLogs();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Log outbound failed');
    } finally {
      setOutBusy(false);
    }
  };

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-slate-600">
        טוען הגדרות תמיכה…
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">שירות לקוחות (support@)</h2>
        <p className="mt-1 text-sm text-slate-600">
          הגדרות טון ומדיניות, טיוטת תשובה עם הקשר מערכת (מנוי / שימוש / שיחות), ותיעוד מלא של פניות ותשובות לפי
          משתמש או מייל.
        </p>
        {error && (
          <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</div>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm space-y-4">
          <h3 className="font-semibold text-slate-900">הגדרות אישיות ומדיניות</h3>
          <label className="block text-sm text-slate-700">
            אישיות וטון (שירות לקוחות)
            <textarea
              className="mt-1 w-full min-h-[88px] rounded-lg border border-slate-300 px-3 py-2 text-sm font-mono"
              value={settings.personality_text}
              onChange={(e) => setSettings({ ...settings, personality_text: e.target.value })}
              placeholder="למשל: קצר, חם, פותר בעיה; פונה בגוף ראשון רבים…"
            />
          </label>
          <label className="block text-sm text-slate-700">
            גבולות / תנאי שירות (מה מותר להבטיח, החזרים, זמני תגובה…)
            <textarea
              className="mt-1 w-full min-h-[100px] rounded-lg border border-slate-300 px-3 py-2 text-sm font-mono"
              value={settings.terms_and_boundaries_text}
              onChange={(e) => setSettings({ ...settings, terms_and_boundaries_text: e.target.value })}
            />
          </label>
          <label className="block text-sm text-slate-700">
            הקשר מוצר ושיטה (אופציונלי — ברירת מחדל קיימת אם ריק)
            <textarea
              className="mt-1 w-full min-h-[100px] rounded-lg border border-slate-300 px-3 py-2 text-sm font-mono"
              value={settings.methodology_context_text}
              onChange={(e) => setSettings({ ...settings, methodology_context_text: e.target.value })}
            />
          </label>
          <div
            className={`rounded-lg border px-3 py-2 text-sm ${
              settings.transactional_email_configured === false
                ? 'border-red-200 bg-red-50 text-red-950'
                : settings.transactional_email_configured === true
                  ? 'border-emerald-200 bg-emerald-50 text-emerald-950'
                  : 'border-slate-200 bg-slate-50 text-slate-700'
            }`}
          >
            <strong>מנוע שליחת מייל (Azure)</strong>
            {settings.transactional_email_configured === true &&
              settings.transactional_email_via === 'acs' && (
                <span className="block mt-1">מוגדר: Azure Communication Services (EMAIL_CONNECTION_STRING).</span>
              )}
            {settings.transactional_email_configured === true &&
              settings.transactional_email_via === 'sendgrid' && (
                <span className="block mt-1">מוגדר: SendGrid (SENDGRID_API_KEY).</span>
              )}
            {settings.transactional_email_configured === false && (
              <span className="block mt-1">
                לא מוגדר בשרת — לא תישלח תשובה אוטומטית בפועל. ב-Azure App Service הוסף{' '}
                <code className="rounded bg-white/80 px-1 text-xs">EMAIL_CONNECTION_STRING</code> או{' '}
                <code className="rounded bg-white/80 px-1 text-xs">SENDGRID_API_KEY</code> (+ כתובת שולח מאומתת ב־
                <code className="rounded bg-white/80 px-1 text-xs">EMAIL_SENDER</code>).
              </span>
            )}
            {settings.transactional_email_configured === undefined && (
              <span className="block mt-1 text-slate-600">
                סטטוס מנוע השליחה זמין אחרי פריסת שרת מעודכן — או רענון דף אחרי העדכון.
              </span>
            )}
          </div>
          <label className="flex items-start gap-2 text-sm text-slate-700 cursor-pointer">
            <input
              type="checkbox"
              className="mt-1 rounded border-slate-300"
              checked={settings.auto_reply_enabled}
              onChange={(e) => setSettings({ ...settings, auto_reply_enabled: e.target.checked })}
            />
            <span>
              <strong>תשובה אוטומטית ללקוח</strong> — כשמופעל, מייל נכנס שמגיע דרך ה־Webhook נרשם במערכת, נוצרת טיוטה ב־AI,
              והתשובה נשלחת אוטומטית לכתובת השולח (דרך ACS/SendGrid כמו שאר המיילים). כבוי = רישום וטיוטה בלבד ללא שליחה.
            </span>
          </label>
          {(typeof settings.auto_reply_effective === 'boolean' ||
            Boolean(settings.support_auto_reply_env?.trim())) && (
            <div className="rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-xs text-sky-950 space-y-1">
              <div>
                <strong>בפועל כעת בשרת:</strong>{' '}
                {settings.auto_reply_effective === true
                  ? 'שולח תשובה אוטומטית (כולל אחרי מייל נכנס).'
                  : settings.auto_reply_effective === false
                    ? 'לא שולח — רישום וטיוטה בלבד.'
                    : '—'}
              </div>
              {settings.support_auto_reply_env?.trim() ? (
                <div>
                  Azure דורס את המסד:{' '}
                  <code className="rounded bg-white px-1">SUPPORT_AUTO_REPLY_ENABLED</code>={' '}
                  <code className="rounded bg-white px-1">{settings.support_auto_reply_env.trim()}</code>
                </div>
              ) : null}
            </div>
          )}
          <div className="rounded-lg border border-amber-100 bg-amber-50/80 p-4 text-sm text-slate-800 space-y-2">
            <div className="font-semibold text-amber-950">חיבור inbound (SendGrid, Make, Zapier…)</div>
            <p className="text-slate-700">
              <strong>Multipart</strong> (SendGrid Inbound Parse וכדומה): שדות טיפוסיים{' '}
              <code className="bg-white px-1 rounded text-xs">from</code>,{' '}
              <code className="bg-white px-1 rounded text-xs">to</code>,{' '}
              <code className="bg-white px-1 rounded text-xs">subject</code>,{' '}
              <code className="bg-white px-1 rounded text-xs">text</code> /{' '}
              <code className="bg-white px-1 rounded text-xs">html</code>,{' '}
              <code className="bg-white px-1 rounded text-xs">headers</code>.
            </p>
            <p className="text-slate-700">
              <strong>Make / Zapier</strong> אחרי טריגר IMAP לתיבת Hostinger: השתמשו במודול HTTP עם{' '}
              <code className="bg-white px-1 rounded text-xs">POST</code> וגוף{' '}
              <code className="bg-white px-1 rounded text-xs">JSON</code> — אין צורך בצעד נפרד ל-OpenAI או ל-Google Sheets:
              השרת כבר מריץ AI (Azure OpenAI), רושם בתיעוד במסד, ושולח תשובה דרך ACS/SendGrid כשמופעלת התשובה האוטומטית.
            </p>
            <div>
              <span className="text-slate-600">Webhook multipart:</span>
              <code className="mt-1 block break-all rounded bg-white px-2 py-1.5 text-xs font-mono border border-amber-200">
                {`${getApiBase()}/internal/support-email/inbound`}
              </code>
            </div>
            <div>
              <span className="text-slate-600">Webhook JSON (מומלץ ל-Make/Zapier):</span>
              <code className="mt-1 block break-all rounded bg-white px-2 py-1.5 text-xs font-mono border border-amber-200">
                {`${getApiBase()}/internal/support-email/inbound-json`}
              </code>
            </div>
            <p className="text-xs text-slate-600">
              מפתחות JSON נתמכים: <code className="bg-white px-1 rounded">from</code>,{' '}
              <code className="bg-white px-1 rounded">to</code>, <code className="bg-white px-1 rounded">subject</code>,{' '}
              <code className="bg-white px-1 rounded">text</code>, <code className="bg-white px-1 rounded">html</code>,{' '}
              <code className="bg-white px-1 rounded">headers</code>,{' '}
              <code className="bg-white px-1 rounded">message_id</code> (אופציונלי — למניעת כפילויות אם Make מריץ שוב אותה הודעה).
            </p>
            <p className="text-xs text-slate-600">
              חובה ב-Azure: <code className="bg-white px-1 rounded">SUPPORT_INBOUND_WEBHOOK_SECRET</code> — אותו ערך בכותרת{' '}
              <code className="bg-white px-1 rounded">X-Support-Inbound-Secret</code>. אופציונלי:{' '}
              <code className="bg-white px-1 rounded">SUPPORT_INBOUND_MAILBOX</code> (ברירת מחדל{' '}
              <code className="bg-white px-1 rounded">support@jewishcoacher.com</code>).
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => void saveSettings()}
              disabled={settingsBusy}
              className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {settingsBusy ? 'שומר…' : 'שמור הגדרות'}
            </button>
            {settings.updated_at && (
              <span className="text-xs text-slate-500">עודכן: {new Date(settings.updated_at).toLocaleString()}</span>
            )}
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm space-y-4">
          <h3 className="font-semibold text-slate-900">טיוטת תשובה (AI)</h3>
          <label className="block text-sm text-slate-700">
            מייל הלקוח
            <input
              type="email"
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={custEmail}
              onChange={(e) => setCustEmail(e.target.value)}
              placeholder="customer@example.com"
            />
          </label>
          <label className="block text-sm text-slate-700">
            תוכן הפנייה (הדבקה מהמייל)
            <textarea
              className="mt-1 w-full min-h-[120px] rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={incoming}
              onChange={(e) => setIncoming(e.target.value)}
            />
          </label>
          <div className="flex flex-wrap gap-4 text-sm text-slate-700">
            <label className="flex items-center gap-2">
              <span>שפה</span>
              <select
                className="rounded border border-slate-300 px-2 py-1"
                value={lang}
                onChange={(e) => setLang(e.target.value)}
              >
                <option value="he">עברית</option>
                <option value="en">English</option>
              </select>
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={recordInbound} onChange={(e) => setRecordInbound(e.target.checked)} />
              תעד פנייה נכנסת בטבלה
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={recordDraft} onChange={(e) => setRecordDraft(e.target.checked)} />
              תעד טיוטת AI בטבלה
            </label>
          </div>
          <button
            type="button"
            onClick={() => void runDraft()}
            disabled={draftBusy || !custEmail.trim() || !incoming.trim()}
            className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {draftBusy ? 'מייצר…' : 'צור טיוטת תשובה'}
          </button>

          {(draftSubject || draftBody) && (
            <div className="rounded-lg border border-emerald-100 bg-emerald-50/60 p-4 space-y-2">
              <div className="text-xs font-semibold text-emerald-900">טיוטה</div>
              <div className="text-sm">
                <span className="font-medium text-slate-700">נושא: </span>
                {draftSubject}
              </div>
              <pre className="whitespace-pre-wrap text-sm text-slate-800 font-sans">{draftBody}</pre>
              {draftNotes && (
                <div className="text-xs text-slate-600 border-t border-emerald-200 pt-2">
                  <span className="font-semibold">הערות פנימיות: </span>
                  {draftNotes}
                </div>
              )}
            </div>
          )}
          {snapshotJson && (
            <details className="text-xs">
              <summary className="cursor-pointer text-slate-600">הצג snapshot מערכת (JSON)</summary>
              <pre className="mt-2 max-h-48 overflow-auto rounded bg-slate-50 p-2 font-mono">{snapshotJson}</pre>
            </details>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm space-y-4">
        <h3 className="font-semibold text-slate-900">תיעוד תשובה שנשלחה (ידני)</h3>
        <p className="text-sm text-slate-600">
          אחרי ששלחת תשובה מ-Gmail / Outlook, תעד כאן את הנושא והגוף — זה יופיע בתיעוד לצד הפניות וטיוטות.
        </p>
        <div className="grid gap-3 md:grid-cols-2">
          <label className="block text-sm text-slate-700 md:col-span-2">
            נושא (אופציונלי)
            <input
              type="text"
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={outSubject}
              onChange={(e) => setOutSubject(e.target.value)}
            />
          </label>
          <label className="block text-sm text-slate-700 md:col-span-2">
            גוף התשובה שנשלחה
            <textarea
              className="mt-1 w-full min-h-[100px] rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={outBody}
              onChange={(e) => setOutBody(e.target.value)}
            />
          </label>
        </div>
        <button
          type="button"
          onClick={() => void logOutboundSent()}
          disabled={outBusy || !outBody.trim()}
          className="rounded-lg bg-slate-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {outBusy ? 'שומר…' : 'תעד תשובה יוצאת'}
        </button>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm space-y-4">
        <div className="flex flex-wrap items-end gap-3 justify-between">
          <div>
            <h3 className="font-semibold text-slate-900">תיעוד מיילים לפי משתמש</h3>
            <p className="text-sm text-slate-600 mt-1">
              סנן לפי מזהה משתמש פנימי (כמו בטבלת Users) או לפי כתובת מייל. כיוון: נכנס / יוצא / טיוטה.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void reloadLogs()}
            disabled={logsBusy}
            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50 disabled:opacity-50"
          >
            {logsBusy ? 'טוען…' : 'רענן תיעוד'}
          </button>
        </div>
        <div className="flex flex-wrap gap-3">
          <label className="text-sm text-slate-700">
            מייל לקוח
            <input
              type="text"
              className="mt-1 block w-56 rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
              value={filterEmail}
              onChange={(e) => setFilterEmail(e.target.value)}
              placeholder="support customer email"
            />
          </label>
          <label className="text-sm text-slate-700">
            מזהה משתמש (user id)
            <input
              type="text"
              className="mt-1 block w-36 rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
              value={filterUserId}
              onChange={(e) => setFilterUserId(e.target.value)}
              placeholder="e.g. 42"
            />
          </label>
          <label className="text-sm text-slate-700">
            כיוון
            <select
              className="mt-1 block rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
              value={filterDirection}
              onChange={(e) => setFilterDirection(e.target.value as typeof filterDirection)}
            >
              <option value="all">הכל</option>
              <option value="inbound">נכנס</option>
              <option value="outbound">יוצא</option>
              <option value="draft">טיוטה</option>
            </select>
          </label>
        </div>

        <div className="text-xs text-slate-500">
          סה״כ רשומות (לפי סינון שרת): {logsTotal} · מוצגות: {logs.length}
        </div>

        <div className="overflow-x-auto rounded-lg border border-slate-200">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-600">
              <tr>
                <th className="px-3 py-2">זמן</th>
                <th className="px-3 py-2">כיוון</th>
                <th className="px-3 py-2">מייל</th>
                <th className="px-3 py-2">משתמש</th>
                <th className="px-3 py-2">נושא</th>
                <th className="px-3 py-2">תוכן</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-3 py-8 text-center text-slate-500">
                    אין רשומות. הגדר סינון ולחץ «רענן תיעוד», או צור טיוטה כדי ליצור רישום ראשון.
                  </td>
                </tr>
              ) : (
                logs.map((row) => {
                  const outboundSendOk = coerceOutboundSendOk(row.meta);
                  return (
                  <tr key={row.id} className="align-top hover:bg-slate-50/80">
                    <td className="px-3 py-2 whitespace-nowrap text-slate-600">
                      {row.created_at ? new Date(row.created_at).toLocaleString() : '—'}
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={`rounded px-2 py-0.5 text-xs font-medium ${
                          row.direction === 'inbound'
                            ? 'bg-blue-100 text-blue-900'
                            : row.direction === 'outbound'
                              ? 'bg-green-100 text-green-900'
                              : 'bg-amber-100 text-amber-900'
                        }`}
                      >
                        {row.direction}
                      </span>
                      <div className="text-[10px] text-slate-400 mt-0.5">{row.channel}</div>
                      {row.direction === 'outbound' && outboundSendOk !== undefined ? (
                        <div
                          className={`text-[10px] mt-0.5 font-medium ${outboundSendOk ? 'text-emerald-700' : 'text-red-600'}`}
                        >
                          {outboundSendOk
                            ? 'שליחה: אושר ע״י ACS/SendGrid (לא תמיד אומר שהגיע לתיבה)'
                            : (() => {
                                const err =
                                  typeof row.meta.send_error === 'string' && row.meta.send_error.trim()
                                    ? row.meta.send_error.trim()
                                    : 'לא נשמרה סיבה (רישום ישן או לפני עדכון השרת)';
                                return `שליחה נכשלה: ${err.slice(0, 180)}${err.length > 180 ? '…' : ''}`;
                              })()}
                        </div>
                      ) : null}
                    </td>
                    <td className="px-3 py-2 font-mono text-xs">{row.customer_email}</td>
                    <td className="px-3 py-2 text-xs">
                      {row.user_id != null ? (
                        <>
                          #{row.user_id}
                          {row.user_display_name ? (
                            <div className="text-slate-500 truncate max-w-[140px]">{row.user_display_name}</div>
                          ) : null}
                        </>
                      ) : (
                        <span className="text-slate-400">לא matched</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-slate-700 max-w-[160px] truncate">{row.subject || '—'}</td>
                    <td className="px-3 py-2 text-slate-700 max-w-md">
                      <details>
                        <summary className="cursor-pointer text-xs text-slate-600">הצג גוף</summary>
                        <pre className="mt-1 whitespace-pre-wrap text-xs font-sans text-slate-800 max-h-40 overflow-auto">
                          {row.body}
                        </pre>
                      </details>
                    </td>
                  </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
