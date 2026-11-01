import { useRef, useState } from 'react';
import { CardShell } from '../shared/CardShell';
import { ChipGroup } from '../shared/ChipGroup';
import { useG } from '../shared/gender';
import { SubmitButton } from '../shared/SubmitButton';

const ALL_EMOTIONS = [
  'כעס', 'עצב', 'חרדה', 'תסכול', 'בושה', 'פחד',
  'עלבון', 'אשמה', 'אכזבה', 'בדידות', 'חוסר אונים', 'ריקנות',
];

export interface EmotionSelectorProps {
  data?: { suggested_emotions?: string[]; event_summary?: string };
  onSubmit: (toolType: string, data: { emotions: string[] }) => void;
  isSubmitting: boolean;
}

export function EmotionSelector({ data, onSubmit, isSubmitting }: EmotionSelectorProps) {
  const g = useG();
  // Build emotion list: suggested first (highlighted), then the rest
  const suggested = data?.suggested_emotions || [];
  const suggestedSet = new Set(suggested);
  const remaining = ALL_EMOTIONS.filter((e) => !suggestedSet.has(e));
  const EMOTION_OPTIONS = [
    ...suggested.map((e) => ({ id: e, label: e })),
    ...remaining.map((e) => ({ id: e, label: e })),
  ];
  const [selected, setSelected] = useState<string[]>([]);

  const handleToggle = (id: string) => {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    );
  };

  const chipsRef = useRef<HTMLDivElement>(null);
  const missing = selected.length >= 2 ? null
    : selected.length === 1 ? g('בחר עוד רגש אחד', 'בחרי עוד רגש אחד') : g('בחר לפחות 2 רגשות', 'בחרי לפחות 2 רגשות');

  return (
    <CardShell
      titleHe="מה הרגשת באותו רגע?"
      instructionHe={g('בחר לפחות 2 רגשות. אפשר גם להוסיף רגש משלך.', 'בחרי לפחות 2 רגשות. אפשר גם להוסיף רגש משלך.')}
    >
      <div className="space-y-5">
        <div ref={chipsRef} tabIndex={-1} className="rounded-xl outline-none">
        <ChipGroup
          options={EMOTION_OPTIONS}
          selected={selected}
          onToggle={handleToggle}
          multiSelect
          minSelect={2}
          allowCustom
          customPlaceholder="רגש אחר..."
        />
        </div>

        {selected.length > 0 && (
          <div className="text-right">
            <p
              className="text-xs text-[rgba(45,70,88,0.5)]"
              style={{ fontFamily: "'Heebo', sans-serif" }}
            >
              {selected.length < 2
                ? `בחרת ${selected.length} — צריך לפחות 2`
                : `בחרת ${selected.length} רגשות`}
            </p>
          </div>
        )}

        <div className="flex justify-center pt-1">
          <SubmitButton
            label="המשך"
            missing={missing}
            target={() => chipsRef.current}
            isSubmitting={isSubmitting}
            onSubmit={() => onSubmit('emotion_selector', { emotions: selected })}
            className="w-full max-w-[300px] h-[48px] rounded-xl bg-[#9747ff] text-white text-sm font-medium
                       hover:bg-[#8035e6] transition-colors
                       drop-shadow-[0px_4px_2px_rgba(0,0,0,0.08)]"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          />
        </div>
      </div>
    </CardShell>
  );
}
