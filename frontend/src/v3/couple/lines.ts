import type { Checkpoint, Gender } from './coupleApi';

// Headings of the shared-screen lines (first person, the same for both genders) — drafts for the expert to approve.
// Line ids and their order come from the backend (services/couple_service.py MIRROR_LINE_IDS / COMMITMENT_LINE_IDS).
export const LINE_HEADINGS: Record<Checkpoint, Record<string, string>> = {
  mirror: {
    emotions: 'מה הרגשתי',
    thought: 'מה עבר לי בראש',
    action: 'מה עשיתי',
    desired_emotion: 'איך רציתי להרגיש',
    desired_action: 'מה רציתי לעשות',
    pattern: 'הדפוס שלי',
    paradigm: 'מה עומד מאחורי זה',
    stance: 'האמונה שלי',
    trigger: 'הכפתור שלי',
    gains: 'מה זה נותן לי',
    losses: 'מה זה עולה לי',
  },
  commitment: {
    new_stance: 'העמדה החדשה שלי',
    new_action: 'מה אעשה אחרת',
    request: 'הבקשה שלי',
  },
};

export const LINE_ORDER: Record<Checkpoint, string[]> = {
  mirror: Object.keys(LINE_HEADINGS.mirror),
  commitment: Object.keys(LINE_HEADINGS.commitment),
};

/** g('בחר', 'בחרי') for a known gender — the masculine form when unknown, like the rest of the app */
export const gFor = (gender: Gender | null | undefined) => (m: string, f: string) => (gender === 'female' ? f : m);

export const FONT = { fontFamily: "'Heebo', sans-serif" };
export const TITLE_FONT = { fontFamily: "'Karantina', cursive" };

// Shown on the opening screens — numbers to verify before launch
export const SAFETY_NOTE =
  'התהליך מיועד לוויכוחים ולרגעים טעונים בזוגיות. אם יש פחד מבן/בת הזוג או אלימות — זה לא המקום. '
  + 'אפשר לפנות בדיסקרטיות למוקד 118 של משרד הרווחה (אלימות במשפחה), ובמצב מסוכן — למשטרה 100.';

/** The invite the inviter sends (WhatsApp / share sheet), in the inviter's gender */
export function inviteMessage(name: string, gender: Gender | null, title: string, link: string) {
  const g = gFor(gender);
  return `${name} ${g('מזמין', 'מזמינה')} אותך לעבוד יחד על אירוע שחווינו: ״${title}״.\n`
    + 'כל אחד עובד לבד ובפרטיות, ובסוף רואים יחד רק את מה שכל אחד בחר לשתף.\n'
    + link;
}
