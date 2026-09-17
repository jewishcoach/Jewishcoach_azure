import { useState } from 'react';
import { CardShell } from '../shared/CardShell';

interface DeclarationCardProps {
  data?: { old_pattern?: string; old_paradigm?: string };
  onSubmit: (toolType: string, data: {
    renewal: string;
    next_action: string;
    feels_right: boolean;
  }) => void;
  isSubmitting: boolean;
}

export function DeclarationCard({ data, onSubmit, isSubmitting }: DeclarationCardProps) {
  const [renewal, setRenewal] = useState('');
  const [nextAction, setNextAction] = useState('');
  const [feelsRight, setFeelsRight] = useState<boolean | null>(null);

  const canSubmit = renewal.trim().length > 0 && nextAction.trim().length > 0 && feelsRight !== null;

  const handleSubmit = () => {
    onSubmit('declaration_card', {
      renewal: renewal.trim(),
      next_action: nextAction.trim(),
      feels_right: feelsRight!,
    });
  };

  return (
    <CardShell
      titleHe="הבחירה החדשה שלך"
      instructionHe="הגיע הזמן לבחור מה מחליף את הישן. כתוב את האמונה החדשה שלך, ואיך תפעל אחרת."
    >
      <div className="space-y-5">
        {/* Old vs new context */}
        {data && (data.old_pattern || data.old_paradigm) && (
          <div className="bg-[#f6f4f0] rounded-lg p-3 space-y-1 border border-[#e0ddd8]">
            <p
              className="text-[10px] font-bold uppercase tracking-wider text-[rgba(45,70,88,0.5)]"
              style={{ fontFamily: "'Heebo', sans-serif" }}
            >
              מה היה עד עכשיו
            </p>
            {data.old_pattern && (
              <p className="text-xs text-[rgba(45,70,88,0.7)]" style={{ fontFamily: "'Heebo', sans-serif" }}>
                <span className="font-semibold">הדפוס הישן:</span> {data.old_pattern}
              </p>
            )}
            {data.old_paradigm && (
              <p className="text-xs text-[rgba(45,70,88,0.7)]" style={{ fontFamily: "'Heebo', sans-serif" }}>
                <span className="font-semibold">האמונה הישנה:</span> {data.old_paradigm}
              </p>
            )}
          </div>
        )}

        {/* Divider arrow */}
        <div className="flex justify-center">
          <div className="w-8 h-8 rounded-full bg-[rgba(3,255,230,0.15)] flex items-center justify-center">
            <span className="text-[#03ffe6] text-sm">↓</span>
          </div>
        </div>

        {/* New declaration */}
        <div>
          <label
            className="block text-sm font-medium text-[#2d4658] text-right mb-1"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            אני מאמין ש...
          </label>
          <textarea
            value={renewal}
            onChange={(e) => setRenewal(e.target.value)}
            placeholder="כתוב את האמונה החדשה שלך"
            rows={2}
            className="w-full px-3 py-2.5 rounded-xl border border-[#e0ddd8] text-sm text-[#2d4658] text-right
                       placeholder:text-[rgba(45,70,88,0.35)] resize-none
                       focus:outline-none focus:border-[#03ffe6] transition-colors"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          />
        </div>

        {/* Next action */}
        <div>
          <label
            className="block text-sm font-medium text-[#2d4658] text-right mb-1"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            מה תעשה אחרת בפעם הבאה?
          </label>
          <textarea
            value={nextAction}
            onChange={(e) => setNextAction(e.target.value)}
            placeholder="תאר פעולה קונקרטית"
            rows={2}
            className="w-full px-3 py-2.5 rounded-xl border border-[#e0ddd8] text-sm text-[#2d4658] text-right
                       placeholder:text-[rgba(45,70,88,0.35)] resize-none
                       focus:outline-none focus:border-[#03ffe6] transition-colors"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          />
        </div>

        {/* Joy check */}
        <div className="space-y-2">
          <p
            className="text-sm font-medium text-[#2d4658] text-right"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            האם זה מרגיש כמו אתה? זה משמח אותך?
          </p>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => setFeelsRight(true)}
              className={`
                flex-1 h-[44px] rounded-xl text-sm font-medium transition-all duration-200
                ${feelsRight === true
                  ? 'bg-[rgba(3,255,230,0.3)] border-[#04c4b1] border text-[#2d4658]'
                  : 'bg-white border border-[#d2d2d2] text-[rgba(45,70,88,0.6)] hover:border-[#03ffe6]'
                }
              `}
              style={{ fontFamily: "'Heebo', sans-serif" }}
            >
              כן, זה אני!
            </button>
            <button
              type="button"
              onClick={() => setFeelsRight(false)}
              className={`
                flex-1 h-[44px] rounded-xl text-sm font-medium transition-all duration-200
                ${feelsRight === false
                  ? 'bg-[rgba(255,200,200,0.3)] border-[#e0a0a0] border text-[#2d4658]'
                  : 'bg-white border border-[#d2d2d2] text-[rgba(45,70,88,0.6)] hover:border-[#e0a0a0]'
                }
              `}
              style={{ fontFamily: "'Heebo', sans-serif" }}
            >
              עוד לא בדיוק
            </button>
          </div>
        </div>

        {/* Submit */}
        <div className="flex justify-center pt-2">
          <button
            type="button"
            disabled={!canSubmit || isSubmitting}
            onClick={handleSubmit}
            className={`
              w-full max-w-[300px] h-[48px] rounded-xl text-white text-sm font-medium
              transition-colors disabled:opacity-50
              drop-shadow-[0px_4px_2px_rgba(0,0,0,0.08)]
              ${feelsRight
                ? 'bg-[#9747ff] hover:bg-[#8035e6]'
                : 'bg-[#6b6b6b] hover:bg-[#555]'
              }
            `}
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            {isSubmitting ? '...' : feelsRight ? 'זו הבחירה שלי' : 'שלח בכל זאת'}
          </button>
        </div>
      </div>
    </CardShell>
  );
}
