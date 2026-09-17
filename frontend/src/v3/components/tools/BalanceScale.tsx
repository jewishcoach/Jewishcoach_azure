import { useState } from 'react';
import { CardShell } from '../shared/CardShell';
import { TagInput } from '../shared/TagInput';

interface BalanceScaleProps {
  onSubmit: (toolType: string, data: { gains: string[]; losses: string[] }) => void;
  isSubmitting: boolean;
}

export function BalanceScale({ onSubmit, isSubmitting }: BalanceScaleProps) {
  const [gains, setGains] = useState<string[]>([]);
  const [losses, setLosses] = useState<string[]>([]);

  const canSubmit = gains.length >= 2 && losses.length >= 2 && !isSubmitting;

  return (
    <CardShell
      titleHe="מה אני מרוויח ומה אני מפסיד?"
      instructionHe="הוסף רווחים והפסדים מהדפוס שזיהית"
    >
      <div className="space-y-5">
        {/* Two columns — stack on mobile */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Right column: Gains */}
          <div className="space-y-3">
            <div className="bg-[rgba(3,255,230,0.08)] rounded-lg px-3 py-2">
              <h4
                className="text-sm font-semibold text-[#009081] text-right"
                style={{ fontFamily: "'Heebo', sans-serif" }}
              >
                מה אני מרוויח מהדפוס
              </h4>
            </div>
            <TagInput
              tags={gains}
              onAdd={(tag) => setGains((prev) => [...prev, tag])}
              onRemove={(idx) => setGains((prev) => prev.filter((_, i) => i !== idx))}
              placeholder="הוסף רווח..."
              minTags={2}
            />
            <p
              className="text-[11px] text-[rgba(45,70,88,0.4)] text-right"
              style={{ fontFamily: "'Heebo', sans-serif" }}
            >
              {gains.length} פריטים
            </p>
          </div>

          {/* Left column: Losses */}
          <div className="space-y-3">
            <div className="bg-[rgba(220,80,80,0.06)] rounded-lg px-3 py-2">
              <h4
                className="text-sm font-semibold text-[#c04040] text-right"
                style={{ fontFamily: "'Heebo', sans-serif" }}
              >
                מה אני מפסיד מהדפוס
              </h4>
            </div>
            <TagInput
              tags={losses}
              onAdd={(tag) => setLosses((prev) => [...prev, tag])}
              onRemove={(idx) => setLosses((prev) => prev.filter((_, i) => i !== idx))}
              placeholder="הוסף הפסד..."
              minTags={2}
            />
            <p
              className="text-[11px] text-[rgba(45,70,88,0.4)] text-right"
              style={{ fontFamily: "'Heebo', sans-serif" }}
            >
              {losses.length} פריטים
            </p>
          </div>
        </div>

        {/* Scale metaphor — subtle visual */}
        <div className="flex items-center justify-center gap-3 py-1">
          <span className="text-xs text-[rgba(45,70,88,0.3)]" style={{ fontFamily: "'Heebo', sans-serif" }}>
            {gains.length} רווחים
          </span>
          <span className="text-lg text-[rgba(3,255,230,0.4)]">⚖</span>
          <span className="text-xs text-[rgba(45,70,88,0.3)]" style={{ fontFamily: "'Heebo', sans-serif" }}>
            {losses.length} הפסדים
          </span>
        </div>

        {/* Submit */}
        <div className="flex justify-center pt-2">
          <button
            type="button"
            disabled={!canSubmit}
            onClick={() => onSubmit('balance_scale', { gains, losses })}
            className="px-8 h-[53px] rounded-xl bg-[#9747ff] text-white text-base
                       hover:bg-[#8035e6] transition-colors disabled:opacity-50
                       drop-shadow-[0px_8px_2.9px_rgba(0,0,0,0.12)]"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            {isSubmitting ? '...' : canSubmit ? 'סיימתי את המאזן' : `צריך עוד ${Math.max(0, 2 - gains.length)} רווחים ו-${Math.max(0, 2 - losses.length)} הפסדים`}
          </button>
        </div>
      </div>
    </CardShell>
  );
}
