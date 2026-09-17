import { useState, useCallback } from 'react';
import { TagInput } from '../shared/TagInput';
import { DragList } from '../shared/DragList';

interface TraitCardBuilderProps {
  data?: {
    suggestions?: {
      source: string[];
      nature: string[];
    };
    existing_source?: string[];
    existing_nature?: string[];
  };
  onSubmit: (toolType: string, data: { source_forces: string[]; nature_forces: string[] }) => void;
  isSubmitting: boolean;
}

const MIN_TRAITS = 6;

export function TraitCardBuilder({ data, onSubmit, isSubmitting }: TraitCardBuilderProps) {
  const [source, setSource] = useState<string[]>(data?.existing_source || []);
  const [nature, setNature] = useState<string[]>(data?.existing_nature || []);

  const sourceSuggestions = data?.suggestions?.source || [];
  const natureSuggestions = data?.suggestions?.nature || [];

  const sourceMissing = Math.max(0, MIN_TRAITS - source.length);
  const natureMissing = Math.max(0, MIN_TRAITS - nature.length);
  const isReady = source.length >= MIN_TRAITS && nature.length >= MIN_TRAITS;

  const addSource = useCallback((trait: string) => {
    setSource((prev) => prev.includes(trait) ? prev : [...prev, trait]);
  }, []);

  const addNature = useCallback((trait: string) => {
    setNature((prev) => prev.includes(trait) ? prev : [...prev, trait]);
  }, []);

  const removeSource = useCallback((idx: number) => {
    setSource((prev) => prev.filter((_, i) => i !== idx));
  }, []);

  const removeNature = useCallback((idx: number) => {
    setNature((prev) => prev.filter((_, i) => i !== idx));
  }, []);

  const handleSubmit = () => {
    if (!isReady || isSubmitting) return;
    onSubmit('trait_card_builder', { source_forces: source, nature_forces: nature });
  };

  const buttonText = isSubmitting
    ? '...'
    : isReady
      ? 'סיימתי את הכרטיס'
      : `צריך עוד${sourceMissing > 0 ? ` ${sourceMissing} מקור` : ''}${sourceMissing > 0 && natureMissing > 0 ? ' ו-' : ''}${natureMissing > 0 ? `${natureMissing} טבע` : ''}`;

  return (
    <div className="space-y-5" dir="rtl">
      {/* Title */}
      <div className="text-center">
        <h3
          className="text-[28px] text-[#2d4658]"
          style={{ fontFamily: "'Karantina', cursive", lineHeight: '1.3' }}
        >
          כרטיס כוחות — מקור וטבע
        </h3>
        <p
          className="text-sm text-[rgba(45,70,88,0.6)] mt-1"
          style={{ fontFamily: "'Heebo', sans-serif" }}
        >
          בחר תכונות מההצעות או הוסף משלך. גרור לסדר — הראשון הוא המוביל
        </p>
      </div>

      {/* Two columns */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Source column */}
        <ForceColumn
          type="source"
          icon="☀️"
          title="כוחות מקור"
          subtitle="אור, ערכים, שליחות — מה שמביא לך חיים"
          bgClass="bg-[rgba(3,255,230,0.06)]"
          headerBg="bg-[rgba(3,255,230,0.1)]"
          suggestions={sourceSuggestions}
          selected={source}
          onAdd={addSource}
          onRemove={removeSource}
          onReorder={setSource}
          placeholder="הוסף תכונת מקור..."
        />

        {/* Nature column */}
        <ForceColumn
          type="nature"
          icon="🌊"
          title="כוחות טבע"
          subtitle="צרכים, הגנות, דחפים — כלי עבודה לניהול"
          bgClass="bg-[rgba(45,70,88,0.04)]"
          headerBg="bg-[rgba(45,70,88,0.08)]"
          suggestions={natureSuggestions}
          selected={nature}
          onAdd={addNature}
          onRemove={removeNature}
          onReorder={setNature}
          placeholder="הוסף תכונת טבע..."
        />
      </div>

      {/* Submit */}
      <div className="flex justify-center pt-2">
        <button
          type="button"
          disabled={!isReady || isSubmitting}
          onClick={handleSubmit}
          className={`
            w-full max-w-[300px] h-[53px] rounded-xl text-white text-base transition-all duration-200
            drop-shadow-[0px_8px_2.9px_rgba(0,0,0,0.12)]
            ${isReady
              ? 'bg-[#9747ff] hover:bg-[#8035e6]'
              : 'bg-[rgba(151,71,255,0.4)] cursor-not-allowed'}
          `}
          style={{ fontFamily: "'Heebo', sans-serif" }}
        >
          {buttonText}
        </button>
      </div>
    </div>
  );
}


