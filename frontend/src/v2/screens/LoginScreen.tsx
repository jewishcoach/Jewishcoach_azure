import { SignIn, SignUp } from '@clerk/clerk-react';
import { useState, useRef } from 'react';

interface LoginScreenProps {
  onSignedIn?: () => void;
}

function BennyAudioPlayer({ size = 'lg' }: { size?: 'sm' | 'lg' }) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(172);

  const toggle = async () => {
    const el = audioRef.current;
    if (!el) return;
    if (playing) {
      el.pause();
      setPlaying(false);
    } else {
      try {
        await el.play();
        setPlaying(true);
      } catch (e) {
        console.error('Audio play failed:', e);
      }
    }
  };

  const formatTime = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;
  const btnSize = size === 'lg' ? 'w-14 h-14' : 'w-10 h-10';
  const iconSize = size === 'lg' ? 24 : 20;

  return (
    <div className="aspect-video bg-[#fffdfb] rounded-xl flex items-center justify-center overflow-hidden relative shadow-[0px_27px_14.2px_rgba(0,0,0,0.25)]"
         style={size === 'sm' ? { boxShadow: '0px 14px 8px rgba(0,0,0,0.2)' } : undefined}>
      <div className="absolute inset-0 bg-slate-700" />
      <audio
        ref={audioRef}
        src="/benny-intro.mp3"
        preload="auto"
        onTimeUpdate={() => {
          const el = audioRef.current;
          if (el) { setCurrentTime(el.currentTime); setProgress(el.duration ? (el.currentTime / el.duration) * 100 : 0); }
        }}
        onLoadedMetadata={() => { if (audioRef.current) setDuration(audioRef.current.duration); }}
        onEnded={() => { setPlaying(false); setProgress(0); setCurrentTime(0); }}
      />
      <div className="relative z-10 flex flex-col items-center gap-3">
        <button type="button" onClick={toggle} className={`${btnSize} rounded-full bg-[rgba(150,150,150,0.69)] hover:bg-[rgba(150,150,150,0.9)] flex items-center justify-center transition-colors`}>
          {playing ? (
            <svg width={iconSize} height={iconSize} viewBox="0 0 24 24" fill="white"><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></svg>
          ) : (
            <svg width={iconSize} height={iconSize} viewBox="0 0 24 24" fill="white"><path d="M8 5v14l11-7z"/></svg>
          )}
        </button>
        <span className={`${size === 'lg' ? 'text-sm' : 'text-xs'} font-semibold text-white`} style={{ fontFamily: "'Assistant', sans-serif" }}>
          {playing ? `${formatTime(currentTime)} / ${formatTime(duration)}` : `${formatTime(duration)}`}
        </span>
      </div>
      {playing && (
        <div className="absolute bottom-0 left-0 right-0 h-1 bg-white/20">
          <div className="h-full bg-[#03ffe6] transition-all duration-300" style={{ width: `${progress}%` }} />
        </div>
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
              className="text-[20px] text-[#2d4658] text-center tracking-[-0.5px]"
              style={{ fontFamily: "'Heebo', sans-serif", lineHeight: '32px' }}
            >
              כמה מילים אישיות עבורך מבני גל לפני שמתחילים
            </p>
            <BennyAudioPlayer size="sm" />
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
          <BennyAudioPlayer size="lg" />
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
