import { SignIn, SignUp } from '@clerk/clerk-react';
import { useState, useRef } from 'react';

interface LoginScreenProps {
  onSignedIn?: () => void;
}

// Benny's welcome video (Nov 9, replaces the 2:49 benny-intro.mp3): 53 s, Hebrew subtitles burned in, made in
// landing-video/ (welcome_script.md). Nothing is downloaded until play (preload="none"); the poster is Benny's photo.
// Before the first play our own button sits over the poster; after it the browser's controls take over.
function BennyWelcomeVideo({ size = 'lg' }: { size?: 'sm' | 'lg' }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [started, setStarted] = useState(false);

  const play = async () => {
    const el = videoRef.current;
    if (!el) return;
    setStarted(true);
    try {
      await el.play();
    } catch (e) {
      console.error('Video play failed:', e);
    }
  };

  const btnSize = size === 'lg' ? 'w-16 h-16' : 'w-12 h-12';
  const iconSize = size === 'lg' ? 28 : 22;

  return (
    <div className="aspect-video bg-[#2d4658] rounded-xl overflow-hidden relative shadow-[0px_27px_14.2px_rgba(0,0,0,0.25)]"
         style={size === 'sm' ? { boxShadow: '0px 14px 8px rgba(0,0,0,0.2)' } : undefined}>
      <video
        ref={videoRef}
        src="/welcome.mp4"
        poster="/welcome-poster.jpg"
        preload="none"
        playsInline
        controls={started}
        className="absolute inset-0 w-full h-full object-cover"
        aria-label="סרטון פתיחה מבני גל"
      />
      {!started && (
        <button type="button" onClick={play} aria-label="הפעלת הסרטון של בני"
          className="absolute inset-0 z-10 group">
          {/* in the navy beside Benny's photo (the poster's middle third), so it never covers him */}
          <span className="absolute left-[16.5%] top-1/2 -translate-x-1/2 -translate-y-1/2">
            <span className={`${btnSize} rounded-full bg-black/45 group-hover:bg-black/60 backdrop-blur-sm ring-2 ring-white/70 flex items-center justify-center transition-colors`}>
              <svg width={iconSize} height={iconSize} viewBox="0 0 24 24" fill="white" style={{ marginInlineStart: 3 }}><path d="M8 5v14l11-7z"/></svg>
            </span>
          </span>
        </button>
      )}
    </div>
  );
}

export function LoginScreen({ onSignedIn: _onSignedIn }: LoginScreenProps) {
  const [mode, setMode] = useState<'signin' | 'signup'>('signup');

  return (
    <div className="h-screen flex" dir="rtl">
      {/* Right side — auth form (dark background) */}
      <div className="flex-1 flex flex-col items-center justify-between px-5 lg:px-6 py-8 lg:py-10 overflow-hidden bg-[#2d4658]">
        <div className="w-full max-w-[483px] space-y-4 flex-1 flex flex-col justify-center">
          {/* Mobile-only hero section: video */}
          <div className="lg:hidden w-full space-y-4 mb-6">
            <p
              className="text-[20px] text-white text-center tracking-[-0.5px]"
              style={{ fontFamily: "'Heebo', sans-serif", lineHeight: '32px' }}
            >
              כמה מילים אישיות עבורך מבני גל לפני שמתחילים
            </p>
            <BennyWelcomeVideo size="sm" />
          </div>

          {/* Title */}
          <div className="text-center">
            <h1
              className="text-[48px] lg:text-[75px] text-white"
              style={{ fontFamily: "'Karantina', cursive", lineHeight: '1.03' }}
            >
              {mode === 'signup' ? 'נפגשים בפעם הראשונה' : 'ברוך הבא למסע שלך'}
            </h1>
            {mode === 'signin' && (
              <p className="text-[17px] text-[#fff3f3] mt-2" style={{ fontFamily: "'Heebo', sans-serif" }}>
                איך תרצה להמשיך?
              </p>
            )}
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
                    socialButtonsBlockButton: 'rounded-xl border-[0.8px] border-[#e0ddd8] py-3 bg-white text-[13px] font-medium shadow-[0px_1px_2px_rgba(0,0,0,0.1)]',
                    formFieldInput: 'rounded-xl border-[0.8px] border-[#e0ddd8] bg-white text-right',
                    formFieldLabel: 'text-white text-xs',
                    formButtonPrimary: 'rounded-xl bg-[#9747ff] hover:bg-[#8035e6] drop-shadow-[0px_8px_2.9px_rgba(0,0,0,0.12)] text-[15px] font-medium',
                    footerAction: 'hidden',
                    dividerLine: 'bg-[#e0ddd8]',
                    dividerText: 'text-white',
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
                    socialButtonsBlockButton: 'rounded-xl border-[0.8px] border-[#e0ddd8] py-3 bg-white text-[13px] font-medium shadow-[0px_1px_2px_rgba(0,0,0,0.1)]',
                    formFieldInput: 'rounded-xl border-[0.8px] border-[#e0ddd8] bg-white text-right',
                    formFieldLabel: 'text-white text-xs',
                    formButtonPrimary: 'rounded-xl bg-[#9747ff] hover:bg-[#8035e6] drop-shadow-[0px_8px_2.9px_rgba(0,0,0,0.12)] text-[15px] font-medium',
                    footerAction: 'hidden',
                    dividerLine: 'bg-[#e0ddd8]',
                    dividerText: 'text-white',
                  },
                }}
              />
            )}
          </div>

          {/* Toggle mode + terms */}
          <div className="space-y-2">
            {mode === 'signup' && (
              <p className="text-center text-[16px]" style={{ fontFamily: "'Assistant', sans-serif" }}>
                <span className="text-[#03ffe6]">בהרשמה אתה מסכים ל</span>
                <span className="text-[#03ffe6] font-semibold">תנאי השימוש ולמדיניות הפרטיות</span>
              </p>
            )}
            <p className="text-center text-[13px]" style={{ fontFamily: "'Assistant', sans-serif" }}>
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

        {/* Bottom motivational text */}
        <p
          className="text-[25px] text-white text-center tracking-[-1px] mt-6 max-w-[450px]"
          style={{ fontFamily: "'Heebo', sans-serif", lineHeight: '41px' }}
        >
          בכמה הדקות הקרובות לא נחפש פתרונות. אלא
          <br />
          נתחיל לבנות את האמון בדרך שלך.
        </p>
      </div>

      {/* Left side — video + text (sky background) */}
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-between p-10 relative overflow-hidden">
        {/* Background image — sky with clouds */}
        <img src="/login-bg.png" alt="" className="absolute inset-0 w-full h-full object-cover" />

        <div className="space-y-4 relative z-10">
          <p
            className="text-[25px] text-[#2d4658] text-center tracking-[-1px]"
            style={{ fontFamily: "'Heebo', sans-serif", lineHeight: '41px' }}
          >
            כמה מילים אישיות עבורך מבני גל לפני שמתחילים
          </p>
          <BennyWelcomeVideo size="lg" />
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

        <div className="relative z-10" />
      </div>
    </div>
  );
}
