import { useState } from 'react';
import { CardShell } from '../shared/CardShell';
import { SliderInput } from '../shared/SliderInput';

interface GapCardProps {
  // The card only names and measures the gap. The booklet's belief and opportunity questions (p.13) are
  // asked by the coach in the chat, where he can deepen — a checkbox here skipped that exploration.
  onSubmit: (toolType: string, data: { gap_name: string; gap_score: number }) => void;
  isSubmitting: boolean;
}

export function GapCard({ onSubmit, isSubmitting }: GapCardProps) {
  const [gapName, setGapName] = useState('');
  const [gapScore, setGapScore] = useState(5);

  const canSubmit = gapName.trim().length > 0;

  const handleSubmit = () => {
    onSubmit('gap_card', { gap_name: gapName.trim(), gap_score: gapScore });
  };

  return (
    <CardShell
      titleHe="הפער"
      instructionHe="הפער בין מה שהיה לבין מה שהיית רוצה — נגדיר אותו ונמדוד אותו. אחר כך נתבונן בו יחד."
    >
      <div className="space-y-6">
        {/* 1. Gap name */}
        <div>
          <label
            className="block text-sm font-medium text-[#2d4658] text-right mb-1"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            איך תקרא לפער הזה? (1-2 מילים)
          </label>
          <input
            type="text"
            value={gapName}
            onChange={(e) => setGapName(e.target.value)}
            placeholder="למשל: ביטול עצמי, פחד מדחייה..."
            className="w-full h-[44px] px-3 rounded-xl border border-[#e0ddd8] text-sm text-[#2d4658] text-right
                       placeholder:text-[rgba(45,70,88,0.35)]
                       focus:outline-none focus:border-[#03ffe6] transition-colors"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          />
        </div>

        {/* 2. Gap score slider */}
        <SliderInput
          value={gapScore}
          onChange={setGapScore}
          label="מה עוצמת הפער?"
        />

        {/* Submit */}
        <div className="flex justify-center pt-2">
          <button
            type="button"
            disabled={!canSubmit || isSubmitting}
            onClick={handleSubmit}
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
