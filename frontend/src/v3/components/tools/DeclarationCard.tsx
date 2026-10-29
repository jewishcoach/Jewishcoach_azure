import { useState } from 'react';
import { CardShell } from '../shared/CardShell';
import { useG } from '../shared/gender';
import { AutoTextarea } from '../shared/AutoTextarea';

interface DeclarationCardProps {
  data?: { old_pattern?: string; old_paradigm?: string; old_stance?: string };
  onSubmit: (toolType: string, data: {
    renewal: string;
    next_action: string;
    feels_right: boolean;
  }) => void;
  isSubmitting: boolean;
}

export function DeclarationCard({ data, onSubmit, isSubmitting }: DeclarationCardProps) {
  const g = useG();
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
      instructionHe={g('הגיע הזמן לבחור מה מחליף את הישן: מה אתה מאמין מעכשיו, ואיך תפעל אחרת.', 'הגיע הזמן לבחור מה מחליף את הישן: מה את מאמינה מעכשיו, ואיך תפעלי אחרת.')}
    >
      <div className="space-y-5">
        {/* Old vs new context — the choice faces the old stance (booklet: בחירת עמדה חדשה) */}
        {data && (data.old_stance || data.old_pattern) && (
          <div className="bg-[#f6f4f0] rounded-lg p-3 space-y-1 border border-[#e0ddd8]">
            <p
              className="text-[10px] font-bold uppercase tracking-wider text-[rgba(45,70,88,0.5)]"
              style={{ fontFamily: "'Heebo', sans-serif" }}
            >
              מה היה עד עכשיו
            </p>
            {data.old_stance && (
              <p className="text-xs text-[rgba(45,70,88,0.7)]" style={{ fontFamily: "'Heebo', sans-serif" }}>
                <span className="font-semibold">העמדה הישנה:</span> {data.old_stance}
              </p>
            )}
            {data.old_pattern && (
              <p className="text-xs text-[rgba(45,70,88,0.7)]" style={{ fontFamily: "'Heebo', sans-serif" }}>
                <span className="font-semibold">הדפוס הישן:</span> {data.old_pattern}
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
            {g('העמדה החדשה שאני בוחר — אני מאמין ש…', 'העמדה החדשה שאני בוחרת — אני מאמינה ש…')}
          </label>
          <AutoTextarea
            value={renewal}
            onChange={(e) => setRenewal(e.target.value)}
            placeholder="תפיסה חדשה, במשפט קצר ובמילים שלך"
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
            {g('מה תעשה אחרת בפעם הבאה?', 'מה תעשי אחרת בפעם הבאה?')}
          </label>
          <AutoTextarea
            value={nextAction}
            onChange={(e) => setNextAction(e.target.value)}
            placeholder={g('תאר פעולה קונקרטית', 'תארי פעולה קונקרטית')}
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
            {g('האם זה מרגיש כמו אתה? זה משמח אותך?', 'האם זה מרגיש כמו את? זה משמח אותך?')}
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
              bg-[#9747ff] hover:bg-[#8035e6]
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
