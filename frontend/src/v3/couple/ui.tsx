import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { FONT, TITLE_FONT } from './lines';

export function CoupleScreen({ children }: { children: ReactNode }) {
  return (
    <div className="flex-1 overflow-y-auto pb-14 lg:pb-0 animate-[fadeIn_0.3s_ease-out]" dir="rtl">
      <div className="max-w-[670px] mx-auto px-4 py-8 space-y-6">{children}</div>
    </div>
  );
}

export function ScreenTitle({ children, sub }: { children: ReactNode; sub?: ReactNode }) {
  return (
    <div className="text-center space-y-2">
      <h1 className="text-[36px] sm:text-[40px] text-[#2d4658] leading-[1.3]" style={TITLE_FONT}>{children}</h1>
      {sub && <p className="text-base text-[#2d4658] leading-relaxed" style={FONT}>{sub}</p>}
    </div>
  );
}

export function Panel({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`bg-white rounded-xl border-t-2 border-[#03ffe6] shadow-[0px_0px_3.35px_rgba(0,0,0,0.08)] p-5 ${className}`}>
      {children}
    </div>
  );
}

export function Note({ children }: { children: ReactNode }) {
  return <p className="text-sm text-[rgba(45,70,88,0.7)] leading-relaxed text-right" style={FONT}>{children}</p>;
}

export function PrimaryButton({ children, ...rest }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      {...rest}
      className="min-w-[239px] h-[53px] px-6 rounded-xl bg-[#9747ff] text-white text-base hover:bg-[#8035e6] transition-colors
                 drop-shadow-[0px_8px_2.9px_rgba(0,0,0,0.12)] flex items-center justify-center gap-2
                 disabled:bg-[#d9d9d9] disabled:text-[#999] disabled:cursor-not-allowed"
      style={FONT}
    >
      {children}
    </button>
  );
}

export function SecondaryButton({ children, ...rest }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      {...rest}
      className="flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl border border-[#03ffe6] text-sm text-[#2d4658]
                 hover:bg-[rgba(3,255,230,0.05)] transition-colors disabled:opacity-50"
      style={FONT}
    >
      {children}
    </button>
  );
}

export function Spinner() {
  return (
    <div className="flex justify-center py-10">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-[#03ffe6] border-t-transparent" />
    </div>
  );
}

export function ErrorText({ children }: { children: ReactNode }) {
  return children ? <p className="text-sm text-red-500 text-center" style={FONT}>{children}</p> : null;
}

export const inputClass =
  'w-full h-[44px] px-3 rounded-xl border border-[#e0ddd8] text-sm text-[#2d4658] text-right bg-white '
  + 'placeholder:text-[rgba(45,70,88,0.35)] focus:outline-none focus:border-[#03ffe6] transition-colors';

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-medium text-[#2d4658] text-right mb-1" style={FONT}>{label}</label>
      {children}
      {hint && <p className="text-xs text-[rgba(45,70,88,0.6)] mt-1 text-right" style={FONT}>{hint}</p>}
    </div>
  );
}

/** זכר / נקבה — asked only when the profile has no gender yet */
export function GenderPicker({ value, onChange }: { value: string | null; onChange: (g: 'male' | 'female') => void }) {
  return (
    <div className="flex gap-3 justify-start">
      {([['male', 'זכר'], ['female', 'נקבה']] as const).map(([id, label]) => (
        <button
          key={id}
          type="button"
          onClick={() => onChange(id)}
          className={`h-[44px] px-6 rounded-xl border text-sm transition-colors ${value === id
            ? 'border-[#04c4b1] bg-[rgba(3,255,230,0.3)] text-[#2d4658]'
            : 'border-[#d2d2d2] bg-white text-[#2d4658] hover:border-[#04c4b1]'}`}
          style={FONT}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

/** The four steps of the couple process, impersonal plural so it reads the same for everyone */
export function HowItWorks() {
  const steps = [
    'כותבים כותרת קצרה לאירוע ומזמינים את בן/בת הזוג.',
    'כל אחד עובד לבד ובפרטיות על מה שקרה בתוכו: מה הרגיש, מה עשה, ואיזו אמונה עמדה מאחורי זה.',
    'בסוף שלב הגילוי רואים יחד, זה לצד זה, רק את מה שכל אחד בחר לשתף.',
    'כל אחד ממשיך לבד לבחירה חדשה, ובסוף — התחייבות של כל אחד לחלק שלו.',
  ];
  return (
    <ol className="space-y-3">
      {steps.map((s, i) => (
        <li key={i} className="flex gap-3 items-start text-right">
          <span className="flex-shrink-0 w-7 h-7 rounded-full bg-[#2d4658] text-[#03ffe6] text-sm flex items-center justify-center" style={FONT}>
            {i + 1}
          </span>
          <span className="text-sm text-[#2d4658] leading-relaxed" style={FONT}>{s}</span>
        </li>
      ))}
    </ol>
  );
}
