/**
 * Wrap known BSD / methodology phrases in **markdown bold** before ReactMarkdown.
 * Preserves existing **…** blocks from the coach so we don’t nest incorrectly.
 */

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/** Hebrew letters + geresh / gershayim used inside words */
const HEBREW_BOUNDARY_CLASS = 'א-ת״׳';

function maskBoldSegments(text: string): { masked: string; segments: string[] } {
  const segments: string[] = [];
  const masked = text.replace(/\*\*([\s\S]*?)\*\*/g, (_, inner: string) => {
    const i = segments.length;
    segments.push(`**${inner}**`);
    return `<<<BSD_MD_${i}>>>`;
  });
  return { masked, segments };
}

function unmaskBoldSegments(marked: string, segments: string[]): string {
  return marked.replace(/<<<BSD_MD_(\d+)>>>/g, (_, i) => segments[Number(i)] ?? '');
}

/**
 * Coach/server sometimes leaves closing `**` without a proper pair (e.g. המצוי**).
 * After we auto-wrap terms, that becomes **** and Markdown shows literal stars.
 * Strip orphan ** immediately after a Hebrew run (repeat until stable).
 */
function stripOrphanStarsAfterHebrew(text: string): string {
  let prev = '';
  let out = text;
  const re = /([\u0590-\u05FF]{2,})\*{2}(?!\*)/gu;
  while (out !== prev) {
    prev = out;
    out = out.replace(re, '$1');
  }
  return out;
}

/** Don't break `[טקסט](url)` or `` `code` `` while wrapping terms */
function maskMarkdownLinks(text: string): { masked: string; segments: string[] } {
  const segments: string[] = [];
  const masked = text.replace(/\[([^\]]+)]\([^)]+\)/g, (full) => {
    const i = segments.length;
    segments.push(full);
    return `<<<BSD_LINK_${i}>>>`;
  });
  return { masked, segments };
}

function unmaskMarkdownLinks(marked: string, segments: string[]): string {
  return marked.replace(/<<<BSD_LINK_(\d+)>>>/g, (_, i) => segments[Number(i)] ?? '');
}

function maskInlineCode(text: string): { masked: string; segments: string[] } {
  const segments: string[] = [];
  const masked = text.replace(/`[^`\n]+`/g, (full) => {
    const i = segments.length;
    segments.push(full);
    return `<<<BSD_CODE_${i}>>>`;
  });
  return { masked, segments };
}

function unmaskInlineCode(marked: string, segments: string[]): string {
  return marked.replace(/<<<BSD_CODE_(\d+)>>>/g, (_, i) => segments[Number(i)] ?? '');
}

function wrapHebrewTerms(masked: string, term: string): string {
  const esc = escapeRegExp(term);
  // Default: term must start after non-Hebrew (avoid matching inside longer words).
  // Exclude predecessor `*` so we never wrap inside broken `*מילה` / partial markdown.
  // Also allow common single-letter proclitics (ו״את בכל״ם / ולכבמשה) immediately before the term so
  // "המצוי והרצוי" → והרצוי still wraps הרצוי, and "לפער" wraps פער after ל.
  const re = new RegExp(
    `(^|[^*${HEBREW_BOUNDARY_CLASS}]|[ולבכמשה])(${esc})(?=[^${HEBREW_BOUNDARY_CLASS}]|$)`,
    'gu',
  );
  return masked.replace(re, (_full, sep: string, word: string) => `${sep}**${word}**`);
}

function wrapEnglishTerms(masked: string, term: string): string {
  const esc = escapeRegExp(term);
  if (/\s/.test(term)) {
    const re = new RegExp(`(^|[^A-Za-z])(${esc})(?=[^A-Za-z]|$)`, 'gi');
    return masked.replace(re, (_full, sep: string, phrase: string) => `${sep}**${phrase}**`);
  }
  const re = new RegExp(`\\b(${esc})\\b`, 'gi');
  return masked.replace(re, (_full, word: string) => `**${word}**`);
}

/** Longest first — avoids shorter overlaps */
const HEBREW_BSD_TERMS: string[] = [
  'טבלת רווח והפסד',
  'רווח והפסד',
  'אמירה פנימית',
  'אמירה רצויה',
  'מעשה רצוי',
  'רגשות רצויות',
  'רגש רצוי',
  'תפיסת מציאות',
  'כוחות מקור וטבע',
  'כוחות מקור',
  'כוחות טבע',
  'מחשבת מעשה',
  'נושא האימון',
  'תהליך השיבה',
  'כמ״ז',
  'כמ"ז',
  'המצוי',
  'הרצוי',
  'פרדיגמה',
  'פרכדיגמה',
  'עמדה',
  'טריגר',
  'דפוס',
  'פער',
  'חזון',
  'מחויבות',
  'בחירה חופשית',
  'מצוי',
  'רצוי',
].sort((a, b) => b.length - a.length);

const ENGLISH_BSD_TERMS: string[] = [
  'profit and loss table',
  'gain and loss table',
  'desired inner utterance',
  'desired action',
  'desired emotion',
  'desired emotions',
  'inner utterance',
  'coaching topic',
  'reality perception',
  'activation trigger',
  'source forces',
  'nature forces',
  'return process',
  'free choice',
  'actual and desired',
  'KaMaZ',
  'paradigm',
  'pattern',
  'stance',
  'trigger',
  'commitment',
  'vision',
  /** BSD stages: actual / desired / gap (Hebrew מצוי·רצוי·פער) */
  'desired state',
  'actual state',
  'the desired',
  'the actual',
  'desired',
  'actual',
  'gap',
].sort((a, b) => b.length - a.length);

/**
 * @param lang i18n language string, e.g. `he`, `en`
 */
export function emphasizeBsdCoachTerms(text: string, lang: string): string {
  if (!text || !text.trim()) return text;
  const isHe = lang === 'he' || lang.startsWith('he');
  const terms = isHe ? HEBREW_BSD_TERMS : ENGLISH_BSD_TERMS;
  const wrap = isHe ? wrapHebrewTerms : wrapEnglishTerms;

  const { masked: linkMasked, segments: linkSeg } = maskMarkdownLinks(text);
  const { masked: codeMasked, segments: codeSeg } = maskInlineCode(linkMasked);
  const { masked, segments: boldSeg } = maskBoldSegments(codeMasked);
  let out = stripOrphanStarsAfterHebrew(masked);
  for (const term of terms) {
    out = wrap(out, term);
  }
  out = unmaskBoldSegments(out, boldSeg);
  out = unmaskInlineCode(out, codeSeg);
  out = unmaskMarkdownLinks(out, linkSeg);
  return out;
}
