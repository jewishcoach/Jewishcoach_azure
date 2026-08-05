interface OptionChipProps {
  label: string;
  emoji?: string;
  selected: boolean;
  onToggle: () => void;
}

export function OptionChip({ label, emoji, selected, onToggle }: OptionChipProps) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className={`
        px-4 py-3 rounded-xl border text-base transition-all duration-200
        ${
          selected
            ? 'border-[#04c4b1] bg-[rgba(3,255,230,0.3)] text-[#2d4658]'
            : 'border-[#d2d2d2] bg-[rgba(255,255,255,0.3)] text-[#2d4658] hover:border-[#04c4b1]'
        }
      `}
      style={{ fontFamily: "'Heebo', sans-serif" }}
    >
      {emoji && <span className="me-1.5">{emoji}</span>}
      {label}
    </button>
  );
}
