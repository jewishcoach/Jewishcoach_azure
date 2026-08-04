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

  // Map insights into structured card data
  const insightLabels = isHe
    ? ['מה גיליתי', 'מה מנהל אותי כרגע', 'מה אני מבקש לבחור', 'משפט לקחת איתי']
    : ['What I discovered', 'What drives me now', 'What I choose', 'A sentence to carry'];

  return (
    <div className="flex-1 overflow-y-auto pb-14 lg:pb-0">
      <div className="max-w-lg mx-auto px-4 sm:px-6 py-6 sm:py-10 space-y-6">
        {/* Progress indicator */}
        <div className="flex items-center justify-between text-sm text-gray-500">
          <span>{isHe ? 'משימה 1/5' : 'Task 1/5'}</span>
          <span className="text-xs text-gray-400">
            {isHe ? summary.stage_title : summary.stage_title}
          </span>
        </div>

        {/* Tree illustration placeholder */}
        <div className="flex justify-center py-6">
          <div className="w-32 h-40 rounded-2xl bg-gradient-to-t from-teal-700 via-teal-500 to-emerald-400 opacity-80 shadow-lg flex items-end justify-center pb-3">
            <div className="w-4 h-10 bg-amber-800 rounded-sm" />
          </div>
        </div>

        {/* Title */}
        <h2 className="text-xl sm:text-2xl font-bold text-center text-gray-800">
          {isHe
            ? `סיימת את שלב ה${summary.stage_title}`
            : `You completed the ${summary.stage_title} stage`}
        </h2>

        {/* Insight card — dark background */}
        <div className="bg-slate-800 rounded-2xl p-5 sm:p-6 space-y-4 shadow-xl">
          {/* Card header */}
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-teal-500/20 flex items-center justify-center">
              <Lightbulb size={16} className="text-teal-400" />
            </div>
            <h3 className="text-sm font-bold text-white">
              {isHe ? 'כרטיס התובנה שלך' : 'Your Insight Card'}
            </h3>
          </div>

          {/* Insight sections */}
          <div className="space-y-3">
            {summary.insights.map((insight, idx) => (
              <div key={idx} className="space-y-1">
                <p className="text-xs font-semibold text-teal-400">
                  {insightLabels[idx] ?? (isHe ? 'תובנה' : 'Insight')}
                </p>
                <p className="text-sm text-gray-200 leading-relaxed">
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
            className="w-full px-4 py-3 rounded-xl border border-gray-200 text-sm text-gray-700
                       placeholder:text-gray-400 focus:outline-none focus:border-teal-400 focus:ring-1
                       focus:ring-teal-400/20 transition-colors"
          />
          <p className="text-xs text-gray-400 text-center">
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
              className="w-full py-3.5 rounded-full bg-purple-500 text-white font-semibold text-sm
                         hover:bg-purple-600 transition-colors shadow-lg shadow-purple-500/25
                         flex items-center justify-center gap-2"
            >
              <span>{isHe ? 'המשך לצעד הבא' : 'Continue to next step'}</span>
              <ArrowLeft size={16} className="rtl:rotate-180" />
            </button>

            {/* Next stage hint */}
            <p className="text-xs text-center text-gray-500">
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
