import { useState, useRef, useCallback } from 'react';

interface OnboardingScreenProps {
  onComplete: (emotions: string[], domain: string, freeText?: string) => void;
}

const EMOTION_OPTIONS = [
  'אני מרגיש תקוע',
  'אני מרגיש מבולבל',
  'אני מרגיש שחוק',
  'אני מרגיש רחוק מעצמי',
  'אני מרגיש שאני לא ממש את עצמי',
  'אני מרגיש שאני מגיב במקום לבחור',
  'אני מרגיש שהחיים שלי יכולים להיות אחרת',
  'קשה לי להגדיר',
];

const DOMAIN_OPTIONS = [
  'זוגיות',
  'עבודה',
  'משפחה',
  'בריאות',
  'כסף',
  'הגשמה אישית',
  'אחר',
];

export function OnboardingScreen({ onComplete }: OnboardingScreenProps) {
  const [selectedEmotions, setSelectedEmotions] = useState<string[]>([]);
  const [selectedDomain, setSelectedDomain] = useState<string>('');
  const [freeText, setFreeText] = useState('');
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [showExplanation, setShowExplanation] = useState(false);
  const domainRef = useRef<HTMLDivElement>(null);
  const freeTextRef = useRef<HTMLDivElement>(null);

  const toggleEmotion = useCallback((emotion: string) => {
    setSelectedEmotions((prev) => {
      const next = prev.includes(emotion) ? [] : [emotion];
      if (next.length > 0) {
        setStep(2);
        setTimeout(() => {
          domainRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 100);
      }
      return next;
    });
  }, []);

  const selectDomain = (domain: string) => {
    setSelectedDomain((prev) => {
      const next = prev === domain ? '' : domain;
      if (next) {
        setStep(3);
        setTimeout(() => {
          freeTextRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 100);
      }
      return next;
    });
  };

  const handleContinue = () => {
    if (step === 1 && selectedEmotions.length > 0) {
      setStep(2);
    } else if (step === 2 && selectedDomain) {
      setStep(3);
    } else if (step === 3) {
      onComplete(selectedEmotions, selectedDomain, freeText || undefined);
    }
  };

  const canContinue = step === 1
    ? selectedEmotions.length > 0
    : step === 2
      ? selectedDomain !== ''
      : true;

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-[832px] mx-auto px-6 py-10 sm:py-14 space-y-10">
        {/* Heading */}
        <div className="text-center space-y-3">
          <h1
            className="text-[40px] text-[#2d4658] leading-[77px]"
            style={{ fontFamily: "'Karantina', cursive" }}
          >
            בוא נפגוש את המקום שבו אתה נמצא היום.
          </h1>
          <p
            className="text-base text-[#2d4658] leading-[29px]"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            לפעמים אנחנו רצים כל כך מהר, שאנחנו כבר לא שמים לב למה שעובר עלינו.
            <br />
            לפני שנחפש לאן ללכת, נעצור לרגע ונראה איפה אנחנו נמצאים.
          </p>
        </div>

        {/* Helper chip */}
        <div className="flex flex-col items-center gap-3">
          <button
            type="button"
            onClick={() => setShowExplanation((prev) => !prev)}
            className="px-6 py-3 rounded-xl border border-[#01897b] text-[#2d4658] text-lg hover:bg-[rgba(1,137,123,0.05)] transition-colors"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            למה מתחילים מהמקום שבו אני נמצא?
          </button>
          {showExplanation && (
            <p
              className="text-sm text-[#2d4658] text-center max-w-lg leading-relaxed animate-[fadeIn_0.3s_ease-out]"
              style={{ fontFamily: "'Heebo', sans-serif" }}
            >
              כדי שנוכל ללכת לכיוון הנכון, קודם צריך לדעת מאיפה יוצאים.
              כשאנחנו עוצרים לרגע ומזהים מה באמת קורה — בלי לשפוט, בלי לפתור —
              אנחנו כבר מתחילים ליצור שינוי.
            </p>
          )}
        </div>

        {/* Emotions section */}
        <div className="space-y-6">
          <div className="text-right space-y-1">
            <h2
              className="text-[25px] font-semibold text-[#2d4658] tracking-[-1px] text-right"
              style={{ fontFamily: "'Heebo', sans-serif" }}
            >
              מה הכי מתאר את מה שאתה מרגיש בתקופה הזו?
            </h2>
            <p
              className="text-base text-[#2d4658] text-right"
              style={{ fontFamily: "'Heebo', sans-serif" }}
            >
              אין צורך לדייק עכשיו. מספיק לבחור את מה שהכי קרוב למה שאתה מרגיש
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {EMOTION_OPTIONS.map((emotion) => {
              const isSelected = selectedEmotions.includes(emotion);
              return (
                <button
                  key={emotion}
                  type="button"
                  onClick={() => toggleEmotion(emotion)}
                  className={`
                    h-[68px] px-6 rounded-xl border text-base text-center
                    transition-all duration-200
                    ${isSelected
                      ? 'border-[#04c4b1] bg-[rgba(3,255,230,0.3)] text-[#2d4658]'
                      : 'border-[#d2d2d2] bg-[rgba(255,255,255,0.3)] text-[#2d4658] hover:border-[#04c4b1]'
                    }
                  `}
                  style={{ fontFamily: "'Heebo', sans-serif" }}
                >
                  {emotion}
                </button>
              );
            })}
          </div>
        </div>

        {/* Domain section */}
        {step >= 2 && (
          <div ref={domainRef} className="space-y-6 animate-[fadeIn_0.3s_ease-out]">
            <h2
              className="text-[25px] font-semibold text-[#2d4658] text-right tracking-[-1px]"
              style={{ fontFamily: "'Heebo', sans-serif" }}
            >
              באיזה תחום זה מורגש לך הכי הרבה?
            </h2>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {DOMAIN_OPTIONS.map((domain) => {
                const isSelected = selectedDomain === domain;
                return (
                  <button
                    key={domain}
                    type="button"
                    onClick={() => selectDomain(domain)}
                    className={`
                      h-[68px] px-3 rounded-xl border text-base text-center
                      transition-all duration-200
                      ${isSelected
                        ? 'border-[#04c4b1] bg-[rgba(3,255,230,0.3)] text-[#2d4658]'
                        : 'border-[#d2d2d2] bg-[rgba(255,255,255,0.3)] text-[#2d4658] hover:border-[#04c4b1]'
                      }
                    `}
                    style={{ fontFamily: "'Heebo', sans-serif" }}
                  >
                    {domain}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Free text section (V3 addition) */}
        {step >= 3 && (
          <div ref={freeTextRef} className="space-y-4 animate-[fadeIn_0.3s_ease-out]">
            <h2
              className="text-[25px] font-semibold text-[#2d4658] text-right tracking-[-1px]"
              style={{ fontFamily: "'Heebo', sans-serif" }}
            >
              ספר בקצרה מה עובר עליך
            </h2>
            <p
              className="text-base text-[#2d4658] text-right"
              style={{ fontFamily: "'Heebo', sans-serif" }}
            >
              זה יעזור לנו להתחיל מהמקום הנכון. משפט או שניים מספיקים.
            </p>
            <textarea
              dir="auto"
              value={freeText}
              onChange={(e) => setFreeText(e.target.value)}
              placeholder="למשל: יש לי קונפליקט עם השותף בעבודה שחוזר על עצמו..."
              rows={3}
              className="w-full px-4 py-3 rounded-xl border-[0.8px] border-[#03ffe6] bg-white text-base text-[#2d4658]
                         placeholder:text-[rgba(45,70,88,0.4)] focus:outline-none
                         shadow-[0px_0px_6.7px_0px_rgba(0,0,0,0.08)] text-right resize-none"
              style={{ fontFamily: "'Heebo', sans-serif" }}
            />
          </div>
        )}

        {/* Continue button */}
        <div className="flex justify-center pt-2">
          <button
            type="button"
            onClick={handleContinue}
            disabled={!canContinue}
            className={`
              w-[239px] h-[53px] rounded-xl text-base font-normal
              drop-shadow-[0px_8px_2.9px_rgba(0,0,0,0.12)]
              transition-colors
              ${canContinue
                ? 'bg-[#9747ff] text-white hover:bg-[#8035e6]'
                : 'bg-[#d9d9d9] text-[#999] cursor-not-allowed'
              }
            `}
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            {step < 3 ? 'המשך לצעד הבא' : 'בוא נתחיל'}
          </button>
        </div>

        {step >= 2 && (
          <p className="text-center text-sm text-[#2d4658]" style={{ fontFamily: "'Heebo', sans-serif" }}>
            עצם זה שעצרת לרגע והתבוננת, כבר יוצר תנועה חדשה.
          </p>
        )}
      </div>
    </div>
  );
}
