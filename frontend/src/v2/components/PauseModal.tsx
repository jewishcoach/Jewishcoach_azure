import { TreePine } from 'lucide-react';

interface PauseModalProps {
  isOpen: boolean;
  onContinue: () => void;
  onGoHome: () => void;
}

export function PauseModal({ isOpen, onContinue, onGoHome }: PauseModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" dir="rtl">
      {/* Overlay */}
      <div className="absolute inset-0 bg-black/40" onClick={onContinue} />

      {/* Card */}
      <div className="relative bg-white rounded-2xl shadow-xl max-w-[420px] w-[90%] p-8 space-y-5 animate-[fadeIn_0.2s_ease-out]">
        {/* Tree illustration */}
        <div className="flex justify-center">
          <div className="w-16 h-16 rounded-full bg-[rgba(3,255,230,0.1)] flex items-center justify-center">
            <TreePine size={32} className="text-[#2d4658]" />
          </div>
        </div>

        {/* Title */}
        <h2
          className="text-[22px] font-semibold text-[#2d4658] text-center"
          style={{ fontFamily: "'Heebo', sans-serif" }}
        >
          המסע שלך נשמר.
        </h2>

        {/* Body text */}
        <p
          className="text-sm text-[#2d4658] text-center leading-relaxed"
          style={{ fontFamily: "'Heebo', sans-serif" }}
        >
          לפעמים נכון לעצור להנוע. כשתרגיש מוכן, תמיד אפשר להמשיך בדיוק מהמקום שבו עצרת.
          <br />
          מה תרצה לעשות עכשיו?
        </p>

        {/* Buttons */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onGoHome}
            className="flex-1 h-[46px] rounded-xl border border-[#03ffe6] text-[#2d4658] text-sm font-medium
                       hover:bg-[rgba(3,255,230,0.05)] transition-colors"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            חזרה לעמוד הבית
          </button>
          <button
            type="button"
            onClick={onContinue}
            className="flex-1 h-[46px] rounded-xl bg-[#9747ff] text-white text-sm font-medium
                       hover:bg-[#8035e6] transition-colors
                       drop-shadow-[0px_4px_2px_rgba(0,0,0,0.1)]"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            נמשיך מאיפה שעצרנו
          </button>
        </div>
      </div>
    </div>
  );
}
