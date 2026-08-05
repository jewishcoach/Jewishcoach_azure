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
      <div className="max-w-[832px] w-full space-y-8">
        <div className="text-center space-y-3">
          <h2
            className="text-[40px] text-[#2d4658]"
            style={{ fontFamily: "'Karantina', cursive", lineHeight: '77px' }}
          >
            {payload.stage_title}
          </h2>
          <p
            className="text-base text-[#2d4658]"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            {payload.intro_text}
          </p>
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
            className={`
              w-[239px] h-[53px] rounded-xl text-base
              drop-shadow-[0px_8px_2.9px_rgba(0,0,0,0.12)]
              transition-colors
              ${
                hasAllAnswers && !isSubmitting
                  ? 'bg-[#9747ff] text-white hover:bg-[#8035e6]'
                  : 'bg-[#d9d9d9] text-[#999] cursor-not-allowed'
              }
            `}
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            {isSubmitting ? '...' : 'המשך לצעד הבא'}
          </button>
        </div>
      </div>
    </div>
  );
}
