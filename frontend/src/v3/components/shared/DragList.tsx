import { useState, useRef, type ReactNode } from 'react';

interface DragListProps {
  items: string[];
  onReorder: (newOrder: string[]) => void;
  onRemove?: (index: number) => void;
  renderItem?: (item: string, index: number) => ReactNode;
}

export function DragList({ items, onReorder, onRemove, renderItem }: DragListProps) {
  const [dragIdx, setDragIdx] = useState<number | null>(null);
  const [overIdx, setOverIdx] = useState<number | null>(null);
  const dragNode = useRef<HTMLDivElement | null>(null);

  const handleDragStart = (e: React.DragEvent, idx: number) => {
    setDragIdx(idx);
    dragNode.current = e.currentTarget as HTMLDivElement;
    e.dataTransfer.effectAllowed = 'move';
    // Make the drag image slightly transparent
    requestAnimationFrame(() => {
      if (dragNode.current) dragNode.current.style.opacity = '0.4';
    });
  };

  const handleDragEnd = () => {
    if (dragNode.current) dragNode.current.style.opacity = '1';
    if (dragIdx !== null && overIdx !== null && dragIdx !== overIdx) {
      const updated = [...items];
      const [moved] = updated.splice(dragIdx, 1);
      updated.splice(overIdx, 0, moved);
      onReorder(updated);
    }
    setDragIdx(null);
    setOverIdx(null);
    dragNode.current = null;
  };

  const handleDragOver = (e: React.DragEvent, idx: number) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setOverIdx(idx);
  };

  // Touch-based reorder: move up/down buttons as fallback
  const moveItem = (fromIdx: number, toIdx: number) => {
    if (toIdx < 0 || toIdx >= items.length) return;
    const updated = [...items];
    const [moved] = updated.splice(fromIdx, 1);
    updated.splice(toIdx, 0, moved);
    onReorder(updated);
  };

  if (items.length === 0) return null;

  return (
    <div className="space-y-1.5" dir="rtl">
      {items.map((item, idx) => {
        const isLeading = idx === 0;
        const isDragOver = overIdx === idx && dragIdx !== idx;

        return (
          <div
            key={`${item}-${idx}`}
            draggable
            onDragStart={(e) => handleDragStart(e, idx)}
            onDragEnd={handleDragEnd}
            onDragOver={(e) => handleDragOver(e, idx)}
            className={`
              flex items-center gap-2 px-3 py-2.5 rounded-lg bg-white
              border transition-all duration-150 cursor-grab active:cursor-grabbing
              ${isDragOver ? 'border-[#03ffe6] bg-[rgba(3,255,230,0.05)]' : 'border-[#e0ddd8]'}
              ${isLeading ? 'border-[#03ffe6]' : ''}
              hover:shadow-[0px_0px_4px_rgba(0,0,0,0.06)]
            `}
          >
            {/* Drag handle */}
            <span className="text-[rgba(45,70,88,0.3)] select-none flex-shrink-0 text-sm leading-none">
              ⠿
            </span>

            {/* Position number */}
            <span
              className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 text-[10px] font-semibold
                ${isLeading ? 'bg-[#03ffe6] text-[#2d4658]' : 'bg-[#f6f4f0] text-[rgba(45,70,88,0.5)]'}`}
              style={{ fontFamily: "'Heebo', sans-serif" }}
            >
              {idx + 1}
            </span>

            {/* Content */}
            <div className="flex-1 min-w-0">
              {renderItem ? renderItem(item, idx) : (
                <span
                  className="text-sm text-[#2d4658] truncate block"
                  style={{ fontFamily: "'Heebo', sans-serif" }}
                >
                  {item}
                </span>
              )}
            </div>

            {/* Leading badge */}
            {isLeading && (
              <span
                className="flex-shrink-0 px-2 py-0.5 rounded-full bg-[rgba(3,255,230,0.15)] text-[10px] font-semibold text-[#009081]"
                style={{ fontFamily: "'Heebo', sans-serif" }}
              >
                מוביל
              </span>
            )}

            {/* Touch move buttons */}
            <div className="flex flex-col gap-0.5 flex-shrink-0 lg:hidden">
              <button
                type="button"
                onClick={() => moveItem(idx, idx - 1)}
                disabled={idx === 0}
                className="w-5 h-5 flex items-center justify-center text-[10px] text-[rgba(45,70,88,0.4)] disabled:opacity-20"
              >
                ▲
              </button>
              <button
                type="button"
                onClick={() => moveItem(idx, idx + 1)}
                disabled={idx === items.length - 1}
                className="w-5 h-5 flex items-center justify-center text-[10px] text-[rgba(45,70,88,0.4)] disabled:opacity-20"
              >
                ▼
              </button>
            </div>

            {/* Remove button */}
            {onRemove && (
              <button
                type="button"
                onClick={() => onRemove(idx)}
                className="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0
                           text-[rgba(45,70,88,0.3)] hover:text-red-400 hover:bg-red-50 transition-colors"
              >
                ×
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}
