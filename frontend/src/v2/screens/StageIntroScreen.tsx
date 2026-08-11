import type { StageIntroPayload } from '../types';

const STAGE_TREES: Record<string, string> = {
  identification: '/trees/tree-identification.png',
  discovery: '/trees/tree-discovery.png',
  kamaz: '/trees/tree-kamaz.png',
  choice: '/trees/tree-self-discovery.png',
  vision: '/trees/tree-vision.png',
  change: '/trees/tree-change.png',
};

const STAGE_DESCRIPTIONS: Record<string, { time: string; description: string }> = {
  identification: {
    time: 'כ - 10 דקות',
    description: 'בשלב הזה נעצור לרגע כדי לראות מה באמת קורה בך.\nנזהה את הרגשות, המחשבות והפעולות שחוזרים על עצמם — בלי לשפוט, רק להתבונן.',
  },
  discovery: {
    time: 'כ - 7 דקות',
    description: 'שינוי מתחיל כשעוצרים לרגע להתבונן.\nבשלב הזה נגלה מה באמת חשוב לך — לא מה שמצופה ממך, אלא מה שנכון עבורך.\nאין כאן תשובה נכונה. יש רק את המקום שממנו אתה מתחיל היום.',
  },
  kamaz: {
    time: 'כ - 10 דקות',
    description: 'בשלב הזה נבנה יחד את כרטיס מהות הזהות שלך.\nנזהה את כוחות המקור והטבע שפועלים בך — כדי שתוכל לבחור מתוך מודעות.',
  },
  choice: {
    time: 'כ - 5 דקות',
    description: 'הגענו לרגע הבחירה.\nאחרי שהתבוננת בדפוס, בעמדה ובכוחות — עכשיו תבחר איך אתה רוצה לחיות מהיום.',
  },
  vision: {
    time: 'כ - 5 דקות',
    description: 'בשלב האחרון נצייר יחד את החזון שלך.\nאיך נראים החיים כשאתה חי מתוך הבחירה החדשה? ומה הצעד הראשון?',
  },
};

interface StageIntroScreenProps {
  payload: StageIntroPayload;
  onSubmit: (answers: Record<string, string[]>) => void;
  isSubmitting: boolean;
  previousInsights?: string[];
}

export function StageIntroScreen({ payload, onSubmit, isSubmitting, previousInsights }: StageIntroScreenProps) {
  const stageId = payload.stage_id || 'discovery';
  const treeImg = STAGE_TREES[stageId] || STAGE_TREES.discovery;
  const stageInfo = STAGE_DESCRIPTIONS[stageId] || STAGE_DESCRIPTIONS.discovery;

  const handleStart = () => {
    if (!isSubmitting) {
      onSubmit({});
    }
  };

  return (
    <div className="flex-1 flex flex-col items-center px-4 sm:px-6 py-8 sm:py-12 overflow-y-auto" dir="rtl">
      <div className="max-w-[724px] w-full space-y-8">
        {/* Title */}
        <h1
          className="text-[40px] text-[#2d4658] text-center"
          style={{ fontFamily: "'Karantina', cursive", lineHeight: '77px' }}
        >
          ברוך הבא לשלב הבא שלך
        </h1>

        {/* Main card */}
        <div className="bg-white rounded-lg shadow-[0px_0px_6.25px_rgba(0,0,0,0.14)] flex flex-col items-center py-8 px-6">
          {/* Tree image */}
          <div className="w-[175px] h-[212px] mb-4">
            <img src={treeImg} alt="" className="w-full h-full object-contain" />
          </div>

          {/* Stage name */}
          <h2
            className="text-[40px] text-[#00897b] text-center"
            style={{ fontFamily: "'Karantina', cursive", lineHeight: '77px' }}
          >
            {payload.stage_title}
          </h2>

          {/* Time estimate */}
          <p
            className="text-sm text-[#2d4658] text-center mb-4"
            style={{ fontFamily: "'Assistant', sans-serif" }}
          >
            {stageInfo.time}
          </p>

          {/* Description */}
          <p
            className="text-sm text-[#2d4658] text-center max-w-[591px] leading-[21px] whitespace-pre-line"
            style={{ fontFamily: "'Assistant', sans-serif" }}
          >
            {stageInfo.description}
          </p>
        </div>

        {/* Start button */}
        <div className="flex justify-center">
          <button
            type="button"
            onClick={handleStart}
            disabled={isSubmitting}
            className="w-[239px] h-[53px] rounded-xl bg-[#9747ff] text-white text-base hover:bg-[#8035e6] drop-shadow-[0px_8px_2.9px_rgba(0,0,0,0.12)] transition-colors disabled:opacity-50"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            {isSubmitting ? '...' : 'אני מוכן להתחיל'}
          </button>
        </div>

        {/* Previous insights cards */}
        {previousInsights && previousInsights.length > 0 && (
          <div className="space-y-4">
            <p
              className="text-base text-[#2d4658] text-right"
              style={{ fontFamily: "'Heebo', sans-serif" }}
            >
              במה התבוננו יחד בשלב הקודם?
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {previousInsights.slice(0, 3).map((insight, idx) => (
                <div
                  key={idx}
                  className="bg-white border border-[#e0ddd8] rounded-lg p-6 flex items-center gap-4"
                >
                  <div className="flex-1 text-right">
                    <p
                      className="text-sm text-[#009081] font-semibold mb-1"
                      style={{ fontFamily: "'Heebo', sans-serif" }}
                    >
                      {idx === 0 ? 'תובנה שגיליתי' : idx === 1 ? 'מה התגלה' : 'רגע של בהירות'}
                    </p>
                    <p
                      className="text-sm text-[rgba(45,45,45,0.9)]"
                      style={{ fontFamily: "'Assistant', sans-serif" }}
                    >
                      {insight}
                    </p>
                  </div>
                  <div className="w-[54px] h-[54px] rounded-full bg-[rgba(3,255,230,0.2)] flex items-center justify-center shrink-0">
                    <span className="text-[#03ffe6] text-lg">✦</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
