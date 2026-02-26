/**
 * Remove all forms of "undefined" from message content.
 * i18n interpolation or API can sometimes inject "undefined" when values are missing.
 */
export function stripUndefined(text: string): string {
  if (text == null || typeof text !== 'string') return '';
  return text
    .replace(/undefined/g, '')
    .replace(/\?undefined/g, '?')
    .replace(/undefined\?/g, '?')
    .replace(/\s*undefined\s*/g, ' ')
    .replace(/\s{2,}/g, ' ')
    .trim();
}
