interface NotFoundScreenProps {
  onGoToJourney: () => void;
  onStartFresh: () => void;
}

export function NotFoundScreen({ onGoToJourney, onStartFresh }: NotFoundScreenProps) {
  return (
    <div className="h-screen flex flex-col items-center justify-center relative overflow-hidden" dir="rtl">
      <img src="/login-bg.png" alt="" className="absolute inset-0 w-full h-full object-cover" />

      <div className="relative z-10 flex flex-col items-center text-center px-6 max-w-[500px]">
        <p className="text-sm text-[#2d4658]/60" style={{ fontFamily: "'Heebo', sans-serif" }}>404</p>

        <h1
          className="text-[48px] lg:text-[64px] text-[#2d4658] mt-2"
          style={{ fontFamily: "'Karantina', cursive", lineHeight: '1.1' }}
        >
          הדף הזה לא קיים
        </h1>

        <p
          className="text-[18px] text-[#2d4658] mt-4 leading-relaxed"
          style={{ fontFamily: "'Heebo', sans-serif" }}
        >
          אבל המסע שלך ממשיך.
          <br />
          בוא נחזיר אותך למקום שבו אתה צריך להיות.
        </p>

        <button
          type="button"
          onClick={onGoToJourney}
          className="mt-8 w-[260px] h-[50px] rounded-xl bg-[#9747ff] text-white text-base font-medium
                     hover:bg-[#8035e6] transition-colors
                     drop-shadow-[0px_8px_2.9px_rgba(0,0,0,0.12)]"
          style={{ fontFamily: "'Heebo', sans-serif" }}
        >
          חזור למסע שלי
        </button>

        <button
          type="button"
          onClick={onStartFresh}
          className="mt-4 text-sm text-[#2d4658] underline hover:text-[#2d4658]/70 transition-colors"
          style={{ fontFamily: "'Heebo', sans-serif" }}
        >
          התחל מההתחלה
        </button>
      </div>
    </div>
  );
}
