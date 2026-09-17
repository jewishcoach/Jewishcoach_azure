import { CardShell } from '../shared/CardShell';

interface MatzuiSummaryProps {
  data?: {
    emotions?: string[];
    thought?: string;
    action?: string;
  };
  onSubmit: (toolType: string, data: { confirmed: boolean }) => void;
  isSubmitting: boolean;
}

export function MatzuiSummary({ data, onSubmit, isSubmitting }: MatzuiSummaryProps) {
  const emotions = data?.emotions?.join(', ') || '—';
  const thought = data?.thought || '—';
  const action = data?.action || '—';

  return (
    <CardShell
      titleHe="תמונת המצוי שלך"
      instructionHe="ככה נראתה התגובה שלך באותו רגע. מדויק?"
    >
      <div className="space-y-4">
        <div className="space-y-3">
          <SummaryRow label="הרגשת" value={emotions} emoji="💭" />
          <SummaryRow label="חשבת" value={`"${thought}"`} emoji="🧠" />
          <SummaryRow label="עשית" value={action} emoji="⚡" />
        </div>

        <div className="flex justify-center pt-2">
          <button
            type="button"
            disabled={isSubmitting}
            onClick={() => onSubmit('matzui_summary', { confirmed: true })}
            className="w-full max-w-[300px] h-[48px] rounded-xl bg-[#9747ff] text-white text-sm font-medium
                       hover:bg-[#8035e6] transition-colors disabled:opacity-50
                       drop-shadow-[0px_4px_2px_rgba(0,0,0,0.08)]"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            {isSubmitting ? '...' : 'זה מדויק, נמשיך'}
          </button>
        </div>
      </div>
    </CardShell>
  );
}

function SummaryRow({ label, value, emoji }: { label: string; value: string; emoji: string }) {
  return (
    <div className="flex items-start gap-3 bg-[#f6f4f0] rounded-lg p-3">
      <span className="text-lg shrink-0 mt-0.5">{emoji}</span>
      <div className="flex-1 text-right">
        <p
          className="text-[10px] font-semibold text-[#009081] uppercase tracking-wide"
          style={{ fontFamily: "'Heebo', sans-serif" }}
        >
          {label}
        </p>
        <p
          className="text-sm text-[#2d4658] leading-relaxed mt-0.5"
          style={{ fontFamily: "'Heebo', sans-serif" }}
        >
          {value}
        </p>
      </div>
    </div>
  );
}
