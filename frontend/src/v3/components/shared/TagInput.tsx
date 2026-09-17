import { useState, useRef } from 'react';

interface TagInputProps {
  tags: string[];
  onAdd: (tag: string) => void;
  onRemove: (index: number) => void;
  placeholder: string;
  minTags?: number;
}

export function TagInput({ tags, onAdd, onRemove, placeholder, minTags }: TagInputProps) {
  const [value, setValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const handleAdd = () => {
    const trimmed = value.trim();
    if (!trimmed) return;
    if (tags.includes(trimmed)) return;
    onAdd(trimmed);
    setValue('');
    inputRef.current?.focus();
  };

  return (
    <div className="space-y-2" dir="rtl">
      <div className="flex gap-2">
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              handleAdd();
            }
          }}
          placeholder={placeholder}
          className="flex-1 min-w-0 px-3 py-2 rounded-lg border border-[#e0ddd8] text-sm text-[#2d4658] text-right
                     focus:outline-none focus:border-[#03ffe6] transition-colors"
          style={{ fontFamily: "'Heebo', sans-serif" }}
        />
        <button
          type="button"
          onClick={handleAdd}
          disabled={!value.trim()}
          className="px-3 py-2 rounded-lg bg-[rgba(3,255,230,0.15)] text-[#2d4658] text-sm font-medium
                     hover:bg-[rgba(3,255,230,0.3)] transition-colors disabled:opacity-30"
          style={{ fontFamily: "'Heebo', sans-serif" }}
        >
          הוסף
        </button>
      </div>

      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {tags.map((tag, idx) => (
            <span
              key={`${tag}-${idx}`}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full
                         bg-[rgba(3,255,230,0.12)] border border-[#03ffe6]
                         text-xs text-[#2d4658]"
              style={{ fontFamily: "'Heebo', sans-serif" }}
            >
              {tag}
              <button
                type="button"
                onClick={() => onRemove(idx)}
                className="w-4 h-4 rounded-full flex items-center justify-center
                           hover:bg-[rgba(45,70,88,0.1)] transition-colors text-[rgba(45,70,88,0.5)]"
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}

      {minTags != null && tags.length < minTags && tags.length > 0 && (
        <p className="text-[11px] text-[rgba(45,70,88,0.4)]" style={{ fontFamily: "'Heebo', sans-serif" }}>
          {`צריך עוד ${minTags - tags.length}`}
        </p>
      )}
    </div>
  );
}
