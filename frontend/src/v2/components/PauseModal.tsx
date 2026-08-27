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
    <div className="fixed inset-0 lg:right-[330px] z-50 flex items-center justify-center" dir="rtl">
      {/* Overlay */}
      <div className="absolute inset-0 bg-black/40" onClick={onContinue} />

      {/* Card */}
      <div className="relative bg-white rounded-2xl shadow-xl max-w-[580px] w-[92%] px-8 pt-14 pb-7 space-y-4 animate-[fadeIn_0.2s_ease-out]">
        {/* Tree — overflows above the card */}
        <div className="absolute -top-16 left-1/2 -translate-x-1/2">
          <img src={treeImg} alt="" className="w-32 h-32 object-contain drop-shadow-md" />
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
          לפעמים נכון לעצור ולנוח. כשתרגיש מוכן, תמיד אפשר
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
            className="w-[40%] h-[46px] rounded-xl border border-[#03ffe6] text-[#2d4658] text-[14px] font-medium
                       hover:bg-[rgba(3,255,230,0.05)] transition-colors"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            חזרה לעמוד הבית
          </button>
          <button
            type="button"
            onClick={onContinue}
            className="flex-1 h-[46px] rounded-xl bg-[#9747ff] text-white text-[14px] font-semibold
                       hover:bg-[#8035e6] transition-colors"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            נמשיך מאיפה שעצרנו
          </button>
        </div>
      </div>
    </div>
  );
}
