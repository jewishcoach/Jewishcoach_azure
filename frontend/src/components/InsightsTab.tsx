/**
 * InsightsTab — Deep psychological profile analysis
 *
 * Three states:
 *  1. locked     — not enough conversation data yet
 *  2. consent    — needs user's explicit agreement
 *  3. loaded     — shows the full analysis
 */

import { useState, useEffect } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Lock,
  ShieldCheck,
  ShieldOff,
  RefreshCw,
  Loader2,
  MessageSquareText,
  Waves,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertTriangle,
  Lightbulb,
  Compass,
  Layers,
  Brain,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Quote,
  ArrowRight,
} from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const C = {
  bg: '#F0F1F3',
  card: '#FFFFFF',
  text: '#2E3A56',
  muted: '#5A6B8A',
  accent: '#2E3A56',
  accentLight: 'rgba(46,58,86,0.10)',
  gold: '#B38728',
  goldLight: 'rgba(179,135,40,0.12)',
  border: '#E2E4E8',
  shadow: '0 1px 3px rgba(46,58,86,0.08)',
  shadowMd: '0 4px 16px rgba(46,58,86,0.10)',
  green: '#2D7A4F',
  greenLight: 'rgba(45,122,79,0.10)',
  red: '#C0392B',
  redLight: 'rgba(192,57,43,0.10)',
  amber: '#D97706',
  amberLight: 'rgba(217,119,6,0.10)',
};

// ─── Types ────────────────────────────────────────────────────────────────────

interface InsightStatus {
  has_consent: boolean;
  total_user_words: number;
  n_conversations: number;
  unlocked: boolean;
  min_words_required: number;
  has_cached_analysis: boolean;
  cache_stale: boolean;
}

interface Block {
  name: string;
  description: string;
  quote: string;
  frequency: number;
}

interface CoreBelief {
  belief: string;
  evidence: string[];
  stage: string;
}

interface GrowthPoint {
  area: string;
  early_example: string;
  recent_example: string;
  direction: 'positive' | 'stagnant' | 'negative';
}

interface Analysis {
  generated_at: string;
  conversations_analyzed: number;
  total_user_words: number;
  language_depth_score: number;
  language_examples: string[];
  language_depth_note: string;
  emotional_richness_score: number;
  frequent_emotions: string[];
  avoided_emotions: string[];
  emotional_note: string;
  engagement_trend: 'rising' | 'stable' | 'declining';
  engagement_note: string;
  psychological_blocks: Block[];
  core_beliefs: CoreBelief[];
  coping_style: string;
  coping_description: string;
  self_agency_score: number;
  agency_examples: string[];
  growth_points: GrowthPoint[];
  summary: string;
  key_insight: string;
  one_invitation: string;
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function ScoreBar({ value, color = C.accent }: { value: number; color?: string }) {
  const pct = Math.round(value * 100);
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: C.border }}>
        <motion.div
          className="h-full rounded-full"
          style={{ background: color }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      </div>
      <span className="text-sm font-semibold tabular-nums w-9 text-right" style={{ color: C.text }}>
        {pct}%
      </span>
    </div>
  );
}

function SectionCard({
  icon,
  title,
  children,
  delay = 0,
  accent,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
  delay?: number;
  accent?: string;
}) {
  return (
    <motion.div
      className="rounded-2xl p-5"
      style={{ background: C.card, boxShadow: C.shadow }}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.3 }}
    >
      <div className="flex items-center gap-2.5 mb-4">
        <div
          className="p-1.5 rounded-lg"
          style={{ background: accent || C.accentLight, color: C.accent }}
        >
          {icon}
        </div>
        <h3 className="text-sm font-semibold" style={{ color: C.text }}>
          {title}
        </h3>
      </div>
      {children}
    </motion.div>
  );
}

function InlineQuote({ text }: { text: string }) {
  return (
    <div
      className="flex gap-2 mt-2 rounded-lg px-3 py-2"
      style={{ background: C.accentLight }}
    >
      <Quote className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" style={{ color: C.muted }} />
      <p className="text-xs italic leading-relaxed" style={{ color: C.muted }}>
        {text}
      </p>
    </div>
  );
}

function Chip({ label, variant = 'default' }: { label: string; variant?: 'default' | 'muted' | 'gold' }) {
  const styles = {
    default: { background: C.accentLight, color: C.accent },
    muted: { background: C.bg, color: C.muted },
    gold: { background: C.goldLight, color: C.gold },
  }[variant];
  return (
    <span className="inline-block text-xs px-2.5 py-1 rounded-full font-medium" style={styles}>
      {label}
    </span>
  );
}

