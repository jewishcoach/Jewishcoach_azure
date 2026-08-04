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
      <h3 className="text-lg font-semibold text-gray-800 text-center">
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
            className="flex-1 px-4 py-2 rounded-xl border border-gray-200 text-sm focus:outline-none focus:border-teal-400"
            dir="rtl"
          />
        </div>
      )}
    </div>
  );
}
