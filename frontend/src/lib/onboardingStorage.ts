/** משלים זאת רק אחרי זרימת ההיכרות הנוכחית (גרסת acquaintance). */
const INTRO_ACQUAINTANCE_KEY = 'jewishcoach_intro_acquaintance_v1';

/** מפתח ישן מהקרוסלה הקודמת — לא משמש יותר לדילוג על המסכים */
const LEGACY_ONBOARDING_KEY = 'jewishcoach_onboarding_seen';

export function hasSeenOnboarding(): boolean {
  if (localStorage.getItem(INTRO_ACQUAINTANCE_KEY) === 'true') return true;
  /** משתמשים שסיימו את הקרוסלה הישנה — מסומנים כאן פעם אחת בלי להציג שוב את ההיכרות */
  if (localStorage.getItem(LEGACY_ONBOARDING_KEY) === 'true') {
    localStorage.setItem(INTRO_ACQUAINTANCE_KEY, 'true');
    localStorage.removeItem(LEGACY_ONBOARDING_KEY);
    return true;
  }
  return false;
}

export function setOnboardingComplete(): void {
  localStorage.setItem(INTRO_ACQUAINTANCE_KEY, 'true');
  localStorage.removeItem(LEGACY_ONBOARDING_KEY);
}

/** נקרא בעת מעבר ממצב מחובר למנותק – כך שבכניסה הבאה יוצג שוב תהליך ההכרות */
export function clearOnboardingOnSignOut(): void {
  localStorage.removeItem(INTRO_ACQUAINTANCE_KEY);
  localStorage.removeItem(LEGACY_ONBOARDING_KEY);
}

/** איפוס מלא לבדיקות / תמיכה (וגם מ-hash בממשק). */
export function clearAllIntroGateKeys(): void {
  localStorage.removeItem(INTRO_ACQUAINTANCE_KEY);
  localStorage.removeItem(LEGACY_ONBOARDING_KEY);
}
