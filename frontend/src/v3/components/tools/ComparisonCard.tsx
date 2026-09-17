import { useState } from 'react';
import { CardShell } from '../shared/CardShell';

interface ComparisonCardProps {
  data?: {
    emotions?: string[];
    thought?: string;
    action_actual?: string;
  };
  onSubmit: (toolType: string, data: { emotion_desired: string; thought_desired: string; action_desired: string }) => void;
  isSubmitting: boolean;
}

export function ComparisonCard({ data, onSubmit, isSubmitting }: ComparisonCardProps) {
  const [emotionDesired, setEmotionDesired] = useState('');
  const [thoughtDesired, setThoughtDesired] = useState('');
  const [actionDesired, setActionDesired] = useState('');

  const canSubmit = emotionDesired.trim() && thoughtDesired.trim() && actionDesired.trim();

  const matzuiEmotions = data?.emotions?.join(', ') || '—';
  const matzuiThought = data?.thought || '—';
  const matzuiAction = data?.action_actual || '—';

  return (
    <CardShell
      titleHe="באותו רגע בדיוק — מה היית רוצה?"
      instructionHe="נשארים באותה סיטואציה. השינוי הוא בך — איך היית רוצה להרגיש, לחשוב ולפעול."
    >
      <div className="space-y-4">
        {/* Desktop: two columns, Mobile: stacked */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Left column: Matzui (read-only) */}
          <div className="space-y-3 order-2 sm:order-1">
            <h4
              className="text-xs font-bold uppercase tracking-wider text-[rgba(45,70,88,0.5)] text-right"
              style={{ fontFamily: "'Heebo', sans-serif" }}
            >
              מה שהיה (מצוי)
            </h4>
            <ReadOnlyField label="הרגשתי" value={matzuiEmotions} />
            <ReadOnlyField label="חשבתי" value={matzuiThought} />
            <ReadOnlyField label="עשיתי" value={matzuiAction} />
          </div>

          {/* Right column: Ratzui (editable) */}
          <div className="space-y-3 order-1 sm:order-2">
            <h4
              className="text-xs font-bold uppercase tracking-wider text-[#009081] text-right"
              style={{ fontFamily: "'Heebo', sans-serif" }}
            >
              מה שהייתי רוצה (רצוי)
            </h4>
            <EditableField
              label="הייתי רוצה להרגיש"
              value={emotionDesired}
              onChange={setEmotionDesired}
              placeholder="איזה רגש?"
            />
            <EditableField
              label="הייתי רוצה לומר לעצמי"
              value={thoughtDesired}
              onChange={setThoughtDesired}
              placeholder="איזו אמירה פנימית?"
            />
            <EditableField
              label="הייתי רוצה לעשות"
              value={actionDesired}
              onChange={setActionDesired}
              placeholder="איזו פעולה?"
            />
          </div>
        </div>

        <div className="flex justify-center pt-2">
          <button
            type="button"
            disabled={!canSubmit || isSubmitting}
            onClick={() => onSubmit('comparison_card', {
              emotion_desired: emotionDesired.trim(),
              thought_desired: thoughtDesired.trim(),
              action_desired: actionDesired.trim(),
            })}
            className="w-full max-w-[300px] h-[48px] rounded-xl bg-[#9747ff] text-white text-sm font-medium
                       hover:bg-[#8035e6] transition-colors disabled:opacity-50
                       drop-shadow-[0px_4px_2px_rgba(0,0,0,0.08)]"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            {isSubmitting ? '...' : 'המשך'}
          </button>
        </div>
      </div>
    </CardShell>
  );
}

function ReadOnlyField({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-[#f6f4f0] rounded-lg p-3 text-right">
      <p
        className="text-[10px] font-medium text-[rgba(45,70,88,0.4)] uppercase tracking-wide"
        style={{ fontFamily: "'Heebo', sans-serif" }}
      >
        {label}
      </p>
      <p
        className="text-sm text-[#2d4658] mt-0.5"
        style={{ fontFamily: "'Heebo', sans-serif" }}
      >
        {value}
      </p>
    </div>
  );
}

function EditableField({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
}) {
  return (
    <div className="text-right">
      <p
        className="text-[10px] font-medium text-[#009081] uppercase tracking-wide mb-1"
        style={{ fontFamily: "'Heebo', sans-serif" }}
      >
        {label}
      </p>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full h-[40px] px-3 rounded-lg border border-[#e0ddd8] text-sm text-[#2d4658] text-right
                   placeholder:text-[rgba(45,70,88,0.3)]
                   focus:outline-none focus:border-[#03ffe6] transition-colors"
        style={{ fontFamily: "'Heebo', sans-serif" }}
      />
    </div>
  );
}
