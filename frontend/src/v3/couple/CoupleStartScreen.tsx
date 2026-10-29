import { useState } from 'react';
import type { Gender } from './coupleApi';
import { FONT, gFor, SAFETY_NOTE } from './lines';
import { CoupleScreen, ErrorText, Field, GenderPicker, HowItWorks, inputClass, Note, Panel, PrimaryButton, ScreenTitle, SecondaryButton } from './ui';

interface CoupleStartScreenProps {
  defaultName: string;
  profileGender: Gender | null;
  busy: boolean;
  error: string | null;
  onSubmit: (title: string, name: string, gender: Gender | null) => void;
  onBack: () => void;
}

/** Partner A: what the process is, the shared title, and the name the partner will see */
export function CoupleStartScreen({ defaultName, profileGender, busy, error, onSubmit, onBack }: CoupleStartScreenProps) {
  const [title, setTitle] = useState('');
  const [name, setName] = useState(defaultName);
  const [gender, setGender] = useState<Gender | null>(profileGender);
  const g = gFor(gender);
  const canSubmit = title.trim().length >= 2 && name.trim().length > 0 && gender !== null && !busy;

  return (
    <CoupleScreen>
      <ScreenTitle sub="אירוע אחד, שני עולמות פנימיים.">תהליך זוגי</ScreenTitle>

      <Panel className="space-y-4">
        <HowItWorks />
        <Note>
          {`מה ש${g('תכתוב', 'תכתבי')} בשיחה נשאר אצלך. לפני שמשהו מוצג לבן/בת הזוג ${g('תראה', 'תראי')} בדיוק מה יוצג, `
            + `ו${g('תוכל', 'תוכלי')} לתקן או להסתיר כל שורה. השיחה עצמה לא מוצגת אף פעם.`}
        </Note>
      </Panel>

      <Panel className="space-y-4">
        <Field label="כותרת לאירוע" hint="בן/בת הזוג יראו רק את הכותרת הזו. את הסיפור כל אחד מספר בעצמו.">
          <input
            type="text"
            value={title}
            maxLength={80}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="קצרה ועניינית, בלי האשמה: מתי ועל מה. למשל: הוויכוח על ההוצאות, מוצאי שבת"
            className={inputClass}
            style={FONT}
          />
        </Field>
        <Field label="השם שיופיע לבן/בת הזוג">
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
        <PrimaryButton disabled={!canSubmit} onClick={() => onSubmit(title.trim(), name.trim(), gender)}>
          {busy ? <span className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" /> : 'ליצור קישור הזמנה'}
        </PrimaryButton>
        <SecondaryButton onClick={onBack}>חזרה</SecondaryButton>
      </div>
    </CoupleScreen>
  );
}