interface ForceColumnProps {
  type: 'source' | 'nature';
  icon: string;
  title: string;
  subtitle: string;
  bgClass: string;
  headerBg: string;
  suggestions: string[];
  selected: string[];
  onAdd: (trait: string) => void;
  onRemove: (idx: number) => void;
  onReorder: (items: string[]) => void;
  placeholder: string;
}

function ForceColumn({
  type,
  icon,
  title,
  subtitle,
  bgClass,
  headerBg,
  suggestions,
  selected,
  onAdd,
  onRemove,
  onReorder,
  placeholder,
}: ForceColumnProps) {
  const count = selected.length;
  const isFull = count >= MIN_TRAITS;

  return (
    <div className={`rounded-xl overflow-hidden ${bgClass}`}>
      {/* Header */}
      <div className={`${headerBg} px-4 py-3`}>
        <div className="flex items-center gap-2 justify-end">
          <div className="text-right">
            <h4
              className="text-sm font-semibold text-[#2d4658]"
              style={{ fontFamily: "'Heebo', sans-serif" }}
            >
              {icon} {title}
            </h4>
            <p
              className="text-[11px] text-[rgba(45,70,88,0.5)] mt-0.5"
              style={{ fontFamily: "'Assistant', sans-serif" }}
            >
              {subtitle}
            </p>
          </div>
        </div>
        {/* Counter */}
        <div className="flex items-center gap-1.5 mt-2 justify-end">
          <span
            className={`text-xs font-semibold ${isFull ? 'text-[#009081]' : 'text-[rgba(45,70,88,0.4)]'}`}
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            {count}/{MIN_TRAITS} תכונות
          </span>
          {isFull && (
            <span className="text-xs text-[#009081]">✓</span>
          )}
        </div>
      </div>

      <div className="p-3 space-y-3">
        {/* Suggestions */}
        {suggestions.length > 0 && (
          <div>
            <p
              className="text-[10px] text-[rgba(45,70,88,0.4)] mb-1.5 text-right uppercase tracking-wider"
              style={{ fontFamily: "'Heebo', sans-serif" }}
            >
              הצעות
            </p>
            <div className="flex flex-wrap gap-1.5">
              {suggestions.map((sug) => {
                const isSelected = selected.includes(sug);
                return (
                  <button
                    key={sug}
                    type="button"
                    disabled={isSelected}
                    onClick={() => onAdd(sug)}
                    className={`
                      px-2.5 py-1 rounded-full text-xs transition-all duration-150
                      ${isSelected
                        ? 'bg-[rgba(3,255,230,0.2)] text-[rgba(45,70,88,0.3)] border border-[rgba(3,255,230,0.3)] cursor-default'
                        : 'bg-white border border-[#e0ddd8] text-[#2d4658] hover:border-[#03ffe6] hover:bg-[rgba(3,255,230,0.05)] active:scale-95'}
                    `}
                    style={{ fontFamily: "'Heebo', sans-serif" }}
                  >
                    {isSelected ? `✓ ${sug}` : `+ ${sug}`}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Custom input */}
        <TagInput
          tags={[]}
          onAdd={onAdd}
          onRemove={() => {}}
          placeholder={placeholder}
        />

        {/* Selected traits (drag-to-reorder) */}
        {selected.length > 0 && (
          <div>
            <p
              className="text-[10px] text-[rgba(45,70,88,0.4)] mb-1.5 text-right uppercase tracking-wider"
              style={{ fontFamily: "'Heebo', sans-serif" }}
            >
              {type === 'source' ? 'תכונות מקור שנבחרו' : 'תכונות טבע שנבחרו'}
            </p>
            <DragList
              items={selected}
              onReorder={onReorder}
              onRemove={onRemove}
            />
          </div>
        )}
      </div>
    </div>
  );
}
