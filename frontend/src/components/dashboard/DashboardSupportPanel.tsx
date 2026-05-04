import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { i18n as I18nType } from 'i18next';
import { useUser } from '@clerk/clerk-react';
import { motion } from 'framer-motion';
import { Headphones, Loader2, Send, UserRound } from 'lucide-react';
import { apiClient } from '../../services/api';
import { isClerkSyntheticEmail } from '../../lib/clerkEmail';

/** Must match backend default `SUPPORT_INBOUND_MAILBOX` / dashboard copy. */
export const SUPPORT_INBOUND_MAILBOX = 'support@jewishcoacher.com';

export type DashboardSupportPalette = {
  bg?: string;
  card: string;
  text: string;
  textMuted: string;
  accent: string;
  accentLight: string;
  gold: string;
  border: string;
  shadow: string;
  primaryLight?: string;
};

export type SupportThreadItem = {
  id: number;
  direction: string;
  channel: string;
  subject: string | null;
  body: string;
  created_at: string | null;
};

interface DashboardSupportPanelProps {
  colors: DashboardSupportPalette;
  profileEmail: string | null;
  /** Clerk — מרענן JWT לפני קריאות תמיכה (מפחית 401 וטעינת היסטוריה ריקה). */
  refreshAuthToken?: () => Promise<string | null>;
}

function formatThreadTime(iso: string | null, locale: string): string {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    const loc = locale.toLowerCase().startsWith('he') ? 'he-IL' : 'en-US';
    return d.toLocaleString(loc, { dateStyle: 'medium', timeStyle: 'short' });
  } catch {
    return '';
  }
}

function parseAxiosErr(err: unknown): { status?: number; detail?: string } {
  const ax = err as {
    response?: { status?: number; data?: { detail?: string | { msg?: string }[] } };
    message?: string;
  };
  const status = ax?.response?.status;
  const d = ax?.response?.data?.detail;
  let detail: string | undefined;
  if (typeof d === 'string') detail = d;
  else if (Array.isArray(d)) detail = d.map((x) => String((x as { msg?: string }).msg ?? x)).join(' ');
  return { status, detail: detail?.trim() || ax?.message };
}

function SupportBubble({
  item,
  colors,
  t,
  i18n,
}: {
  item: SupportThreadItem;
  colors: DashboardSupportPalette;
  t: (key: string) => string;
  i18n: I18nType;
}) {
  const isUser = item.direction === 'inbound';
  const time = formatThreadTime(item.created_at, i18n.language);
  const isRtl = i18n.dir() === 'rtl';
  /** Hebrew UI: force RTL in bubbles; English keeps auto on body for mixed threads. */
  const bubbleDir = isRtl ? 'rtl' : 'ltr';
  const bodyDir = isRtl ? 'rtl' : 'auto';

  return (
    <div className={`flex w-full ${isUser ? 'justify-start' : 'justify-end'}`}>
      <div
        className="max-w-[min(92%,28rem)] rounded-2xl px-4 py-3 transition-shadow text-start"
        dir={bubbleDir}
        style={{
          background: isUser ? colors.accentLight : colors.card,
          borderInlineStart: `3px solid ${isUser ? colors.accent : colors.gold}`,
          boxShadow: isUser ? 'none' : `0 1px 3px rgba(46, 58, 86, 0.08), 0 0 0 1px ${colors.border}`,
        }}
      >
        <div className="flex items-center gap-2 mb-2 flex-wrap">
          {isUser ? (
            <UserRound className="w-4 h-4 flex-shrink-0" style={{ color: colors.accent }} aria-hidden />
          ) : (
            <Headphones className="w-4 h-4 flex-shrink-0" style={{ color: colors.gold }} aria-hidden />
          )}
          <span className="text-xs font-semibold" style={{ color: colors.text }}>
            {isUser ? t('support.thread.you') : t('support.thread.team')}
          </span>
          <span
            className="text-[11px] opacity-80 whitespace-nowrap ms-auto"
            style={{ color: colors.textMuted }}
            dir="ltr"
          >
            {time}
          </span>
        </div>
        {item.subject?.trim() ? (
          <p className="text-[11px] font-medium mb-1.5 leading-snug text-start" style={{ color: colors.textMuted }}>
            <span className="opacity-80">{t('support.thread.subjectLine')}:</span>{' '}
            <span style={{ color: colors.text }}>{item.subject}</span>
          </p>
        ) : null}
        <p
          className="text-sm leading-relaxed whitespace-pre-wrap break-words text-start"
          style={{ color: colors.text }}
          dir={bodyDir}
        >
          {item.body}
        </p>
      </div>
    </div>
  );
}

