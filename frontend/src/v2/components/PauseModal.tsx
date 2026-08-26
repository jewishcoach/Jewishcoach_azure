const STAGE_TREES = [
  '/trees/tree-1.png',
  '/trees/tree-2.png',
  '/trees/tree-3.png',
  '/trees/tree-4.png',
  '/trees/tree-5.png',
];

interface PauseModalProps {
  isOpen: boolean;
  stageNumber?: number;
  onContinue: () => void;
  onGoHome: () => void;
}

export function PauseModal({ isOpen, stageNumber = 1, onContinue, onGoHome }: PauseModalProps) {
  if (!isOpen) return null;

  const treeImg = STAGE_TREES[Math.min(stageNumber - 1, STAGE_TREES.length - 1)];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" dir="rtl">
      {/* Overlay */}
      <div className="absolute inset-0 bg-black/40" onClick={onContinue} />

      {/* Card */}
      <div className="relative bg-white rounded-2xl shadow-xl max-w-[560px] w-[90%] px-10 pt-16 pb-8 space-y-6 animate-[fadeIn_0.2s_ease-out]">
        {/* Tree — overflows above the card */}
        <div className="absolute -top-14 left-1/2 -translate-x-1/2">
          <img src={treeImg} alt="" className="w-28 h-28 object-contain drop-shadow-md" />
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
