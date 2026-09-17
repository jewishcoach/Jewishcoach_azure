import { useCallback } from 'react';

interface SliderInputProps {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  label?: string;
}

export function SliderInput({ value, onChange, min = 1, max = 10, label }: SliderInputProps) {
  const steps = max - min + 1;
  const pct = ((value - min) / (max - min)) * 100;

  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const rect = e.currentTarget.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const ratio = x / rect.width;
      const raw = min + ratio * (max - min);
      onChange(Math.round(Math.min(max, Math.max(min, raw))));
    },
    [min, max, onChange],
  );

  return (
    <div className="space-y-2" dir="ltr">
      {label && (
        <p
          className="text-sm font-medium text-[#2d4658] text-right"
          dir="rtl"
          style={{ fontFamily: "'Heebo', sans-serif" }}
        >
          {label}
        </p>
      )}

      {/* Value display */}
      <div className="flex justify-center">
        <span
          className="text-3xl font-bold text-[#03ffe6]"
          style={{ fontFamily: "'Heebo', sans-serif" }}
        >
          {value}
        </span>
      </div>

      {/* Track */}
      <div
        className="relative h-[28px] flex items-center cursor-pointer select-none"
        onClick={handleClick}
      >
        {/* Background track */}
        <div className="absolute inset-x-0 h-[6px] rounded-full bg-[#e0ddd8] top-1/2 -translate-y-1/2" />

        {/* Filled portion */}
        <div
          className="absolute h-[6px] rounded-full bg-[#03ffe6] top-1/2 -translate-y-1/2 left-0"
          style={{ width: `${pct}%` }}
        />

        {/* Thumb */}
        <div
          className="absolute w-[24px] h-[24px] rounded-full bg-[#03ffe6] shadow-[0px_2px_4px_rgba(0,0,0,0.2)] top-1/2 -translate-y-1/2 -translate-x-1/2 transition-[left] duration-100"
          style={{ left: `${pct}%` }}
        />
      </div>

      {/* Tick labels */}
      <div className="flex justify-between px-[2px]">
        {Array.from({ length: steps }, (_, i) => {
          const v = min + i;
          return (
            <button
              key={v}
              type="button"
              onClick={() => onChange(v)}
              className={`text-xs w-[20px] text-center transition-colors ${
                v === value ? 'text-[#03ffe6] font-bold' : 'text-[rgba(45,70,88,0.4)]'
              }`}
              style={{ fontFamily: "'Heebo', sans-serif" }}
            >
              {v}
            </button>
          );
        })}
      </div>
    </div>
  );
}
