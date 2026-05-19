import type { I18nT } from '../i18nT';
import { stripUndefined } from './messageContent';

/** Trainee gender from profile (`/users/me`). Unknown / skipped onboarding → neutral copy. */
export type TraineeGender = 'male' | 'female' | null;

export function normalizeTraineeGender(raw: unknown): TraineeGender {
  if (raw === 'male' || raw === 'female') return raw;
  return null;
}

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

function workspaceWelcomeKey(lang: string, traineeGender: TraineeGender): string {
  const he = (lang || 'he').toLowerCase().startsWith('he');
  if (!he) return 'welcome_message';
  if (traineeGender === 'female') return 'welcome_message_he_female';
  if (traineeGender === 'male') return 'welcome_message_he_male';
  return 'welcome_message_he_neutral';
}

/** Same welcome copy as workspace chat — English uses `welcome_message`; Hebrew picks gendered/neutral keys. */
export function buildWelcomeMessage(
  displayName: string | null | undefined,
  clerkFirstName: string | null | undefined,
  lang: string,
  t: I18nT,
  traineeGender: TraineeGender = null,
): string {
  const fallback = lang === 'he' ? 'רב' : 'there';
  const name = getNameForGreeting(displayName, clerkFirstName, lang) || fallback;
  const key = workspaceWelcomeKey(lang, traineeGender);
  const he = (lang || 'he').toLowerCase().startsWith('he');
  let greeting = String(t(key, { name }) ?? '');
  if (!greeting.trim() || greeting === key) {
    greeting = String(
      he ? t('welcome_message_he_neutral', { name }) : t('welcome_message', { name }),
    );
  }
  greeting = greeting.replace(/\bundefined\b/gi, fallback);
  return stripUndefined(greeting);
}

/**
 * Onboarding-only: same flavor as `welcome_message`, ends with asking for their name.
 * Intentionally does NOT personalize with profile/Clerk names — those are often wrong before intake,
 * and we ask for the user's chosen name in the same flow.
 */
export function buildIntakeOpeningMessage(
  _displayName: string | null | undefined,
  _clerkFirstName: string | null | undefined,
  lang: string,
  t: I18nT,
): string {
  return getIntakeOpeningBlocks(lang, t).join('\n\n');
}

/** Three staggered coach bubbles for onboarding entry (typing sequence). */
export function getIntakeOpeningBlocks(lang: string, t: I18nT): string[] {
  const fallback = lang === 'he' ? 'רב' : 'there';
  const keys = [
    'bsdOnboarding.intakeOpeningBlock1',
    'bsdOnboarding.intakeOpeningBlock2',
    'bsdOnboarding.intakeOpeningBlock3',
  ] as const;
  const blocks = keys
    .map((key) => {
      let text = String(t(key) ?? '');
      if (!text.trim() || text === key) return '';
      text = text.replace(/\bundefined\b/gi, fallback);
      return stripUndefined(text);
    })
    .filter(Boolean);
  if (blocks.length >= 3) return blocks;
  const legacy = String(t('bsdOnboarding.intakeOpeningMessage') ?? '');
  if (legacy.trim() && legacy !== 'bsdOnboarding.intakeOpeningMessage') {
    return legacy
      .replace(/\bundefined\b/gi, fallback)
      .split(/\n\n+/)
      .map((p) => p.trim())
      .filter(Boolean);
  }
  return blocks;
}

/** Mirrors server `intake_ask_gender_after_name` — shown instantly after first name reply. */
export function buildAfterNameCoachMessage(
  displayName: string,
  lang: string,
  t: I18nT,
): string {
  const name = getNameForGreeting(displayName, null, lang) || displayName.trim();
  let text = String(t('bsdOnboarding.afterNameCoach', { name }) ?? '');
  if (!text.trim() || text === 'bsdOnboarding.afterNameCoach') {
    text = `שלום ${name}, נעים להכיר!`;
  }
  return stripUndefined(text.replace(/\bundefined\b/gi, name));
}
