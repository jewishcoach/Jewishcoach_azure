const ONBOARDING_STORAGE_KEY = 'jewishcoach_onboarding_seen';

export function hasSeenOnboarding(): boolean {
  return localStorage.getItem(ONBOARDING_STORAGE_KEY) === 'true';
}

export function setOnboardingComplete(): void {
  localStorage.setItem(ONBOARDING_STORAGE_KEY, 'true');
}

/** נקרא בעת התנתקות – כך שבכניסה הבאה יוצג שוב תהליך ההכרות */
export function clearOnboardingOnSignOut(): void {
  localStorage.removeItem(ONBOARDING_STORAGE_KEY);
}

/** נקרא בעת התנתקות – כך שבכניסה הבאה יוצג שוב תהליך ההכרות */
export function clearOnboardingOnSignOut(): void {
  localStorage.removeItem(ONBOARDING_STORAGE_KEY);
}
