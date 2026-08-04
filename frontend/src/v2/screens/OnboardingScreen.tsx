import { useState } from 'react';

interface OnboardingScreenProps {
  onComplete: (emotions: string[], domain: string) => void;
}

const EMOTION_OPTIONS = [
  'אני מרגיש תקוע',
  'אני מרגיש מבולבל',
  'אני מרגיש רחוק מעצמי',
  'אני מרגיש שחוק',
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
  const [step, setStep] = useState<1 | 2>(1);

  const toggleEmotion = (emotion: string) => {
    setSelectedEmotions((prev) =>
      prev.includes(emotion)
        ? prev.filter((e) => e !== emotion)
        : [...prev, emotion],
    );
  };

  const selectDomain = (domain: string) => {
    setSelectedDomain((prev) => (prev === domain ? '' : domain));
  };

  const handleContinue = () => {
    if (step === 1 && selectedEmotions.length > 0) {
      setStep(2);
    } else if (step === 2 && selectedDomain) {
      onComplete(selectedEmotions, selectedDomain);
    }
  };

  const canContinue = step === 1 ? selectedEmotions.length > 0 : selectedDomain !== '';

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-3xl mx-auto px-6 py-10 sm:py-14 space-y-10">
        {/* Heading */}
        <div className="text-center space-y-3">
          <h1 className="text-4xl sm:text-5xl font-bold text-teal-800 leading-snug" style={{ fontFamily: "'Karantina', cursive" }}>
            בוא נפגוש את המקום שבו אתה נמצא היום.
          </h1>
          <p className="text-sm sm:text-base text-gray-600 leading-relaxed">
            לפעמים אנחנו רצים כל כך מהר, שאנחנו כבר לא שמים לב למה שעובר עלינו.
            <br />
            לפני שנחפש לאן ללכת, נעצור לרגע ונראה איפה אנחנו נמצאים.
          </p>
        </div>

        {/* Helper chip */}
        <div className="flex justify-center">
          <div className="px-6 py-3 rounded-full border border-gray-300 text-gray-600 text-sm">
            למה מתחילים מהמקום שבו אני נמצא?
          </div>
        </div>

        {/* Emotions section (always visible) */}
        <div className="space-y-3">
          <div className="text-center space-y-1.5">
            <h2 className="text-lg sm:text-xl font-bold text-gray-800">
              מה הכי מתאר את מה שאתה מרגיש בתקופה הזו?
            </h2>
            <p className="text-sm text-gray-500">
              אין צורך לדייק עכשיו. מספיק לבחור את מה שהכי קרוב למה שאתה מרגיש
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {EMOTION_OPTIONS.map((emotion) => {
              const isSelected = selectedEmotions.includes(emotion);
              return (
                <button
                  key={emotion}
                  type="button"
                  onClick={() => toggleEmotion(emotion)}
                  className={`
                    py-4 px-4 rounded-xl border text-sm font-medium text-center
                    transition-all duration-200
                    ${
                      isSelected
                        ? 'border-teal-300 bg-teal-50 text-teal-800'
                        : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
                    }
                  `}
                >
                  {emotion}
                </button>
              );
            })}
          </div>
        </div>

        {/* Domain section — appears after clicking continue on step 1 */}
        {step === 2 && (
          <div className="space-y-3 animate-[fadeIn_0.3s_ease-out]">
            <h2 className="text-lg sm:text-xl font-bold text-gray-800 text-center">
              באיזה תחום זה מורגש לך הכי הרבה?
            </h2>

            <div className="grid grid-cols-4 gap-3">
              {DOMAIN_OPTIONS.map((domain) => {
                const isSelected = selectedDomain === domain;
                return (
                  <button
                    key={domain}
                    type="button"
                    onClick={() => selectDomain(domain)}
                    className={`
                      py-3.5 px-3 rounded-xl border text-sm font-medium text-center
                      transition-all duration-200
                      ${
                        isSelected
                          ? 'border-teal-300 bg-teal-50 text-teal-800'
                          : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
                      }
                    `}
                  >
                    {domain}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Continue button + footer */}
        <div className="flex justify-center pt-2">
          <button
            type="button"
            onClick={handleContinue}
            disabled={!canContinue}
            className="px-16 py-3.5 rounded-full bg-purple-500 text-white font-semibold text-base
                       disabled:opacity-40 disabled:cursor-not-allowed
                       hover:bg-purple-600 transition-colors"
          >
            המשך לצעד הבא
          </button>
        </div>

        <p className="text-center text-sm text-gray-500">
          עצם זה שעצרת לרגע והתבוננת, כבר יוצר תנועה חדשה.
        </p>
      </div>
    </div>
  );
}
