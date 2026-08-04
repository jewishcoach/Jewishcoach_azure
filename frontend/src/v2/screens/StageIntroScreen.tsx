import { useState } from 'react';
import type { StageIntroPayload } from '../types';
import { IntroQuestionCard } from '../components/IntroQuestionCard';

interface StageIntroScreenProps {
  payload: StageIntroPayload;
  onSubmit: (answers: Record<string, string[]>) => void;
  isSubmitting: boolean;
}

export function StageIntroScreen({ payload, onSubmit, isSubmitting }: StageIntroScreenProps) {
  const [answers, setAnswers] = useState<Record<string, string[]>>({});

  const handleSelectionChange = (questionId: string, optionIds: string[]) => {
    setAnswers((prev) => ({ ...prev, [questionId]: optionIds }));
  };

  const hasAllAnswers = payload.questions.every(
    (q) => (answers[q.id]?.length ?? 0) > 0,
  );

  const handleContinue = () => {
    if (hasAllAnswers && !isSubmitting) {
      onSubmit(answers);
    }
  };

  return (
    <div className="flex-1 flex flex-col items-center justify-start sm:justify-center px-4 sm:px-6 py-8 sm:py-12 overflow-y-auto pb-14 lg:pb-12">
      <div className="max-w-2xl w-full space-y-8">
        <div className="text-center space-y-3">
          <h2 className="text-xl sm:text-2xl font-bold text-gray-800">
            {payload.stage_title}
          </h2>
          <p className="text-sm sm:text-base text-gray-600">{payload.intro_text}</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 sm:gap-8">
          {payload.questions.map((question) => (
            <IntroQuestionCard
              key={question.id}
              question={question}
              selectedOptions={answers[question.id] ?? []}
              onSelectionChange={handleSelectionChange}
            />
          ))}
        </div>

        <div className="flex justify-center pt-4">
          <button
            type="button"
            onClick={handleContinue}
            disabled={!hasAllAnswers || isSubmitting}
            className="px-8 py-3 rounded-full bg-purple-500 text-white font-medium text-sm
                       disabled:opacity-40 disabled:cursor-not-allowed
                       hover:bg-purple-600 transition-colors shadow-md"
          >
            {isSubmitting ? '...' : 'המשך לצעד הבא'}
          </button>
        </div>
      </div>
    </div>
  );
}
