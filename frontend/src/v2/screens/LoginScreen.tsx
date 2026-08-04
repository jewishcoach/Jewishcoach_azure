import { SignIn, SignUp } from '@clerk/clerk-react';
import { useState } from 'react';

interface LoginScreenProps {
  onSignedIn?: () => void;
}

export function LoginScreen({ onSignedIn: _onSignedIn }: LoginScreenProps) {
  const [mode, setMode] = useState<'signin' | 'signup'>('signup');

  return (
    <div className="h-screen flex" dir="rtl">
      {/* Right side — video + text (dark gradient) */}
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-between bg-gradient-to-b from-slate-600 to-slate-800 p-10 text-white">
        <div className="space-y-4">
          <p className="text-base text-gray-300">
            כמה מילים אישיות עבורך מבני גל לפני שמתחילים
          </p>
          {/* Video placeholder */}
          <div className="aspect-video bg-slate-700 rounded-2xl flex items-center justify-center overflow-hidden relative">
            <div className="absolute inset-0 bg-slate-700" />
            <div className="relative z-10 flex flex-col items-center gap-2">
              <div className="w-14 h-14 rounded-full bg-teal-500/30 flex items-center justify-center">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="white"><path d="M8 5v14l11-7z"/></svg>
              </div>
              <span className="text-sm text-gray-300">3 דקות</span>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <p className="text-xl font-medium leading-relaxed">
            כמה דקות של עצירה יכולות לפתוח אפשרויות חדשות שלא ראינו קודם.
            <br />
            לא צריך לפתור עכשיו את כל החיים. רק לעצור לרגע.
          </p>
          <p className="text-sm text-gray-400">
            לא צריך למהר אפשר לקחת את הזמן ולחזור בכל שלב
          </p>
        </div>

        <div className="text-lg font-medium text-center">
          <p>בכמה הדקות הקרובות לא נחפש פתרונות. אלא</p>
          <p>נתחיל לבנות את האמון בדרך שלך.</p>
        </div>
      </div>

      {/* Left side — auth form */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 bg-white">
        <div className="w-full max-w-sm space-y-6">
          {/* Title */}
          <div className="text-center space-y-2">
            <h1 className="text-3xl font-bold text-teal-800" style={{ fontFamily: "'Karantina', cursive" }}>
              {mode === 'signup' ? 'נפגשים בפעם הראשונה' : 'ברוך הבא למסע שלך'}
            </h1>
            {mode === 'signin' && (
              <p className="text-sm text-gray-500">איך תרצה להמשיך?</p>
            )}
          </div>

          {/* Clerk component */}
          <div className="flex justify-center">
            {mode === 'signup' ? (
              <SignUp
                appearance={{
                  elements: {
                    rootBox: 'w-full',
                    card: 'shadow-none border-none w-full',
                    headerTitle: 'hidden',
                    headerSubtitle: 'hidden',
                    socialButtonsBlockButton: 'rounded-xl border border-gray-200 py-3',
                    formFieldInput: 'rounded-xl border-gray-200',
                    formButtonPrimary: 'rounded-full bg-purple-500 hover:bg-purple-600',
                    footerAction: 'hidden',
                  },
                }}
              />
            ) : (
              <SignIn
                appearance={{
                  elements: {
                    rootBox: 'w-full',
                    card: 'shadow-none border-none w-full',
                    headerTitle: 'hidden',
                    headerSubtitle: 'hidden',
                    socialButtonsBlockButton: 'rounded-xl border border-gray-200 py-3',
                    formFieldInput: 'rounded-xl border-gray-200',
                    formButtonPrimary: 'rounded-full bg-purple-500 hover:bg-purple-600',
                    footerAction: 'hidden',
                  },
                }}
              />
            )}
          </div>

          {/* Toggle mode */}
          <p className="text-center text-sm text-gray-500">
            {mode === 'signup' ? (
              <>
                כבר יש לך חשבון?{' '}
                <button type="button" onClick={() => setMode('signin')} className="text-teal-600 font-medium hover:underline">
                  כניסה
                </button>
              </>
            ) : (
              <>
                משתמש חדש?{' '}
                <button type="button" onClick={() => setMode('signup')} className="text-teal-600 font-medium hover:underline">
                  צור חשבון
                </button>
              </>
            )}
          </p>
        </div>
      </div>
    </div>
  );
}