export function DashboardSupportPanel({ colors, profileEmail, refreshAuthToken }: DashboardSupportPanelProps) {
  const { t, i18n } = useTranslation();
  const { user } = useUser();
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');
  const [replyEmail, setReplyEmail] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [thread, setThread] = useState<SupportThreadItem[]>([]);
  const [threadLoading, setThreadLoading] = useState(true);
  const [threadError, setThreadError] = useState<string | null>(null);
  const threadEndRef = useRef<HTMLDivElement>(null);

  const threadScrollBg = colors.bg ?? colors.primaryLight ?? 'rgba(46, 58, 86, 0.06)';
  const isRtl = i18n.dir() === 'rtl';
  const textFieldsDir = isRtl ? 'rtl' : 'auto';

  const defaultReply = useMemo(() => {
    if (profileEmail && !isClerkSyntheticEmail(profileEmail)) return profileEmail;
    const cm = user?.primaryEmailAddress?.emailAddress ?? '';
    if (cm && !isClerkSyntheticEmail(cm)) return cm;
    return '';
  }, [profileEmail, user]);

  useEffect(() => {
    setReplyEmail(defaultReply);
  }, [defaultReply]);

  const loadThread = useCallback(
    async (opts?: { silent?: boolean }) => {
      const silent = !!opts?.silent;
      if (!silent) setThreadError(null);
      if (!silent) setThreadLoading(true);
      try {
        if (refreshAuthToken) {
          const tok = await refreshAuthToken();
          if (tok) apiClient.setToken(tok);
        }
        const data = await apiClient.getSupportThread();
        setThread(data.items ?? []);
      } catch (err: unknown) {
        if (silent) {
          console.debug('[support] thread refresh failed', err);
          return;
        }
        const { status } = parseAxiosErr(err);
        if (status === 401) setThreadError(t('support.thread.sessionExpired'));
        else setThreadError(t('support.thread.loadError'));
        setThread([]);
      } finally {
        if (!silent) setThreadLoading(false);
      }
    },
    [refreshAuthToken, t],
  );

  useEffect(() => {
    void loadThread();
  }, [loadThread]);

  /** Inbound webhook / mail routing can lag a few seconds — poll quietly while this tab is open. */
  useEffect(() => {
    const tick = window.setInterval(() => void loadThread({ silent: true }), 25_000);
    const onVis = () => {
      if (document.visibilityState === 'visible') void loadThread({ silent: true });
    };
    document.addEventListener('visibilitychange', onVis);
    return () => {
      window.clearInterval(tick);
      document.removeEventListener('visibilitychange', onVis);
    };
  }, [loadThread]);

  useEffect(() => {
    if (!threadLoading && thread.length > 0) {
      threadEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [thread, threadLoading]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setDone(false);
    const sub = subject.trim();
    const msg = message.trim();
    const reply = replyEmail.trim();
    if (!sub || !msg) {
      setError(t('support.contact.validation.required'));
      return;
    }
    if (!reply || !reply.includes('@')) {
      setError(t('support.contact.validation.email'));
      return;
    }
    setSubmitting(true);
    try {
      if (refreshAuthToken) {
        const tok = await refreshAuthToken();
        if (tok) apiClient.setToken(tok);
      }
      await apiClient.submitSupportContact({
        subject: sub,
        message: msg,
        reply_email: reply,
      });
      const fullSubj = `[Jewish Coach app] ${sub}`;
      setThread((prev) => [
        ...prev,
        {
          id: -Date.now(),
          direction: 'inbound',
          channel: 'user_dashboard',
          subject: fullSubj,
          body: msg,
          created_at: new Date().toISOString(),
        },
      ]);
      setDone(true);
      setSubject('');
      setMessage('');
      setReplyEmail(reply);
      await loadThread({ silent: true });
    } catch (err: unknown) {
      const { status, detail } = parseAxiosErr(err);
      if (status === 401) setError(t('support.thread.sessionExpired'));
      else if (detail && /expired|signature/i.test(detail)) setError(t('support.thread.sessionExpired'));
      else setError(detail || t('support.contact.errorGeneric'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl w-full mx-auto space-y-6">
      <motion.div
        className="rounded-xl p-5 md:p-6 border"
        style={{ background: colors.card, borderColor: colors.border, boxShadow: colors.shadow }}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h3 className="text-base font-semibold mb-1" style={{ color: colors.text }}>
          {t('support.contact.title')}
        </h3>
        <p className="text-xs leading-snug mb-4" style={{ color: colors.textMuted }}>
          {t('support.contact.intro')}
        </p>

        <div
          className="rounded-lg px-3 py-2.5 mb-5 text-sm"
          style={{ background: colors.accentLight, color: colors.text }}
        >
          <span className="font-semibold" style={{ color: colors.accent }}>
            {t('support.contact.supportEmailLabel')}
          </span>{' '}
          <a
            href={`mailto:${SUPPORT_INBOUND_MAILBOX}`}
            className="underline font-medium break-all"
            style={{ color: colors.accent }}
          >
            {SUPPORT_INBOUND_MAILBOX}
          </a>
        </div>

        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium mb-1.5" style={{ color: colors.textMuted }}>
              {t('support.contact.email')}
            </label>
            <input
              type="email"
              autoComplete="email"
              value={replyEmail}
              onChange={(e) => setReplyEmail(e.target.value)}
              className="w-full px-3 py-2.5 text-sm rounded-lg border focus:ring-2 focus:ring-blue-200 focus:outline-none"
              style={{ borderColor: colors.border, color: colors.text }}
              placeholder={t('support.contact.emailPlaceholder')}
              dir="ltr"
            />
            <p className="text-[11px] mt-1.5 leading-snug" style={{ color: colors.textMuted }}>
              {t('support.contact.emailHint')}
            </p>
          </div>
          <div>
            <label className="block text-xs font-medium mb-1.5" style={{ color: colors.textMuted }}>
              {t('support.contact.subject')}
            </label>
            <input
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              maxLength={500}
              className="w-full px-3 py-2.5 text-sm rounded-lg border focus:ring-2 focus:ring-blue-200 focus:outline-none"
              style={{ borderColor: colors.border, color: colors.text }}
              placeholder={t('support.contact.subjectPlaceholder')}
              dir={textFieldsDir}
            />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1.5" style={{ color: colors.textMuted }}>
              {t('support.contact.message')}
            </label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={6}
              maxLength={20000}
              className="w-full px-3 py-2.5 text-sm rounded-lg border focus:ring-2 focus:ring-blue-200 focus:outline-none resize-y min-h-[120px]"
              style={{ borderColor: colors.border, color: colors.text }}
              placeholder={t('support.contact.messagePlaceholder')}
              dir={textFieldsDir}
            />
          </div>

          {error ? (
            <p className="text-sm text-red-600" role="alert">
              {error}
            </p>
          ) : null}
          {done ? (
            <p className="text-sm font-medium" style={{ color: colors.accent }}>
              {t('support.contact.sent')}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={submitting}
            className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-lg text-white disabled:opacity-50"
            style={{ background: colors.accent }}
          >
            {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            {submitting ? t('support.contact.sending') : t('support.contact.send')}
          </button>
        </form>
      </motion.div>

      <motion.section
        className="rounded-2xl overflow-hidden border"
        style={{ background: colors.card, borderColor: colors.border, boxShadow: colors.shadow }}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05 }}
        aria-labelledby="support-thread-heading"
      >
        <header className="px-5 pt-5 pb-3 border-b" style={{ borderColor: colors.border }}>
          <h2 id="support-thread-heading" className="text-base font-semibold" style={{ color: colors.text }}>
            {t('support.thread.title')}
          </h2>
          <p className="text-xs mt-1 leading-relaxed" style={{ color: colors.textMuted }}>
            {t('support.thread.subtitle')}
          </p>
        </header>

        <div
          className="max-h-[min(440px,52vh)] overflow-y-auto custom-scrollbar px-3 sm:px-4 py-4 space-y-4"
          style={{ background: threadScrollBg }}
        >
          {threadLoading ? (
            <div className="flex flex-col items-center justify-center gap-3 py-14">
              <Loader2 className="w-9 h-9 animate-spin" style={{ color: colors.accent }} aria-hidden />
              <p className="text-sm" style={{ color: colors.textMuted }}>
                {t('support.thread.loading')}
              </p>
            </div>
          ) : threadError ? (
            <p className="text-sm text-center py-10 px-4 text-red-600" role="alert">
              {threadError}
            </p>
          ) : thread.length === 0 ? (
            <p
              className="text-sm text-center py-12 px-5 leading-relaxed max-w-md mx-auto"
              style={{ color: colors.textMuted }}
            >
              {t('support.thread.empty')}
            </p>
          ) : (
            thread.map((item) => (
              <SupportBubble key={item.id} item={item} colors={colors} t={t} i18n={i18n} />
            ))
          )}
          <div ref={threadEndRef} className="h-px" aria-hidden />
        </div>
      </motion.section>
    </div>
  );
}