function ExpandableBlock({ block }: { block: Block }) {
  const [open, setOpen] = useState(false);
  return (
    <div
      className="rounded-xl border overflow-hidden transition-all"
      style={{ borderColor: C.border }}
    >
      <button
        className="w-full flex items-center justify-between px-4 py-3 text-right hover:bg-gray-50 transition-colors"
        onClick={() => setOpen(!open)}
      >
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" style={{ color: C.amber }} />
          <span className="text-sm font-medium" style={{ color: C.text }}>
            {block.name}
          </span>
          {block.frequency > 1 && (
            <span
              className="text-xs px-1.5 py-0.5 rounded-full font-semibold"
              style={{ background: C.amberLight, color: C.amber }}
            >
              ×{block.frequency}
            </span>
          )}
        </div>
        {open ? (
          <ChevronUp className="w-4 h-4" style={{ color: C.muted }} />
        ) : (
          <ChevronDown className="w-4 h-4" style={{ color: C.muted }} />
        )}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="px-4 pb-3 space-y-2"
          >
            <p className="text-sm" style={{ color: C.muted }}>
              {block.description}
            </p>
            <InlineQuote text={block.quote} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function GrowthItem({ point }: { point: GrowthPoint }) {
  const icon =
    point.direction === 'positive' ? (
      <TrendingUp className="w-4 h-4" style={{ color: C.green }} />
    ) : point.direction === 'negative' ? (
      <TrendingDown className="w-4 h-4" style={{ color: C.red }} />
    ) : (
      <Minus className="w-4 h-4" style={{ color: C.muted }} />
    );

  const bg =
    point.direction === 'positive'
      ? C.greenLight
      : point.direction === 'negative'
      ? C.redLight
      : C.accentLight;

  return (
    <div className="rounded-xl p-4 space-y-2.5" style={{ background: bg }}>
      <div className="flex items-center gap-2">
        {icon}
        <span className="text-sm font-semibold" style={{ color: C.text }}>
          {point.area}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-3 text-xs" style={{ color: C.muted }}>
        <div>
          <p className="font-medium mb-1" style={{ color: C.muted }}>
            אז
          </p>
          <p className="italic">"{point.early_example}"</p>
        </div>
        <div>
          <p className="font-medium mb-1" style={{ color: C.green }}>
            עכשיו
          </p>
          <p className="italic">"{point.recent_example}"</p>
        </div>
      </div>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export function InsightsTab() {
  const { getToken } = useAuth();
  const [status, setStatus] = useState<InsightStatus | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [grantingConsent, setGrantingConsent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchStatus();
  }, []);

  const fetchStatus = async () => {
    setLoadingStatus(true);
    try {
      const token = await getToken();
      const res = await fetch(`${API_URL}/api/profile/insights/status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed to load status');
      const data = await res.json();
      setStatus(data);
      if (data.has_consent && data.has_cached_analysis) {
        fetchAnalysis(false);
      }
    } catch (e) {
      setError('לא ניתן לטעון את הנתונים');
    } finally {
      setLoadingStatus(false);
    }
  };

  const grantConsent = async () => {
    setGrantingConsent(true);
    try {
      const token = await getToken();
      await fetch(`${API_URL}/api/profile/insights/consent`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      await fetchStatus();
      fetchAnalysis(false);
    } catch {
      setError('שגיאה בשמירת ההסכמה');
    } finally {
      setGrantingConsent(false);
    }
  };

  const revokeConsent = async () => {
    const token = await getToken();
    await fetch(`${API_URL}/api/profile/insights/consent`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    });
    setAnalysis(null);
    fetchStatus();
  };

  const fetchAnalysis = async (forceRefresh = false) => {
    setLoadingAnalysis(true);
    setError(null);
    try {
      const token = await getToken();
      const url = `${API_URL}/api/profile/insights${forceRefresh ? '?refresh=true' : ''}`;
      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(await res.text());
      setAnalysis(await res.json());
    } catch (e: any) {
      setError('הניתוח נכשל. נסה שוב מאוחר יותר.');
    } finally {
      setLoadingAnalysis(false);
    }
  };

  // ── Loading state ──
  if (loadingStatus) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin" style={{ color: C.accent }} />
      </div>
    );
  }

  if (!status) return null;

  // ── Locked: not enough data ──
  if (!status.unlocked) {
    const pct = Math.min(100, Math.round((status.total_user_words / status.min_words_required) * 100));
    return (
      <motion.div
        className="flex flex-col items-center justify-center py-16 px-8 text-center"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        <div
          className="w-16 h-16 rounded-2xl flex items-center justify-center mb-5"
          style={{ background: C.accentLight }}
        >
          <Lock className="w-7 h-7" style={{ color: C.accent }} />
        </div>
        <h2 className="text-lg font-semibold mb-2" style={{ color: C.text }}>
          המבט הפנימי עדיין ננעל
        </h2>
        <p className="text-sm mb-8 max-w-xs" style={{ color: C.muted }}>
          לניתוח עמוק נדרשות לפחות {status.min_words_required} מילים של שיחה. המשך להתאמן כדי לפתוח
          את הפיצ'ר.
        </p>
        <div className="w-full max-w-xs">
          <div className="flex justify-between text-xs mb-1.5" style={{ color: C.muted }}>
            <span>{status.total_user_words} מילים</span>
            <span>{status.min_words_required} מילים</span>
          </div>
          <div className="h-2 rounded-full overflow-hidden" style={{ background: C.border }}>
            <motion.div
              className="h-full rounded-full"
              style={{ background: C.accent }}
              initial={{ width: 0 }}
              animate={{ width: `${pct}%` }}
              transition={{ duration: 1, ease: 'easeOut' }}
            />
          </div>
          <p className="text-xs mt-2" style={{ color: C.muted }}>
            {pct}% מהדרך
          </p>
        </div>
      </motion.div>
    );
  }

  // ── Consent required ──
  if (!status.has_consent) {
    return (
      <motion.div
        className="flex flex-col items-center justify-center py-12 px-8 text-center max-w-md mx-auto"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div
          className="w-16 h-16 rounded-2xl flex items-center justify-center mb-5"
          style={{ background: C.goldLight }}
        >
          <ShieldCheck className="w-7 h-7" style={{ color: C.gold }} />
        </div>
        <h2 className="text-lg font-semibold mb-3" style={{ color: C.text }}>
          מבט פנימי — ניתוח פסיכולוגי עמוק
        </h2>
        <p className="text-sm mb-6 leading-relaxed" style={{ color: C.muted }}>
          כדי ליצור את הניתוח, הבינה המלאכותית תעבור על נושאי השיחות, הרגשות, הדפוסים והשפה
          שחלקת בשיחות האימון שלך.
        </p>

        <div className="w-full rounded-xl p-4 mb-6 text-right space-y-2.5" style={{ background: C.accentLight }}>
          {[
            'המידע נשמר אצלך בלבד',
            'לא נעביר לגורמים שלישיים',
            'ניתן למחוק את הניתוח בכל עת',
            'זהו ניתוח עזר — לא תחליף לטיפול מקצועי',
          ].map((item, i) => (
            <div key={i} className="flex items-start gap-2.5">
              <ShieldCheck className="w-4 h-4 mt-0.5 flex-shrink-0" style={{ color: C.accent }} />
              <p className="text-sm" style={{ color: C.text }}>
                {item}
              </p>
            </div>
          ))}
        </div>

        {error && (
          <p className="text-sm mb-4" style={{ color: C.red }}>
            {error}
          </p>
        )}

        <button
          onClick={grantConsent}
          disabled={grantingConsent}
          className="w-full flex items-center justify-center gap-2 py-3 rounded-xl font-medium text-white disabled:opacity-60 transition-opacity"
          style={{ background: C.accent }}
        >
          {grantingConsent ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <ShieldCheck className="w-4 h-4" />
          )}
          אני מסכים/ה לנתח את שיחותיי
        </button>
      </motion.div>
    );
  }

  // ── Loading analysis ──
  if (loadingAnalysis || (!analysis && !error)) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <Loader2 className="w-8 h-8 animate-spin" style={{ color: C.accent }} />
        <p className="text-sm" style={{ color: C.muted }}>
          מנתח את השיחות שלך… זה עשוי לקחת כמה שניות
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-3">
        <AlertTriangle className="w-8 h-8" style={{ color: C.amber }} />
        <p className="text-sm" style={{ color: C.muted }}>
          {error}
        </p>
        <button
          onClick={() => fetchAnalysis(false)}
          className="text-sm px-4 py-2 rounded-xl"
          style={{ background: C.accentLight, color: C.accent }}
        >
          נסה שוב
        </button>
      </div>
    );
  }

  if (!analysis) return null;

  // ── Full analysis view ──
  const generatedDate = new Date(analysis.generated_at).toLocaleDateString('he-IL', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });

  return (
    <div className="space-y-5 pb-8">
      {/* Header bar */}
      <div
        className="flex items-center justify-between rounded-xl px-4 py-3"
        style={{ background: C.card, boxShadow: C.shadow }}
      >
        <div>
          <p className="text-xs" style={{ color: C.muted }}>
            מבוסס על {analysis.conversations_analyzed} שיחות •{' '}
            {analysis.total_user_words.toLocaleString('he-IL')} מילים • {generatedDate}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {status.cache_stale && (
            <span
              className="text-xs px-2 py-1 rounded-lg"
              style={{ background: C.amberLight, color: C.amber }}
            >
              יש שיחות חדשות
            </span>
          )}
          <button
            onClick={() => fetchAnalysis(true)}
            className="p-1.5 rounded-lg transition-colors hover:bg-gray-100"
            title="רענן ניתוח"
            style={{ color: C.muted }}
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={revokeConsent}
            className="p-1.5 rounded-lg transition-colors hover:bg-gray-100"
            title="מחק ניתוח ובטל הסכמה"
            style={{ color: C.muted }}
          >
            <ShieldOff className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Summary card */}
      <motion.div
        className="rounded-2xl p-6"
        style={{
          background: `linear-gradient(135deg, ${C.accent} 0%, #1a2540 100%)`,
          boxShadow: C.shadowMd,
        }}
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="flex items-center gap-2 mb-3">
          <Sparkles className="w-4 h-4" style={{ color: C.gold }} />
          <span className="text-xs font-medium" style={{ color: 'rgba(255,255,255,0.6)' }}>
            פורטרט אישי
          </span>
        </div>
        <p className="text-sm leading-relaxed mb-4" style={{ color: 'rgba(255,255,255,0.9)' }}>
          {analysis.summary}
        </p>
        <div
          className="rounded-xl p-3 flex gap-2.5"
          style={{ background: 'rgba(255,255,255,0.08)' }}
        >
          <Lightbulb className="w-4 h-4 flex-shrink-0 mt-0.5" style={{ color: C.gold }} />
          <p className="text-sm" style={{ color: 'rgba(255,255,255,0.85)' }}>
            {analysis.key_insight}
          </p>
        </div>
      </motion.div>

      {/* 3-column metrics */}
      <div className="grid grid-cols-3 gap-4">
        <SectionCard
          icon={<MessageSquareText className="w-4 h-4" />}
          title="עומק שפה"
          delay={0.05}
        >
          <ScoreBar value={analysis.language_depth_score} color={C.accent} />
          <p className="text-xs mt-3 leading-relaxed" style={{ color: C.muted }}>
            {analysis.language_depth_note}
          </p>
          {analysis.language_examples.slice(0, 2).map((ex, i) => (
            <InlineQuote key={i} text={ex} />
          ))}
        </SectionCard>

        <SectionCard
          icon={<Waves className="w-4 h-4" />}
          title="ביטוי רגשי"
          delay={0.1}
        >
          <ScoreBar value={analysis.emotional_richness_score} color={C.gold} />
          {analysis.frequent_emotions.length > 0 && (
            <div className="mt-3">
              <p className="text-xs font-medium mb-1.5" style={{ color: C.muted }}>
                תכוף
              </p>
              <div className="flex flex-wrap gap-1.5">
                {analysis.frequent_emotions.map((e) => (
                  <Chip key={e} label={e} variant="default" />
                ))}
              </div>
            </div>
          )}
          {analysis.avoided_emotions.length > 0 && (
            <div className="mt-3">
              <p className="text-xs font-medium mb-1.5" style={{ color: C.muted }}>
                נמנע
              </p>
              <div className="flex flex-wrap gap-1.5">
                {analysis.avoided_emotions.map((e) => (
                  <Chip key={e} label={e} variant="muted" />
                ))}
              </div>
            </div>
          )}
        </SectionCard>

        <SectionCard
          icon={
            analysis.engagement_trend === 'rising' ? (
              <TrendingUp className="w-4 h-4" />
            ) : analysis.engagement_trend === 'declining' ? (
              <TrendingDown className="w-4 h-4" />
            ) : (
              <Minus className="w-4 h-4" />
            )
          }
          title="מעורבות"
          delay={0.15}
          accent={
            analysis.engagement_trend === 'rising'
              ? C.greenLight
              : analysis.engagement_trend === 'declining'
              ? C.redLight
              : C.accentLight
          }
        >
          <p
            className="text-base font-semibold mb-2"
            style={{
              color:
                analysis.engagement_trend === 'rising'
                  ? C.green
                  : analysis.engagement_trend === 'declining'
                  ? C.red
                  : C.text,
            }}
          >
            {analysis.engagement_trend === 'rising'
              ? 'עולה'
              : analysis.engagement_trend === 'declining'
              ? 'יורדת'
              : 'יציבה'}
          </p>
          <p className="text-xs leading-relaxed" style={{ color: C.muted }}>
            {analysis.engagement_note}
          </p>
        </SectionCard>
      </div>

      {/* Psychological blocks */}
      {analysis.psychological_blocks.length > 0 && (
        <SectionCard
          icon={<Layers className="w-4 h-4" />}
          title="חסמים שזוהו"
          delay={0.2}
          accent={C.amberLight}
        >
          <div className="space-y-2">
            {analysis.psychological_blocks.map((block, i) => (
              <ExpandableBlock key={i} block={block} />
            ))}
          </div>
        </SectionCard>
      )}

      {/* Core beliefs + self-agency */}
      <div className="grid md:grid-cols-2 gap-4">
        {analysis.core_beliefs.length > 0 && (
          <SectionCard
            icon={<Brain className="w-4 h-4" />}
            title="אמונות ליבה מרומזות"
            delay={0.25}
          >
            <div className="space-y-4">
              {analysis.core_beliefs.map((cb, i) => (
                <div key={i}>
                  <p className="text-sm font-medium mb-1.5" style={{ color: C.text }}>
                    "{cb.belief}"
                  </p>
                  {cb.stage && (
                    <Chip label={`שלב ${cb.stage}`} variant="gold" />
                  )}
                  {cb.evidence.slice(0, 2).map((ev, j) => (
                    <InlineQuote key={j} text={ev} />
                  ))}
                </div>
              ))}
            </div>
          </SectionCard>
        )}

        <SectionCard
          icon={<Compass className="w-4 h-4" />}
          title="עמדה עצמית — מוקד שליטה"
          delay={0.3}
        >
          <div className="mb-3">
            <div className="flex justify-between text-xs mb-1.5" style={{ color: C.muted }}>
              <span>חיצוני</span>
              <span>פנימי</span>
            </div>
            <ScoreBar value={analysis.self_agency_score} color={C.green} />
          </div>
          <p className="text-xs mb-3" style={{ color: C.muted }}>
            {analysis.self_agency_score >= 0.6
              ? 'נטייה ללקיחת אחריות עצמית'
              : analysis.self_agency_score >= 0.4
              ? 'מאוזן בין אחריות לגורמים חיצוניים'
              : 'נטייה לייחס אחריות לגורמים חיצוניים'}
          </p>
          <div className="space-y-1">
            {analysis.agency_examples.slice(0, 2).map((ex, i) => (
              <InlineQuote key={i} text={ex} />
            ))}
          </div>
        </SectionCard>
      </div>

      {/* Coping style */}
      <SectionCard
        icon={<Lightbulb className="w-4 h-4" />}
        title="סגנון התמודדות"
        delay={0.35}
        accent={C.goldLight}
      >
        <div className="flex items-start gap-3">
          <Chip label={analysis.coping_style} variant="gold" />
          <p className="text-sm leading-relaxed" style={{ color: C.muted }}>
            {analysis.coping_description}
          </p>
        </div>
      </SectionCard>

      {/* Growth trajectory */}
      {analysis.growth_points.length > 0 && (
        <SectionCard
          icon={<TrendingUp className="w-4 h-4" />}
          title="מסלול הצמיחה"
          delay={0.4}
          accent={C.greenLight}
        >
          <div className="space-y-3">
            {analysis.growth_points.map((gp, i) => (
              <GrowthItem key={i} point={gp} />
            ))}
          </div>
        </SectionCard>
      )}

      {/* Invitation */}
      <motion.div
        className="rounded-2xl p-5 flex gap-4"
        style={{
          background: C.goldLight,
          border: `1px solid rgba(179,135,40,0.25)`,
        }}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.45 }}
      >
        <div
          className="w-8 h-8 rounded-xl flex-shrink-0 flex items-center justify-center"
          style={{ background: C.goldLight }}
        >
          <ArrowRight className="w-4 h-4" style={{ color: C.gold }} />
        </div>
        <div>
          <p className="text-xs font-medium mb-1" style={{ color: C.gold }}>
            הזמנה להמשך הדרך
          </p>
          <p className="text-sm leading-relaxed" style={{ color: C.text }}>
            {analysis.one_invitation}
          </p>
        </div>
      </motion.div>
    </div>
  );
}
