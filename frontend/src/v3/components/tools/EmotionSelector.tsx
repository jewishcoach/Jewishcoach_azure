import { useState } from 'react';
import { CardShell } from '../shared/CardShell';
import { ChipGroup } from '../shared/ChipGroup';

const EMOTION_OPTIONS = [
  { id: 'כעס', label: 'כעס' },
  { id: 'עצב', label: 'עצב' },
  { id: 'חרדה', label: 'חרדה' },
  { id: 'תסכול', label: 'תסכול' },
  { id: 'בושה', label: 'בושה' },
  { id: 'פחד', label: 'פחד' },
  { id: 'עלבון', label: 'עלבון' },
  { id: 'אשמה', label: 'אשמה' },
  { id: 'אכזבה', label: 'אכזבה' },
  { id: 'בדידות', label: 'בדידות' },
  { id: 'חוסר אונים', label: 'חוסר אונים' },
  { id: 'ריקנות', label: 'ריקנות' },
];

interface EmotionSelectorProps {
  onSubmit: (toolType: string, data: { emotions: string[] }) => void;
  isSubmitting: boolean;
}

export function EmotionSelector({ onSubmit, isSubmitting }: EmotionSelectorProps) {
  const [selected, setSelected] = useState<string[]>([]);

  const handleToggle = (id: string) => {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    );
  };

  const canSubmit = selected.length >= 2;

  return (
    <CardShell
      titleHe="מה הרגשת באותו רגע?"
      instructionHe="בחר לפחות 2 רגשות. אפשר גם להוסיף רגש משלך."
    >
      <div className="space-y-5">
        <ChipGroup
          options={EMOTION_OPTIONS}
          selected={selected}
          onToggle={handleToggle}
          multiSelect
          minSelect={2}
          allowCustom
          customPlaceholder="רגש אחר..."
        />

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
          <button
            type="button"
            disabled={!canSubmit || isSubmitting}
            onClick={() => onSubmit('emotion_selector', { emotions: selected })}
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
