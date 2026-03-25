/**
 * Remove all forms of "undefined" from message content.
 * i18n interpolation or API can sometimes inject "undefined" when values are missing.
 */
export function stripUndefined(text: string): string {
  if (text == null || typeof text !== 'string') return '';
  return text
    .replace(/([?\u061f])undefined\s*$/gi, '$1')  // "?undefined" / "؟undefined" at end (greetings)
    .replace(/undefined\s*$/gi, '')                // "undefined" at very end
    .replace(/[^\S\n]*undefined[^\S\n]*/gi, ' ')   // inline: replace with single space, preserve newlines
    .replace(/\n+undefined[^\S\n]*$/gi, '')        // trailing undefined after newline(s)
    .replace(/^[^\S\n]*undefined\n*/gi, '')        // leading undefined before newline(s)
    .replace(/\?undefined/gi, '?')
    .replace(/undefined\?/gi, '?')
    .replace(/undefined/gi, '')                    // catch any remaining occurrences
    .replace(/[^\S\n]{2,}/g, ' ')                  // collapse multiple spaces/tabs (NOT newlines)
    .replace(/[^\S\n]+$/, '')                      // trailing spaces on last line
    .trim();
}
