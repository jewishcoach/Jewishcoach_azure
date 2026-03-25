import type { TFunction } from 'i18next';

/** `useTranslation().t` — use for props/helpers so CI accepts i18next’s real TFunction signature */
export type I18nT = TFunction;
