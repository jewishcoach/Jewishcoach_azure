import { useState } from 'react';
import { Lightbulb, ArrowLeft } from 'lucide-react';
import type { StageSummaryPayload } from '../types';

interface StageCompleteScreenProps {
  summary: StageSummaryPayload;
  onContinue: () => void;
  language: string;
}

export function StageCompleteScreen({ summary, onContinue, language }: StageCompleteScreenProps) {
  const isHe = language.startsWith('he');
  const [personalStatement, setPersonalStatement] = useState('');

  const insightLabels = isHe
    ? ['מה גיליתי', 'מה מנהל אותי כרגע', 'מה אני מבקש לבחור', 'משפט לקחת איתי']
    : ['What I discovered', 'What drives me now', 'What I choose', 'A sentence to carry'];

  return (
    <div className="flex-1 overflow-y-auto pb-14 lg:pb-0">
      <div className="max-w-lg mx-auto px-4 sm:px-6 py-6 sm:py-10 space-y-6">
        {/* Progress indicator */}
        <div className="flex items-center justify-between text-sm text-[#2d4658]" style={{ fontFamily: "'Heebo', sans-serif" }}>
          <span>{isHe ? 'משימה 1/5' : 'Task 1/5'}</span>
          <span className="text-xs text-[rgba(45,70,88,0.6)]">
            {summary.stage_title}
          </span>
        </div>

        {/* Tree illustration placeholder */}
        <div className="flex justify-center py-6">
          <div className="w-32 h-40 rounded-2xl bg-gradient-to-t from-[#2d4658] via-[#01897b] to-[#03ffe6] opacity-80 shadow-lg flex items-end justify-center pb-3">
            <div className="w-4 h-10 bg-amber-800 rounded-sm" />
          </div>
        </div>

        {/* Title */}
        <h2
          className="text-[40px] text-center text-[#2d4658]"
          style={{ fontFamily: "'Karantina', cursive", lineHeight: '77px' }}
        >
          {isHe
            ? `סיימת את שלב ה${summary.stage_title}`
            : `You completed the ${summary.stage_title} stage`}
        </h2>

        {/* Insight card — dark background */}
        <div className="bg-[#2d4658] rounded-xl p-5 sm:p-6 space-y-4 shadow-xl">
          {/* Card header */}
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-[rgba(3,255,230,0.2)] flex items-center justify-center">
              <Lightbulb size={16} className="text-[#03ffe6]" />
            </div>
            <h3 className="text-sm font-semibold text-white" style={{ fontFamily: "'Heebo', sans-serif" }}>
              {isHe ? 'כרטיס התובנה שלך' : 'Your Insight Card'}
            </h3>
          </div>

          {/* Insight sections */}
          <div className="space-y-3">
            {summary.insights.map((insight, idx) => (
              <div key={idx} className="space-y-1">
                <p className="text-xs font-semibold text-[#03ffe6]" style={{ fontFamily: "'Heebo', sans-serif" }}>
                  {insightLabels[idx] ?? (isHe ? 'תובנה' : 'Insight')}
                </p>
                <p className="text-sm text-gray-200 leading-relaxed" style={{ fontFamily: "'Heebo', sans-serif" }}>
                  {insight}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Personal statement input */}
        <div className="space-y-2">
          <input
            type="text"
            value={personalStatement}
            onChange={(e) => setPersonalStatement(e.target.value)}
            placeholder={isHe ? 'כתוב את המשפט שלך כאן' : 'Write your statement here'}
            className="w-full px-4 py-3 rounded-xl border border-[#03ffe6] text-base text-[#2d4658]
                       placeholder:text-[rgba(45,70,88,0.4)] focus:outline-none
                       shadow-[0px_0px_6.7px_0px_rgba(0,0,0,0.08)] text-end"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          />
          <p className="text-xs text-[rgba(45,70,88,0.6)] text-center" style={{ fontFamily: "'Heebo', sans-serif" }}>
            {isHe
              ? 'אתה יכול ללכת ולחזור מתי שתרצה. המידע ישמר אוטומטית'
              : 'You can come and go anytime. Data is saved automatically'}
          </p>
        </div>

        {/* CTA button */}
        {summary.next_stage_id && (
          <div className="space-y-3 pt-2">
            <button
              type="button"
              onClick={onContinue}
              className="w-full h-[53px] rounded-xl bg-[#9747ff] text-white text-base
                         hover:bg-[#8035e6] transition-colors
                         drop-shadow-[0px_8px_2.9px_rgba(0,0,0,0.12)]
                         flex items-center justify-center gap-2"
              style={{ fontFamily: "'Heebo', sans-serif" }}
            >
              <span>{isHe ? 'המשך לצעד הבא' : 'Continue to next step'}</span>
              <ArrowLeft size={16} className="rtl:rotate-180" />
            </button>

            <p className="text-xs text-center text-[rgba(45,70,88,0.6)]" style={{ fontFamily: "'Heebo', sans-serif" }}>
              {isHe
                ? `הצעד הבא שלך — ${summary.next_stage_title}`
                : `Your next step — ${summary.next_stage_title}`}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
