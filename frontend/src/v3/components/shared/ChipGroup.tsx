import { useState } from 'react';

interface ChipOption {
  id: string;
  label: string;
}

interface ChipGroupProps {
  options: ChipOption[];
  selected: string[];
  onToggle: (id: string) => void;
  multiSelect: boolean;
  minSelect?: number;
  allowCustom?: boolean;
  customPlaceholder?: string;
}

export function ChipGroup({
  options,
  selected,
  onToggle,
  multiSelect,
  allowCustom,
  customPlaceholder = 'הקלד כאן...',
}: ChipGroupProps) {
  const [customOpen, setCustomOpen] = useState(false);
  const [customText, setCustomText] = useState('');

  const handleCustomAdd = () => {
    const trimmed = customText.trim();
    if (trimmed) {
      onToggle(trimmed);
      setCustomText('');
      setCustomOpen(false);
    }
  };

  return (
    <div className="flex flex-wrap gap-2" dir="rtl">
      {options.map((opt) => {
        const isSelected = selected.includes(opt.id);
        return (
          <button
            key={opt.id}
            type="button"
            onClick={() => {
              if (!multiSelect && !isSelected) {
                onToggle(opt.id);
              } else if (multiSelect) {
                onToggle(opt.id);
              }
            }}
            className={`
              h-[42px] px-4 rounded-xl text-sm transition-all duration-200
              ${isSelected
                ? 'border-[1.5px] border-[#04c4b1] bg-[rgba(3,255,230,0.3)] text-[#2d4658] font-medium'
                : 'border border-[#d2d2d2] bg-white text-[#2d4658] hover:border-[#03ffe6] hover:bg-[rgba(3,255,230,0.05)]'
              }
            `}
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            {opt.label}
          </button>
        );
      })}

      {allowCustom && !customOpen && (
        <button
          type="button"
          onClick={() => setCustomOpen(true)}
          className="h-[42px] px-4 rounded-xl text-sm border border-dashed border-[#d2d2d2] bg-white text-[rgba(45,70,88,0.5)] hover:border-[#03ffe6] transition-colors"
          style={{ fontFamily: "'Heebo', sans-serif" }}
        >
          + אחר
        </button>
      )}

      {allowCustom && customOpen && (
        <div className="flex items-center gap-2 w-full mt-1">
          <input
            type="text"
            value={customText}
            onChange={(e) => setCustomText(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleCustomAdd(); }}
            placeholder={customPlaceholder}
            autoFocus
            className="flex-1 h-[42px] px-3 rounded-xl border border-[#e0ddd8] text-sm text-[#2d4658] text-right
                       focus:outline-none focus:border-[#03ffe6] transition-colors"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          />
          <button
            type="button"
            onClick={handleCustomAdd}
            disabled={!customText.trim()}
            className="h-[42px] px-4 rounded-xl bg-[#03ffe6] text-[#2d4658] text-sm font-medium disabled:opacity-40 transition-colors"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            הוסף
          </button>
          <button
            type="button"
            onClick={() => { setCustomOpen(false); setCustomText(''); }}
            className="h-[42px] px-3 rounded-xl text-sm text-[rgba(45,70,88,0.5)] hover:text-[#2d4658] transition-colors"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            ביטול
          </button>
        </div>
      )}
    </div>
  );
}
