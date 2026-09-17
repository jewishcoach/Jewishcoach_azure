import { useState } from 'react';
import { CardShell } from '../shared/CardShell';

interface ActionFieldProps {
  onSubmit: (toolType: string, data: { action_actual: string }) => void;
  isSubmitting: boolean;
}

export function ActionField({ onSubmit, isSubmitting }: ActionFieldProps) {
  const [action, setAction] = useState('');

  const canSubmit = action.trim().length >= 3;

  return (
    <CardShell
      titleHe="מה עשית?"
      instructionHe="תאר את הפעולה שעשית בפועל — משהו שאפשר לראות מבחוץ."
    >
      <div className="space-y-3">
        <textarea
          value={action}
          onChange={(e) => setAction(e.target.value)}
          placeholder="מה עשית בפועל? (פעולה שאפשר לראות מבחוץ — למשל: 'קמתי ויצאתי בלי מילה')"
          rows={2}
          className="w-full px-3 py-2.5 rounded-xl border border-[#e0ddd8] text-sm text-[#2d4658] text-right
                     placeholder:text-[rgba(45,70,88,0.35)] resize-none
                     focus:outline-none focus:border-[#03ffe6] transition-colors"
          style={{ fontFamily: "'Heebo', sans-serif" }}
        />

        <p
          className="text-xs text-[rgba(45,70,88,0.4)] text-right"
          style={{ fontFamily: "'Assistant', sans-serif" }}
        >
          תאר פעולה נצפית, לא פרשנות (לא &quot;ויתרתי&quot; אלא &quot;שתקתי ויצאתי מהחדר&quot;)
        </p>

        <div className="flex justify-center pt-1">
          <button
            type="button"
            disabled={!canSubmit || isSubmitting}
            onClick={() => onSubmit('action_field', { action_actual: action.trim() })}
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
