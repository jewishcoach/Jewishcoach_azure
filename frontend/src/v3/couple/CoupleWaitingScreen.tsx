import { useState } from 'react';
import type { Checkpoint, CoupleStatus } from './coupleApi';
import { gFor } from './lines';
import { ShareLinkButtons } from './CoupleInviteScreen';
import { CoupleScreen, Note, Panel, PrimaryButton, ScreenTitle, SecondaryButton } from './ui';

interface CoupleWaitingScreenProps {
  checkpoint: Checkpoint;
  status: CoupleStatus | null;
  remind: { text: string; link: string } | null;
  onPrepareRemind: () => void;
  onCancel: () => void;
  onContinueAlone: () => void;
}

/** Only status — nothing of the partner's work — until both approved; the hook polls and opens the screen */
export function CoupleWaitingScreen({ checkpoint, status, remind, onPrepareRemind, onCancel, onContinueAlone }: CoupleWaitingScreenProps) {
  const [confirmCancel, setConfirmCancel] = useState(false);
  const g = gFor(status?.me.gender);
  const partner = status?.partner;
  const gp = gFor(partner?.gender);
  const who = partner?.name || 'בן/בת הזוג';

  if (status?.status === 'cancelled') {
    return (
      <CoupleScreen>
        <ScreenTitle>התהליך המשותף הסתיים</ScreenTitle>
        <Panel><Note>מה שאישרת לא יוצג. התהליך שלך ממשיך כתהליך אישי, מאותה נקודה.</Note></Panel>
        <div className="flex justify-center">
          <PrimaryButton onClick={onContinueAlone}>{checkpoint === 'mirror' ? 'להמשך התהליך שלי' : 'סיום'}</PrimaryButton>
        </div>
      </CoupleScreen>
    );
  }

  const partnerLine = !partner
    ? 'בן/בת הזוג עוד לא הצטרפו.'
    : `${who} עוד לא ${gp('סיים', 'סיימה')} את החלק ${gp('שלו', 'שלה')}.`;

  return (
    <CoupleScreen>
      <ScreenTitle sub={checkpoint === 'mirror'
        ? 'מה שאישרת שמור, ולא יוצג עד ששניכם תסיימו את שלב הגילוי.'
        : 'ההתחייבות שלך שמורה, ותוצג כששניכם תסיימו.'}
      >
        {checkpoint === 'mirror' ? 'החלק שלך הסתיים' : 'ההתחייבות שלך נשמרה'}
      </ScreenTitle>

      <Panel className="space-y-4">
        <Note>{partnerLine}</Note>
        <Note>{`המסך המשותף ייפתח כאן מעצמו, ונשלח לך מייל. ${g('אתה יכול', 'את יכולה')} לסגור את האפליקציה ולחזור אחר כך.`}</Note>
        {remind
          ? <ShareLinkButtons text={remind.text} link={remind.link} />
          : (
            <div className="flex justify-center">
              <SecondaryButton onClick={onPrepareRemind}>{partner ? 'תזכורת לבן/בת הזוג' : 'לשלוח שוב את ההזמנה'}</SecondaryButton>
            </div>
          )}
      </Panel>

      <div className="flex flex-col items-center gap-3">
        {confirmCancel ? (
          <Panel className="space-y-3 w-full">
            <Note>{`לבטל את התהליך המשותף? כל אחד ימשיך לבד, ומה שאישרת לא יוצג ל${who}.`}</Note>
            <div className="flex justify-center gap-3">
              <SecondaryButton onClick={onCancel}>כן, לבטל</SecondaryButton>
              <SecondaryButton onClick={() => setConfirmCancel(false)}>לא, להמשיך לחכות</SecondaryButton>
            </div>
          </Panel>
        ) : (
          <button type="button" onClick={() => setConfirmCancel(true)} className="text-sm text-[rgba(45,70,88,0.6)] underline">
            לא רוצה לחכות? לבטל את התהליך המשותף
          </button>
        )}
      </div>
    </CoupleScreen>
  );
}
