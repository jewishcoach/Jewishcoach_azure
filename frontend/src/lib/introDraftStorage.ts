/** Local draft from pre-login acquaintance flow; synced to profile/preferences after Clerk sign-in. */

export type IntroGender = 'female' | 'male' | 'non_binary' | 'prefer_not';

export type IntroDraftV1 = {
  version: 1;
  displayName: string;
  age: number | null;
  gender: IntroGender | null;
  intentions: string[];
  completed: boolean;
};

const KEY = 'jewishcoach_intro_draft_v1';

export function loadIntroDraft(): IntroDraftV1 | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    const data = JSON.parse(raw) as IntroDraftV1;
    if (data?.version !== 1) return null;
    return data;
  } catch {
    return null;
  }
}

export function saveIntroDraft(draft: IntroDraftV1): void {
  localStorage.setItem(KEY, JSON.stringify(draft));
}

export function clearIntroDraft(): void {
  localStorage.removeItem(KEY);
}
