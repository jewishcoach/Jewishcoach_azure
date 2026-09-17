import { CheckCircle } from 'lucide-react';
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

interface CompletedToolCardProps {
  result: CompletedToolResult;
}

export function CompletedToolCard({ result }: CompletedToolCardProps) {
  const label = TOOL_LABELS[result.tool_type] || result.tool_type;

  return (
    <div
      dir="rtl"
      className="flex items-center gap-3 px-4 py-2.5 rounded-xl bg-[#f6f4f0] border border-[#e0ddd8] w-full max-w-[662px]"
    >
      <CheckCircle size={16} className="text-[#01897b] flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <span
          className="text-xs font-semibold text-[#01897b]"
          style={{ fontFamily: "'Heebo', sans-serif" }}
        >
          {label}
        </span>
        {result.summary && (
          <p
            className="text-xs text-[rgba(45,70,88,0.6)] truncate mt-0.5"
            style={{ fontFamily: "'Assistant', sans-serif" }}
          >
            {result.summary}
          </p>
        )}
      </div>
    </div>
  );
}
