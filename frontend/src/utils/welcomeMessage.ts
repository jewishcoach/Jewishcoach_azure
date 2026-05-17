import type { I18nT } from '../i18nT';
import { stripUndefined } from './messageContent';

/** Strip bidi / zero-width so "שלום" + name does not visually glue spaces (שלוםישי) */
function normalizeGreetingName(s: string): string {
  return s
    .replace(/[\u200e\u200f\u202a-\u202e\u2066-\u2069]/g, '')
    .replace(/[\u200b-\u200d\ufeff]/g, '')
    .trim();
}

/** Prefer saved profile display name; empty profile → Clerk first name; then locale fallback */
export function getNameForGreeting(
  displayName?: string | null,
  clerkFirstName?: string | null,
  lang: string = 'he',
): string {
  const fromProfile = normalizeGreetingName(
    displayName != null && typeof displayName === 'string' ? displayName : '',
  );
  if (fromProfile) return fromProfile;
  const fromClerk = normalizeGreetingName(
    clerkFirstName != null && typeof clerkFirstName === 'string' ? clerkFirstName : '',
  );
  if (fromClerk) return fromClerk;
  return lang === 'he' ? 'רב' : 'there';
}

/** Same welcome copy as workspace chat (`welcome_message` in i18n) — no "undefined" in output */
export function buildWelcomeMessage(
  displayName: string | null | undefined,
  clerkFirstName: string | null | undefined,
  lang: string,
  t: I18nT,
): string {
  const fallback = lang === 'he' ? 'רב' : 'there';
  const name = getNameForGreeting(displayName, clerkFirstName, lang) || fallback;
  let greeting = String(t('welcome_message', { name }) ?? '');
  greeting = greeting.replace(/\bundefined\b/gi, fallback);
  return stripUndefined(greeting);
}

/** Onboarding-only: same flavor as `welcome_message`, ends with asking for their name (no coaching permission). */
export function buildIntakeOpeningMessage(
  displayName: string | null | undefined,
  clerkFirstName: string | null | undefined,
  lang: string,
  t: I18nT,
): string {
  const fallback = lang === 'he' ? 'רב' : 'there';
  const name = getNameForGreeting(displayName, clerkFirstName, lang) || fallback;
  let text = String(t('bsdOnboarding.intakeOpeningMessage', { name }) ?? '');
  text = text.replace(/\bundefined\b/gi, fallback);
  return stripUndefined(text);
}
