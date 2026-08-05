import { SignIn, SignUp } from '@clerk/clerk-react';
import { useState } from 'react';

interface LoginScreenProps {
  onSignedIn?: () => void;
}

export function LoginScreen({ onSignedIn: _onSignedIn }: LoginScreenProps) {
  const [mode, setMode] = useState<'signin' | 'signup'>('signup');

  return (
    <div className="h-screen flex" dir="rtl">
      {/* Right side — video + text (dark) */}
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-between bg-[#2d4658] p-10 text-white relative overflow-hidden">
        <div className="space-y-4 relative z-10">
          <p
            className="text-[25px] text-[#2d4658] text-center tracking-[-1px]"
            style={{ fontFamily: "'Heebo', sans-serif", lineHeight: '41px' }}
          >
            כמה מילים אישיות עבורך מבני גל לפני שמתחילים
          </p>
          {/* Video placeholder */}
          <div className="aspect-video bg-slate-700 rounded-xl flex items-center justify-center overflow-hidden relative shadow-[0px_27px_14.2px_rgba(0,0,0,0.25)]">
            <div className="absolute inset-0 bg-slate-700" />
            <div className="relative z-10 flex flex-col items-center gap-2">
              <div className="w-11 h-11 rounded-full bg-[rgba(150,150,150,0.69)] flex items-center justify-center">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="white"><path d="M8 5v14l11-7z"/></svg>
              </div>
              <span className="text-sm font-semibold text-white" style={{ fontFamily: "'Assistant', sans-serif" }}>3 דקות</span>
            </div>
          </div>
        </div>

        <div className="space-y-4 relative z-10">
          <p
            className="text-[25px] text-[#2d4658] text-center tracking-[-1px]"
            style={{ fontFamily: "'Heebo', sans-serif", lineHeight: '41px' }}
          >
            כמה דקות של עצירה יכולות לפתוח אפשרויות חדשות שלא ראינו קודם.
            <br />
            לא צריך לפתור עכשיו את כל החיים. רק לעצור לרגע.
          </p>
          <p
            className="text-base text-[#2d4658] text-center"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            לא צריך למהר אפשר לקחת את הזמן ולחזור בכל שלב
          </p>
        </div>

        <div className="relative z-10">
          <p
            className="text-[25px] text-white text-center tracking-[-1px]"
            style={{ fontFamily: "'Heebo', sans-serif", lineHeight: '41px' }}
          >
            בכמה הדקות הקרובות לא נחפש פתרונות. אלא
            <br />
            נתחיל לבנות את האמון בדרך שלך.
          </p>
        </div>
      </div>

      {/* Left side — auth form (dark background) */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 bg-[#2d4658]">
        <div className="w-full max-w-[384px] space-y-6">
          {/* Title */}
          <div className="text-center">
            <h1
              className="text-[75px] text-white"
              style={{ fontFamily: "'Karantina', cursive", lineHeight: '77px' }}
            >
              {mode === 'signup' ? 'נפגשים בפעם הראשונה' : 'ברוך הבא למסע שלך'}
            </h1>
          </div>

          {/* Clerk component */}
          <div className="flex justify-center">
            {mode === 'signup' ? (
              <SignUp
                appearance={{
                  elements: {
                    rootBox: 'w-full',
                    card: 'shadow-none border-none w-full bg-transparent',
                    headerTitle: 'hidden',
                    headerSubtitle: 'hidden',
                    socialButtonsBlockButton: 'rounded-xl border border-[#e0ddd8] py-3 bg-white',
                    formFieldInput: 'rounded-xl border-[#e0ddd8] bg-white',
                    formFieldLabel: 'text-white text-xs',
                    formButtonPrimary: 'rounded-xl bg-[#9747ff] hover:bg-[#8035e6] drop-shadow-[0px_8px_2.9px_rgba(0,0,0,0.12)]',
                    footerAction: 'hidden',
                  },
                }}
              />
            ) : (
              <SignIn
                appearance={{
                  elements: {
                    rootBox: 'w-full',
                    card: 'shadow-none border-none w-full bg-transparent',
                    headerTitle: 'hidden',
                    headerSubtitle: 'hidden',
                    socialButtonsBlockButton: 'rounded-xl border border-[#e0ddd8] py-3 bg-white',
                    formFieldInput: 'rounded-xl border-[#e0ddd8] bg-white',
                    formFieldLabel: 'text-white text-xs',
                    formButtonPrimary: 'rounded-xl bg-[#9747ff] hover:bg-[#8035e6] drop-shadow-[0px_8px_2.9px_rgba(0,0,0,0.12)]',
                    footerAction: 'hidden',
                  },
                }}
              />
            )}
          </div>

          {/* Toggle mode + terms */}
          <div className="text-center space-y-2">
            <p className="text-base" style={{ fontFamily: "'Assistant', sans-serif" }}>
              <span className="text-[#03ffe6] font-semibold">
                {' '}בהרשמה אתה מסכים ל
              </span>
              <span className="text-[#03ffe6] font-semibold">תנאי השימוש ולמדיניות הפרטיות</span>
            </p>
            <p className="text-sm" style={{ fontFamily: "'Assistant', sans-serif" }}>
              {mode === 'signup' ? (
                <>
                  <span className="text-white">כבר יש לך חשבון? </span>
                  <button type="button" onClick={() => setMode('signin')} className="text-[#03ffe6] font-semibold hover:underline">
                    כניסה
                  </button>
                </>
              ) : (
                <>
                  <span className="text-white">משתמש חדש? </span>
                  <button type="button" onClick={() => setMode('signup')} className="text-[#03ffe6] font-semibold hover:underline">
                    צור חשבון
                  </button>
                </>
              )}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
