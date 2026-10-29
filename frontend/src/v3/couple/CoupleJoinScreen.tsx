import { useState } from 'react';
import type { Gender, InvitePreview } from './coupleApi';
import { FONT, gFor, SAFETY_NOTE } from './lines';
import { CoupleScreen, ErrorText, Field, GenderPicker, HowItWorks, inputClass, Note, Panel, PrimaryButton, ScreenTitle, SecondaryButton, Spinner } from './ui';

interface CoupleJoinScreenProps {
  preview: InvitePreview | null;
  defaultName: string;
  profileGender: Gender | null;
  busy: boolean;
  error: string | null;
  onJoin: (name: string, gender: Gender | null) => void;
  onContinueJoined: (conversationId: number) => void;
  onDismiss: () => void;
}

const DEAD_LINK: Record<string, string> = {
  own: 'זה הקישור ששלחת לבן/בת הזוג — הוא מיועד להם. החלק שלך מחכה לך ברשימת השיחות.',
  used: 'ההזמנה הזו כבר נוצלה.',
  expired: 'תוקף ההזמנה פג. אפשר לבקש קישור חדש ממי ששלח אותה.',
  not_found: 'הקישור לא תקין, או שהתהליך המשותף הסתיים.',
};

/** Partner B opened the invite link: who invited, the shared title, how it works — then their own conversation */
export function CoupleJoinScreen({ preview, defaultName, profileGender, busy, error, onJoin, onContinueJoined, onDismiss }: CoupleJoinScreenProps) {
  const [name, setName] = useState(defaultName);
  const [gender, setGender] = useState<Gender | null>(profileGender);

  if (!preview) return <CoupleScreen><Spinner /></CoupleScreen>;

  if (preview.state === 'joined' && preview.conversation_id) {
    return (
      <CoupleScreen>
        <ScreenTitle>כבר הצטרפת</ScreenTitle>
        <div className="flex flex-col items-center gap-3">
          <PrimaryButton onClick={() => onContinueJoined(preview.conversation_id as number)}>להמשך התהליך שלי</PrimaryButton>
        </div>
      </CoupleScreen>
    );
  }

  if (preview.state !== 'valid') {
    return (
      <CoupleScreen>
        <ScreenTitle>תהליך זוגי</ScreenTitle>
        <Panel><Note>{DEAD_LINK[preview.state] ?? DEAD_LINK.not_found}</Note></Panel>
        <div className="flex justify-center"><SecondaryButton onClick={onDismiss}>למסך הבית</SecondaryButton></div>
      </CoupleScreen>
    );
  }

  const gi = gFor(preview.inviter_gender);
  const g = gFor(gender);
  const canJoin = name.trim().length > 0 && gender !== null && !busy;

  return (
    <CoupleScreen>
      <ScreenTitle sub={`״${preview.event_title}״`}>
        {`${preview.inviter_name} ${gi('הזמין', 'הזמינה')} אותך לעבוד יחד על אירוע שחוויתם`}
      </ScreenTitle>

      <Panel className="space-y-4">
        <HowItWorks />
        <Note>
          {`מה ש${g('תכתוב', 'תכתבי')} בשיחה נשאר אצלך. לפני שמשהו מוצג ל${preview.inviter_name} ${g('תראה', 'תראי')} בדיוק מה יוצג, `
            + `ו${g('תוכל', 'תוכלי')} לתקן או להסתיר כל שורה. השיחה עצמה לא מוצגת אף פעם.`}
        </Note>
      </Panel>

      <Panel className="space-y-4">
        <Field label={`השם שיופיע ל${preview.inviter_name}`}>
          <input type="text" value={name} maxLength={40} onChange={(e) => setName(e.target.value)} className={inputClass} style={FONT} />
        </Field>
        {profileGender === null && (
          <Field label="איך לפנות אליך?">
            <GenderPicker value={gender} onChange={setGender} />
          </Field>
        )}
      </Panel>

      <Note>{SAFETY_NOTE}</Note>
      <ErrorText>{error}</ErrorText>

      <div className="flex flex-col items-center gap-3">
        <PrimaryButton disabled={!canJoin} onClick={() => onJoin(name.trim(), gender)}>
          {busy ? <span className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" /> : 'להצטרף ולהתחיל'}
        </PrimaryButton>
        <SecondaryButton onClick={onDismiss}>לא עכשיו</SecondaryButton>
      </div>
    </CoupleScreen>
  );
}
