import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useUser } from '@clerk/clerk-react';
import { motion } from 'framer-motion';
import { Loader2, Send } from 'lucide-react';
import { apiClient } from '../../services/api';
import { isClerkSyntheticEmail } from '../../lib/clerkEmail';

/** Must match backend default `SUPPORT_INBOUND_MAILBOX` / dashboard copy. */
export const SUPPORT_INBOUND_MAILBOX = 'support@jewishcoacher.com';

export type DashboardSupportPalette = {
  card: string;
  text: string;
  textMuted: string;
  accent: string;
  accentLight: string;
  border: string;
  shadow: string;
};

interface DashboardSupportPanelProps {
  colors: DashboardSupportPalette;
  profileEmail: string | null;
}

export function DashboardSupportPanel({ colors, profileEmail }: DashboardSupportPanelProps) {
  const { t } = useTranslation();
  const { user } = useUser();
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');
  const [replyEmail, setReplyEmail] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const defaultReply = useMemo(() => {
    if (profileEmail && !isClerkSyntheticEmail(profileEmail)) return profileEmail;
    const cm = user?.primaryEmailAddress?.emailAddress ?? '';
    if (cm && !isClerkSyntheticEmail(cm)) return cm;
    return '';
  }, [profileEmail, user]);

  useEffect(() => {
    setReplyEmail(defaultReply);
  }, [defaultReply]);

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
      await apiClient.submitSupportContact({
        subject: sub,
        message: msg,
        reply_email: reply,
      });
      setDone(true);
      setSubject('');
      setMessage('');
      setReplyEmail(reply);
    } catch (err: unknown) {
      const ax = err as { response?: { data?: { detail?: string | string[] } }; message?: string };
      const d = ax?.response?.data?.detail;
      const text = Array.isArray(d) ? d.map((x) => String(x)).join(' ') : typeof d === 'string' ? d : ax?.message;
      setError(text?.trim() || t('support.contact.errorGeneric'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-xl w-full mx-auto">
      <motion.div
        className="rounded-xl p-5 md:p-6"
        style={{ background: colors.card, boxShadow: colors.shadow }}
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
    </div>
  );
}
