import { useState } from 'react';
import { CardShell } from '../shared/CardShell';

interface EventFormProps {
  onSubmit: (toolType: string, data: { when: string; with_whom: string; what_happened: string }) => void;
  isSubmitting: boolean;
}

export function EventForm({ onSubmit, isSubmitting }: EventFormProps) {
  const [when, setWhen] = useState('');
  const [withWhom, setWithWhom] = useState('');
  const [whatHappened, setWhatHappened] = useState('');

  const canSubmit = when.trim() && withWhom.trim() && whatHappened.trim().length >= 5;

  return (
    <CardShell
      titleHe="האירוע"
      instructionHe="ספר על אירוע ספציפי — שיחה או אינטראקציה שהתרחשה לאחרונה, עם אנשים אחרים."
    >
      <div className="space-y-4">
        <div>
          <label
            className="block text-sm font-medium text-[#2d4658] text-right mb-1"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            מתי זה קרה?
          </label>
          <input
            type="text"
            value={when}
            onChange={(e) => setWhen(e.target.value)}
            placeholder="למשל: אתמול בערב, לפני שבוע..."
            className="w-full h-[44px] px-3 rounded-xl border border-[#e0ddd8] text-sm text-[#2d4658] text-right
                       placeholder:text-[rgba(45,70,88,0.35)]
                       focus:outline-none focus:border-[#03ffe6] transition-colors"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          />
        </div>

        <div>
          <label
            className="block text-sm font-medium text-[#2d4658] text-right mb-1"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            עם מי?
          </label>
          <input
            type="text"
            value={withWhom}
            onChange={(e) => setWithWhom(e.target.value)}
            placeholder="למשל: בן/בת הזוג, הבוס, חבר..."
            className="w-full h-[44px] px-3 rounded-xl border border-[#e0ddd8] text-sm text-[#2d4658] text-right
                       placeholder:text-[rgba(45,70,88,0.35)]
                       focus:outline-none focus:border-[#03ffe6] transition-colors"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          />
        </div>

        <div>
          <label
            className="block text-sm font-medium text-[#2d4658] text-right mb-1"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            ספר בקצרה מה קרה (2-3 משפטים)
          </label>
          <textarea
            value={whatHappened}
            onChange={(e) => setWhatHappened(e.target.value)}
            placeholder="מה קרה שם? מה נאמר או נעשה?"
            rows={3}
            className="w-full px-3 py-2.5 rounded-xl border border-[#e0ddd8] text-sm text-[#2d4658] text-right
                       placeholder:text-[rgba(45,70,88,0.35)] resize-none
                       focus:outline-none focus:border-[#03ffe6] transition-colors"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          />
        </div>

        <div className="flex justify-center pt-2">
          <button
            type="button"
            disabled={!canSubmit || isSubmitting}
            onClick={() => onSubmit('event_form', { when, with_whom: withWhom, what_happened: whatHappened })}
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
