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
      <div className="relative bg-white rounded-2xl shadow-xl max-w-[440px] w-[90%] px-8 pt-10 pb-8 space-y-6 animate-[fadeIn_0.2s_ease-out]">
        {/* Tree illustration */}
        <div className="flex justify-center">
          <img src="/tree-illustration.png" alt="" className="w-20 h-20 object-contain" onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
        </div>

        {/* Title */}
        <h2
          className="text-[24px] font-bold text-[#2d4658] text-center"
          style={{ fontFamily: "'Heebo', sans-serif" }}
        >
          המסע שלך נשמר.
        </h2>

        {/* Body text */}
        <p
          className="text-[15px] text-[#2d4658] text-center leading-relaxed"
          style={{ fontFamily: "'Heebo', sans-serif" }}
        >
          לפעמים נכון לעצור להנוע. כשתרגיש מוכן, תמיד אפשר
          <br />
          להמשיך בדיוק מהמקום שבו עצרת.
          <br />
          מה תרצה לעשות עכשיו?
        </p>

        {/* Buttons */}
        <div className="flex items-center gap-3 pt-2">
          <button
            type="button"
            onClick={onGoHome}
            className="flex-1 h-[48px] rounded-xl border border-[#03ffe6] text-[#2d4658] text-[15px] font-medium
                       hover:bg-[rgba(3,255,230,0.05)] transition-colors"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            חזרה לעמוד הבית
          </button>
          <button
            type="button"
            onClick={onContinue}
            className="flex-1 h-[48px] rounded-xl bg-[#03ffe6] text-[#2d4658] text-[15px] font-semibold
                       hover:bg-[#02e6d0] transition-colors"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            נמשיך מאיפה שעצרנו
          </button>
        </div>
      </div>
    </div>
  );
}
