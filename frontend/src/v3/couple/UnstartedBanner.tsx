import { Heart } from 'lucide-react';
import type { CoupleStatus } from './coupleApi';
import { FONT } from './lines';

/** My ongoing couple process on the start screen: a part that never started (the app reloaded on the invite screen)
 *  starts with one tap; a started one opens where it stopped (it may have too few messages for "welcome back") */
export function UnstartedBanner({ session, onStart }: { session: CoupleStatus; onStart: () => void }) {
  const notStarted = !session.me.step || session.me.step === 'S0';
  return (
    <div className="px-4 pt-4" dir="rtl">
      <button
        type="button"
        onClick={onStart}
        className="w-full max-w-[670px] mx-auto flex items-center gap-3 rounded-xl border border-[#9747ff] bg-white
                   px-4 py-3 text-right hover:bg-[rgba(151,71,255,0.06)] transition-colors"
        style={FONT}
      >
        <Heart size={18} className="text-[#9747ff] flex-shrink-0" />
        <span className="text-sm text-[#2d4658]">
          {`${notStarted ? 'התהליך הזוגי שלך מחכה' : 'התהליך הזוגי שלך'}: ״${session.event_title}״ — `}
          <span className="font-semibold text-[#9747ff]">{notStarted ? 'להתחיל את החלק שלי' : 'להמשיך מאיפה שעצרתי'}</span>
        </span>
      </button>
    </div>
  );
}
