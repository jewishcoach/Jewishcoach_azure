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
        px-4 py-3 rounded-2xl border-2 text-sm font-medium transition-all duration-200
        ${
          selected
            ? 'border-teal-400 bg-teal-50 text-teal-800 shadow-sm'
            : 'border-gray-200 bg-white text-gray-700 hover:border-teal-200 hover:bg-teal-50/30'
        }
      `}
    >
      {emoji && <span className="me-1.5">{emoji}</span>}
      {label}
    </button>
  );
}
