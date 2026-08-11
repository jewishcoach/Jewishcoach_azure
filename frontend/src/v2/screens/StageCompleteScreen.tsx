import { useState } from 'react';
import { Lightbulb, ArrowLeft, Share2, Download } from 'lucide-react';
import type { StageSummaryPayload } from '../types';

const TREE_IMAGES: Record<string, string> = {
  identification: '/trees/tree-identification.png',
  discovery: '/trees/tree-discovery.png',
  kamaz: '/trees/tree-kamaz.png',
  choice: '/trees/tree-self-discovery.png',
  vision: '/trees/tree-vision.png',
};

interface StageCompleteScreenProps {
  summary: StageSummaryPayload;
  onContinue: () => void;
  language: string;
  userMessages?: string[];
}

export function StageCompleteScreen({ summary, onContinue, language, userMessages }: StageCompleteScreenProps) {
  const isHe = language.startsWith('he');
  const [personalStatement, setPersonalStatement] = useState('');

  const insightLabels = isHe
    ? ['מה גיליתי', 'מה מנהל אותי כרגע', 'מה אני מבקש לבחור', 'משפט לקחת איתי']
    : ['What I discovered', 'What drives me now', 'What I choose', 'A sentence to carry'];

  const treeImage = TREE_IMAGES[summary.stage_id] || TREE_IMAGES.identification;

  return (
    <div className="flex-1 overflow-y-auto pb-14 lg:pb-0" dir="rtl">
      <div className="max-w-[670px] mx-auto px-4 py-6 space-y-6">
        {/* Task progress bar */}
        <div className="bg-white border-b border-[#e0ddd8] rounded-t-xl px-6 py-4 flex items-center justify-between">
          <div className="text-right">
            <p className="text-[10px] uppercase tracking-wide text-[#6b6b6b] font-semibold" style={{ fontFamily: "'Assistant', sans-serif" }}>
              {isHe ? 'משימת היום' : "Today's task"}
            </p>
            <p className="text-[17px] font-semibold text-[#2d4658]" style={{ fontFamily: "'Heebo', sans-serif" }}>
              {isHe ? 'לעצור לרגע כדי לראות מה באמת קורה בי' : 'Stop to see what\'s really happening'}
            </p>
          </div>
          <div className="text-center">
            <p className="text-[10px] text-[#2d4658]" style={{ fontFamily: "'Heebo', sans-serif" }}>
              {isHe ? 'משימה' : 'Task'}
            </p>
            <p className="text-lg font-semibold text-[#2d4658]" style={{ fontFamily: "'Heebo', sans-serif" }}>
              1/5
            </p>
          </div>
        </div>

        {/* Tree illustration */}
        <div className="flex justify-center py-4">
          <img
            src={treeImage}
            alt=""
            className="h-[140px] w-auto object-contain mix-blend-multiply"
          />
        </div>

        {/* Title */}
        <h2
          className="text-[40px] text-center text-[#2d4658]"
          style={{ fontFamily: "'Karantina', cursive", lineHeight: '77px' }}
        >
          {isHe
            ? `סיימת את שלב ״ה${summary.stage_title}״`
            : `You completed the "${summary.stage_title}" stage`}
        </h2>

        {/* Insight card */}
        <div className="rounded-xl overflow-hidden shadow-[0px_0px_3.35px_rgba(0,0,0,0.08)]">
          {/* Card header */}
          <div className="bg-[#2d4658] px-4 py-3 flex items-center gap-2 justify-end">
            <span className="text-[13px] font-semibold text-white" style={{ fontFamily: "'Heebo', sans-serif" }}>
              {isHe ? 'כרטיס התובנה שלך' : 'Your Insight Card'}
            </span>
            <Lightbulb size={20} className="text-[#03ffe6]" />
          </div>

          {/* Card body */}
          <div className="bg-white p-6 space-y-5">
            {/* Insight sections */}
            <div className="space-y-4">
              {summary.insights.map((insight, idx) => (
                <div key={idx} className="text-right">
                  <p className="text-[10px] font-medium uppercase text-[#01897b] leading-[15px]" style={{ fontFamily: "'Heebo', sans-serif" }}>
                    {insightLabels[idx] ?? (isHe ? 'תובנה' : 'Insight')}
                  </p>
                  <p className="text-sm text-[#2d4658] leading-[22.75px]" style={{ fontFamily: "'Heebo', sans-serif" }}>
                    {insight}
                  </p>
                </div>
              ))}
            </div>

            {/* "משפט לקחת איתי" highlighted */}
            {summary.insights.length >= 4 && (
              <div className="bg-[#f6f4f0] rounded-xl px-4 py-3 text-right">
                <p className="text-[10px] font-bold uppercase text-[#01897b] tracking-wider" style={{ fontFamily: "'Heebo', sans-serif" }}>
                  {isHe ? 'משפט לקחת איתי' : 'A sentence to carry'}
                </p>
                <p className="text-sm font-medium text-[#2d4658]" style={{ fontFamily: "'Heebo', sans-serif" }}>
                  {summary.insights[3]}
                </p>
              </div>
            )}

            {/* Personal statement input */}
            <div className="text-right">
              <p className="text-[10px] uppercase text-[#01897b]" style={{ fontFamily: "'Heebo', sans-serif" }}>
                {isHe ? 'משפט שאני רוצה להגיד לעצמי' : 'A sentence I want to tell myself'}
              </p>
              <input
                type="text"
                value={personalStatement}
                onChange={(e) => setPersonalStatement(e.target.value)}
                placeholder={isHe ? 'כתוב את המשפט שלך כאן' : 'Write your statement here'}
                className="w-full mt-1 px-4 py-3 rounded-xl border border-[#00a696] text-sm text-[#2d4658]
                           placeholder:text-[rgba(45,70,88,0.4)] focus:outline-none
                           shadow-[0px_0px_6.7px_0px_rgba(0,0,0,0.08)] text-right"
                style={{ fontFamily: "'Heebo', sans-serif" }}
              />
            </div>
          </div>

          {/* Card footer */}
          <div className="bg-[#2d4658] px-4 py-3 text-center">
            <p className="text-[13px] font-semibold text-white" style={{ fontFamily: "'Heebo', sans-serif" }}>
              {isHe ? 'אתה יכול ללכת ולחזור מתי שתרצה המידע ישמר אוטומטית' : 'You can come and go anytime. Data is saved automatically.'}
            </p>
          </div>
        </div>

        {/* Action buttons (share/save) */}
        <div className="flex items-center justify-center gap-4 pt-2">
          <button
            type="button"
            onClick={() => {
              const insightsText = summary.insights.join('\n');
              const userText = userMessages?.length
                ? `\n\n${isHe ? 'מה שכתבתי:' : 'What I wrote:'}\n${userMessages.slice(-3).join('\n')}`
                : '';
              if (navigator.share) {
                navigator.share({
                  title: isHe ? 'כרטיס התובנה שלי' : 'My Insight Card',
                  text: insightsText + userText,
                });
              }
            }}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl border border-[#03ffe6] text-sm text-[#2d4658] hover:bg-[rgba(3,255,230,0.05)] transition-colors"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            <Share2 size={16} className="text-[#03ffe6]" />
            <span>{isHe ? 'שיתוף' : 'Share'}</span>
          </button>
          <button
            type="button"
            onClick={() => {
              const text = summary.insights.join('\n');
              const blob = new Blob([text], { type: 'text/plain' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `insight-${summary.stage_id}.txt`;
              a.click();
              URL.revokeObjectURL(url);
            }}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl border border-[#03ffe6] text-sm text-[#2d4658] hover:bg-[rgba(3,255,230,0.05)] transition-colors"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            <Download size={16} className="text-[#03ffe6]" />
            <span>{isHe ? 'שמירה' : 'Save'}</span>
          </button>
        </div>

        {/* CTA button */}
        {summary.next_stage_id && (
          <div className="flex flex-col items-center gap-2 pt-4">
            <button
              type="button"
              onClick={onContinue}
              className="w-[239px] h-[53px] rounded-xl bg-[#9747ff] text-white text-base
                         hover:bg-[#8035e6] transition-colors
                         drop-shadow-[0px_8px_2.9px_rgba(0,0,0,0.12)]
                         flex items-center justify-center gap-2"
              style={{ fontFamily: "'Heebo', sans-serif" }}
            >
              <span>{isHe ? 'המשך לצעד הבא' : 'Continue to next step'}</span>
            </button>

            <p className="text-base text-[#2d4658]" style={{ fontFamily: "'Heebo', sans-serif" }}>
              {isHe
                ? `הצעד הבא שלך - ${summary.next_stage_title}`
                : `Your next step — ${summary.next_stage_title}`}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
