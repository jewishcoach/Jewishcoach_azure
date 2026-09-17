import type { ReactNode } from 'react';

interface CardShellProps {
  children: ReactNode;
  className?: string;
  titleHe?: string;
  instructionHe?: string;
}

export function CardShell({ children, className, titleHe, instructionHe }: CardShellProps) {
  return (
    <div
      dir="rtl"
      className={`
        bg-white rounded-xl border-t-2 border-[#03ffe6]
        shadow-[0px_0px_3.35px_rgba(0,0,0,0.08)]
        animate-[fadeIn_0.3s_ease-out]
        w-full max-w-[662px]
        ${className || ''}
      `}
    >
      {titleHe && (
        <div className="px-5 pt-5 pb-2 border-b border-[#e0ddd8]">
          <h3
            className="text-base font-semibold text-[#2d4658]"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            {titleHe}
          </h3>
          {instructionHe && (
            <p
              className="text-sm text-[rgba(45,70,88,0.6)] mt-1 leading-relaxed"
              style={{ fontFamily: "'Assistant', sans-serif" }}
            >
              {instructionHe}
            </p>
          )}
        </div>
      )}
      <div className="p-5">
        {children}
      </div>
    </div>
  );
}
