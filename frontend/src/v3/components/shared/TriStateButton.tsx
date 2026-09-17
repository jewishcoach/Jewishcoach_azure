interface TriStateButtonProps {
  value: 'yes' | 'no' | 'unsure' | null;
  onChange: (value: 'yes' | 'no' | 'unsure') => void;
  labels?: { yes: string; no: string; unsure: string };
}

const DEFAULT_LABELS = { yes: 'כן', no: 'לא', unsure: 'לא בטוח' };

export function TriStateButton({ value, onChange, labels }: TriStateButtonProps) {
  const l = labels || DEFAULT_LABELS;
  const options: { key: 'yes' | 'no' | 'unsure'; label: string }[] = [
    { key: 'yes', label: l.yes },
    { key: 'no', label: l.no },
    { key: 'unsure', label: l.unsure },
  ];

  return (
    <div className="flex gap-2" dir="rtl">
      {options.map((opt) => {
        const isSelected = value === opt.key;
        return (
          <button
            key={opt.key}
            type="button"
            onClick={() => onChange(opt.key)}
            className={`
              flex-1 h-[40px] rounded-xl text-sm font-medium transition-all duration-200
              ${isSelected
                ? 'bg-[rgba(3,255,230,0.3)] border-[#04c4b1] border text-[#2d4658]'
                : 'bg-white border border-[#d2d2d2] text-[rgba(45,70,88,0.6)] hover:border-[#03ffe6]'
              }
            `}
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
