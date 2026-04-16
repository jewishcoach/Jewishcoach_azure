import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';

const COLORS = {
  text: '#2E3A56',
  textMuted: '#5A6B8A',
  bar: '#2E3A56',
  barMuted: 'rgba(46, 58, 86, 0.12)',
  border: '#E2E4E8',
  cardSub: 'rgba(46, 58, 86, 0.04)',
};

function StatTile({ value, label }: { value: number; label: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl p-4 border"
      style={{ borderColor: COLORS.border, background: COLORS.cardSub }}
    >
      <p className="text-2xl font-semibold tabular-nums tracking-tight" style={{ color: COLORS.text }}>
        {value}
      </p>
      <p className="text-xs mt-1.5 leading-snug" style={{ color: COLORS.textMuted }}>
        {label}
      </p>
    </motion.div>
  );
}

export interface DashboardStatsSummaryProps {
  conversations: number;
  daysActive: number;
  totalMessages: number;
  messagesThisBilling: number;
  billingCap: number;
  messagesLimit: number | null;
}

export function DashboardStatsSummary({
  conversations,
  daysActive,
  totalMessages,
  messagesThisBilling,
  billingCap,
  messagesLimit,
}: DashboardStatsSummaryProps) {
  const { t } = useTranslation();
  const unlimited = messagesLimit === -1;
  const showBar = !unlimited && billingCap > 0;
  const barPct = showBar ? Math.min(100, (messagesThisBilling / billingCap) * 100) : 0;

  return (
    <div className="space-y-6">
      <section>
        <h4 className="text-xs font-semibold mb-3 uppercase tracking-wide" style={{ color: COLORS.textMuted }}>
          {t('dashboard.statsActivity')}
        </h4>
        <div className="grid grid-cols-2 gap-3">
          <StatTile value={conversations} label={t('dashboard.conversations')} />
          <StatTile value={daysActive} label={t('dashboard.daysActive')} />
        </div>
      </section>

      <section>
        <h4 className="text-xs font-semibold mb-3 uppercase tracking-wide" style={{ color: COLORS.textMuted }}>
          {t('dashboard.statsMessages')}
        </h4>
        <div className="space-y-3">
          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
            className="rounded-xl p-4 border"
            style={{ borderColor: COLORS.border, background: COLORS.cardSub }}
          >
            <p className="text-xs font-medium mb-1" style={{ color: COLORS.textMuted }}>
              {t('dashboard.messagesTotal')}
            </p>
            <p className="text-2xl font-semibold tabular-nums" style={{ color: COLORS.text }}>
              {totalMessages}
            </p>
            <p className="text-[11px] mt-1.5 leading-snug" style={{ color: COLORS.textMuted }}>
              {t('dashboard.messagesTotalHint')}
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="rounded-xl p-4 border"
            style={{ borderColor: COLORS.border, background: COLORS.cardSub }}
          >
            <div className="flex items-start justify-between gap-3 flex-wrap">
              <div className="min-w-0">
                <p className="text-xs font-medium" style={{ color: COLORS.textMuted }}>
                  {t('dashboard.messagesBillingPeriod')}
                </p>
                <p className="text-[11px] mt-1 leading-snug" style={{ color: COLORS.textMuted }}>
                  {t('dashboard.messagesBillingHint')}
                </p>
              </div>
              {unlimited ? (
                <p className="text-lg font-semibold shrink-0 tabular-nums" style={{ color: COLORS.text }}>
                  {messagesThisBilling}{' '}
                  <span className="text-xs font-normal" style={{ color: COLORS.textMuted }}>
                    ({t('dashboard.messagesUnlimited')})
                  </span>
                </p>
              ) : (
                <p
                  className="text-lg font-semibold tabular-nums shrink-0"
                  dir="ltr"
                  translate="no"
                  style={{ color: COLORS.text }}
                >
                  {messagesThisBilling} / {billingCap}
                </p>
              )}
            </div>
            {showBar && (
              <div className="mt-3 h-2 rounded-full overflow-hidden" style={{ background: COLORS.barMuted }}>
                <motion.div
                  className="h-full rounded-full"
                  style={{ background: COLORS.bar }}
                  initial={{ width: 0 }}
                  animate={{ width: `${barPct}%` }}
                  transition={{ duration: 0.55, ease: 'easeOut' }}
                />
              </div>
            )}
          </motion.div>
        </div>
      </section>
    </div>
  );
}
