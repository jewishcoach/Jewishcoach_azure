import { useState } from 'react';
import { CheckCircle, ChevronDown, ChevronUp } from 'lucide-react';
import type { CompletedToolResult } from '../types';

const TOOL_LABELS: Record<string, string> = {
  event_form: 'אירוע',
  emotion_selector: 'רגשות',
  action_field: 'פעולה',
  matzui_summary: 'סיכום המצוי',
  comparison_card: 'מצוי מול רצוי',
  gap_card: 'הפער',
  sentence_builder: 'פרדיגמה ועמדה',
  balance_scale: 'רווח והפסד',
  trait_card_builder: 'כרטיס כוחות',
  declaration_card: 'הבחירה החדשה',
  commitment_card: 'מחויבות',
};

const FIELD_LABELS: Record<string, string> = {
  when: 'מתי',
  who: 'עם מי',
  what: 'מה קרה',
  emotions: 'רגשות',
  thought: 'מחשבה',
  action_actual: 'מעשה',
  action_desired: 'מעשה רצוי',
  emotion_desired: 'רגש רצוי',
  thought_desired: 'מחשבה רצויה',
  gap_name: 'שם הפער',
  gap_score: 'עוצמה',
  paradigm: 'פרדיגמה',
  reality_belief: 'אמונת שורש',
  gains: 'רווחים',
  losses: 'הפסדים',
  source: 'מקור',
  nature: 'טבע',
  renewal: 'בחירה חדשה',
  commitment: 'מחויבות',
  vision: 'חזון',
};

function formatValue(value: unknown): string {
  if (Array.isArray(value)) return value.join(', ');
  if (typeof value === 'object' && value !== null) {
    return Object.entries(value)
      .map(([k, v]) => `${FIELD_LABELS[k] || k}: ${formatValue(v)}`)
      .join(' | ');
  }
  return String(value ?? '');
}

interface CompletedToolCardProps {
  result: CompletedToolResult;
}

export function CompletedToolCard({ result }: CompletedToolCardProps) {
  const [expanded, setExpanded] = useState(false);
  const label = TOOL_LABELS[result.tool_type] || result.tool_type;

  const dataEntries = Object.entries(result.data || {}).filter(
    ([, v]) => v !== null && v !== undefined && v !== '' && !(Array.isArray(v) && v.length === 0),
  );

  return (
    <div
      dir="rtl"
      className={`px-4 py-2.5 rounded-xl bg-[rgba(3,255,230,0.08)] border border-[#04c4b1] w-full max-w-[662px]
                 animate-[fadeIn_0.3s_ease-out] cursor-pointer select-none transition-all ${expanded ? 'pb-3' : ''}`}
      onClick={() => setExpanded((prev) => !prev)}
    >
      <div className="flex items-center gap-3">
        <CheckCircle size={16} className="text-[#01897b] flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <span
            className="text-xs font-semibold text-[#01897b]"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            {label}
          </span>
          {!expanded && result.summary && (
            <p
              className="text-xs text-[rgba(45,70,88,0.6)] truncate mt-0.5"
              style={{ fontFamily: "'Assistant', sans-serif" }}
            >
              {result.summary}
            </p>
          )}
        </div>
        {dataEntries.length > 0 && (
          expanded
            ? <ChevronUp size={14} className="text-[#01897b] flex-shrink-0" />
            : <ChevronDown size={14} className="text-[rgba(45,70,88,0.3)] flex-shrink-0" />
        )}
      </div>
      {expanded && dataEntries.length > 0 && (
        <div className="mt-2 pt-2 border-t border-[rgba(4,196,177,0.2)] space-y-1.5">
          {dataEntries.map(([key, value]) => (
            <div key={key} className="flex gap-2 text-xs" style={{ fontFamily: "'Assistant', sans-serif" }}>
              <span className="text-[#01897b] font-semibold flex-shrink-0">
                {FIELD_LABELS[key] || key}:
              </span>
              <span className="text-[rgba(45,70,88,0.8)]">
                {formatValue(value)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
