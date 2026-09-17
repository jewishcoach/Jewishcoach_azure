import { useState } from 'react';
import { CardShell } from '../shared/CardShell';
import { SliderInput } from '../shared/SliderInput';
import { TriStateButton } from '../shared/TriStateButton';

interface GapCardProps {
  onSubmit: (toolType: string, data: {
    gap_name: string;
    gap_score: number;
    belief: 'yes' | 'no' | 'unsure';
    opportunity: { has: boolean; what?: string };
  }) => void;
  isSubmitting: boolean;
}

export function GapCard({ onSubmit, isSubmitting }: GapCardProps) {
  const [gapName, setGapName] = useState('');
  const [gapScore, setGapScore] = useState(5);
  const [belief, setBelief] = useState<'yes' | 'no' | 'unsure' | null>(null);
  const [opportunityAnswer, setOpportunityAnswer] = useState<'yes' | 'no' | 'unsure' | null>(null);
  const [opportunityText, setOpportunityText] = useState('');

  const canSubmit =
    gapName.trim().length > 0 &&
    belief !== null &&
    opportunityAnswer !== null &&
    (opportunityAnswer !== 'yes' || opportunityText.trim().length > 0);

  const handleSubmit = () => {
    onSubmit('gap_card', {
      gap_name: gapName.trim(),
      gap_score: gapScore,
      belief: belief!,
      opportunity: {
        has: opportunityAnswer === 'yes',
        ...(opportunityAnswer === 'yes' && opportunityText.trim() ? { what: opportunityText.trim() } : {}),
      },
    });
  };

  return (
    <CardShell
      titleHe="הפער"
      instructionHe="הפער בין מה שהיה לבין מה שהיית רוצה — נגדיר אותו, נמדוד אותו, ונבדוק מה הוא מזמן."
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

        {/* 3. Belief question */}
        <div className="space-y-2">
          <p
            className="text-sm font-medium text-[#2d4658] text-right"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            אני מאמין שאפשר לקחת את זה למקום אחר
          </p>
          <TriStateButton value={belief} onChange={setBelief} />
        </div>

        {/* 4. Opportunity question */}
        <div className="space-y-2">
          <p
            className="text-sm font-medium text-[#2d4658] text-right"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            יש כאן הזדמנות בשבילי?
          </p>
          <TriStateButton
            value={opportunityAnswer}
            onChange={setOpportunityAnswer}
            labels={{ yes: 'כן', no: 'לא', unsure: 'לא בטוח' }}
          />

          {opportunityAnswer === 'yes' && (
            <div className="pt-1">
              <input
                type="text"
                value={opportunityText}
                onChange={(e) => setOpportunityText(e.target.value)}
                placeholder="מהי ההזדמנות?"
                className="w-full h-[44px] px-3 rounded-xl border border-[#e0ddd8] text-sm text-[#2d4658] text-right
                           placeholder:text-[rgba(45,70,88,0.35)]
                           focus:outline-none focus:border-[#03ffe6] transition-colors
                           animate-[fadeIn_0.2s_ease-out]"
                style={{ fontFamily: "'Heebo', sans-serif" }}
              />
            </div>
          )}
        </div>

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
            {isSubmitting ? '...' : 'המשך לדפוס'}
          </button>
        </div>
      </div>
    </CardShell>
  );
}
