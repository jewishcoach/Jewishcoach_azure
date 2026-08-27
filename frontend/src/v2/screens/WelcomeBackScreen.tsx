import { useState } from 'react';

const MOOD_OPTIONS = ['רגוע מאד', 'שמח אבל כאן', 'צריך כמה דקות', 'מוכן להמשיך'];

interface WelcomeBackScreenProps {
  stageTitle: string;
  stageNumber: number;
  personalStatement?: string;
  lastActiveDate?: string;
  onContinue: () => void;
  onGoHome: () => void;
}

export function WelcomeBackScreen({
  stageTitle,
  stageNumber,
  personalStatement,
  lastActiveDate,
  onContinue,
  onGoHome,
}: WelcomeBackScreenProps) {
  const [selectedMood, setSelectedMood] = useState<string | null>(null);

  const daysAgo = lastActiveDate
    ? Math.max(1, Math.floor((Date.now() - new Date(lastActiveDate).getTime()) / (1000 * 60 * 60 * 24)))
    : null;

  return (
    <div className="flex-1 flex flex-col items-center relative overflow-hidden" dir="rtl">
      {/* Sky background */}
      <img src="/login-bg.png" alt="" className="absolute inset-0 w-full h-full object-cover" />

      {/* Tree illustration - left side */}
      <div className="absolute bottom-0 left-0 w-[220px] lg:w-[320px] z-0">
        <img src="/tree-globe.png" alt="" className="w-full object-contain" />
      </div>

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center justify-center flex-1 w-full max-w-[600px] px-5 py-10 space-y-6">
        {/* Title */}
        <div className="text-center space-y-2">
          <h1
            className="text-[48px] lg:text-[64px] text-[#2d4658]"
            style={{ fontFamily: "'Karantina', cursive", lineHeight: '1.1' }}
          >
            שמחים שחזרת
          </h1>
          <p
            className="text-[18px] text-[#2d4658]"
            style={{ fontFamily: "'Heebo', sans-serif", lineHeight: '28px' }}
          >
            לא הלכת לשום מקום.
            <br />
            המסע שלך מחכה בדיוק איפה שעצרת.
          </p>
        </div>

        {/* Time badge */}
        <div className="flex items-center gap-3">
          <span
            className="px-3 py-1 rounded-full bg-[#2d4658] text-white text-xs font-medium"
            style={{ fontFamily: "'Assistant', sans-serif" }}
          >
            פרק {stageNumber}
          </span>
          {daysAgo && (
            <span
              className="text-sm text-[#2d4658]"
              style={{ fontFamily: "'Heebo', sans-serif" }}
            >
              לפני {daysAgo} ימים
            </span>
          )}
        </div>

        {/* Progress card */}
        <div className="w-full rounded-xl overflow-hidden shadow-[0px_4px_20px_rgba(0,0,0,0.1)]">
          {/* Card header */}
          <div className="bg-[#2d4658] px-5 py-3 text-center">
            <p className="text-sm font-semibold text-white" style={{ fontFamily: "'Heebo', sans-serif" }}>
              נמשיך מהמקום שבו עצרנו
            </p>
            <p className="text-xs text-[rgba(255,255,255,0.6)] mt-0.5" style={{ fontFamily: "'Heebo', sans-serif" }}>
              שלב {stageNumber} מתוך 5
            </p>
          </div>

          {/* Card body */}
          <div className="bg-white px-5 py-5 space-y-4">
            <p
              className="text-base font-semibold text-[#2d4658] text-center"
              style={{ fontFamily: "'Heebo', sans-serif" }}
            >
              {stageTitle}
            </p>

            {personalStatement && (
              <div className="bg-[rgba(3,255,230,0.08)] border border-[rgba(3,255,230,0.3)] rounded-xl px-4 py-3 text-center">
                <p className="text-[11px] text-[#01897b] font-semibold mb-1" style={{ fontFamily: "'Heebo', sans-serif" }}>
                  משפט מלקחת איתך
                </p>
                <p className="text-sm text-[#2d4658]" style={{ fontFamily: "'Heebo', sans-serif" }}>
                  &ldquo;{personalStatement}&rdquo;
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Mood check */}
        <div className="w-full space-y-3">
          <p className="text-sm font-semibold text-[#2d4658] text-right" style={{ fontFamily: "'Heebo', sans-serif" }}>
            איך אתה מגיע היום?
          </p>
          <div className="flex flex-wrap gap-2 justify-center">
            {MOOD_OPTIONS.map((mood) => (
              <button
                key={mood}
                type="button"
                onClick={() => setSelectedMood(mood)}
                className={`px-4 py-2 rounded-xl border text-sm transition-all
                  ${selectedMood === mood
                    ? 'border-[#03ffe6] bg-[rgba(3,255,230,0.15)] text-[#2d4658]'
                    : 'border-[#d2d2d2] bg-white text-[#2d4658] hover:border-[#03ffe6]'
                  }`}
                style={{ fontFamily: "'Assistant', sans-serif" }}
              >
                {mood}
              </button>
            ))}
          </div>
        </div>

        {/* CTA */}
        <button
          type="button"
          onClick={onContinue}
          className="w-full max-w-[320px] h-[53px] rounded-xl bg-[#9747ff] text-white text-base font-medium
                     hover:bg-[#8035e6] transition-colors
                     drop-shadow-[0px_8px_2.9px_rgba(0,0,0,0.12)]"
          style={{ fontFamily: "'Heebo', sans-serif" }}
        >
          נמשיך מאיפה שעצרנו
        </button>

        {/* Home link */}
        <button
          type="button"
          onClick={onGoHome}
          className="text-sm text-[#2d4658] underline hover:no-underline"
          style={{ fontFamily: "'Heebo', sans-serif" }}
        >
          קח אותי למסך הבית
        </button>
      </div>
    </div>
  );
}
