import { useState } from 'react';
import type { IntroQuestion } from '../types';
import { OptionChip } from './OptionChip';

interface IntroQuestionCardProps {
  question: IntroQuestion;
  selectedOptions: string[];
  onSelectionChange: (questionId: string, optionIds: string[]) => void;
}

export function IntroQuestionCard({
  question,
  selectedOptions,
  onSelectionChange,
}: IntroQuestionCardProps) {
  const [freeText, setFreeText] = useState('');

  const handleToggle = (optionId: string) => {
    let updated: string[];
    if (question.multi_select) {
      updated = selectedOptions.includes(optionId)
        ? selectedOptions.filter((id) => id !== optionId)
        : [...selectedOptions, optionId];
    } else {
      updated = selectedOptions.includes(optionId) ? [] : [optionId];
    }
    onSelectionChange(question.id, updated);
  };

  const handleFreeTextSubmit = () => {
    if (!freeText.trim()) return;
    const freeId = `free_${Date.now()}`;
    const updated = [...selectedOptions, freeId];
    onSelectionChange(question.id, updated);
    setFreeText('');
  };

  return (
    <div className="space-y-4">
      <h3
        className="text-[25px] font-semibold text-[#2d4658] text-end tracking-[-1px]"
        style={{ fontFamily: "'Heebo', sans-serif" }}
      >
        {question.prompt}
      </h3>
      <div className="flex flex-wrap gap-3 justify-center">
        {question.options.map((option) => (
          <OptionChip
            key={option.id}
            label={option.label}
            emoji={option.emoji ?? undefined}
            selected={selectedOptions.includes(option.id)}
            onToggle={() => handleToggle(option.id)}
          />
        ))}
      </div>
      {question.allow_free_text && (
        <div className="flex gap-2 mt-3">
          <input
            type="text"
            value={freeText}
            onChange={(e) => setFreeText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleFreeTextSubmit()}
            placeholder="משהו אחר..."
            className="flex-1 px-4 py-3 rounded-xl border border-[#03ffe6] text-base text-[#2d4658]
                       placeholder:text-[rgba(45,70,88,0.4)] focus:outline-none
                       shadow-[0px_0px_6.7px_0px_rgba(0,0,0,0.08)] text-end"
            style={{ fontFamily: "'Heebo', sans-serif" }}
            dir="rtl"
          />
        </div>
      )}
    </div>
  );
}
