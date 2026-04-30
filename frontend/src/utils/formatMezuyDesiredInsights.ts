import type { I18nT } from '../i18nT';

/** Subsections for HUD / ladder: מעשה → רגשות → אמירה פנימית (כמו בחוברת המצוי). */
export function buildActualInsightSections(
  t: I18nT,
  currentIdx: number,
  emotions: string[],
  thought: string | undefined,
  actionActual: string | undefined,
): { heading: string; body: string }[] {
  const sections: { heading: string; body: string }[] = [];
  if (currentIdx >= 4 && actionActual?.trim()) {
    sections.push({
      heading: t('insights.section.actualAction'),
      body: actionActual.trim(),
    });
  }
  if (currentIdx >= 2 && emotions.length > 0) {
    sections.push({
      heading: t('insights.section.actualEmotions'),
      body: emotions.join(', '),
    });
  }
  if (currentIdx >= 3 && thought?.trim()) {
    sections.push({
      heading: t('insights.section.actualUtterance'),
      body: `"${thought.trim()}"`,
    });
  }
  return sections;
}

/** רצוי: מעשה → רגשות → אמירה פנימית */
export function buildDesiredInsightSections(
  t: I18nT,
  actionDesired: string | undefined,
  emotionDesired: string | undefined,
  thoughtDesired: string | undefined,
): { heading: string; body: string }[] {
  const sections: { heading: string; body: string }[] = [];
  if (actionDesired?.trim()) {
    sections.push({
      heading: t('insights.section.desiredAction'),
      body: actionDesired.trim(),
    });
  }
  if (emotionDesired?.trim()) {
    sections.push({
      heading: t('insights.section.desiredEmotions'),
      body: emotionDesired.trim(),
    });
  }
  if (thoughtDesired?.trim()) {
    sections.push({
      heading: t('insights.section.desiredUtterance'),
      body: `"${thoughtDesired.trim()}"`,
    });
  }
  return sections;
}

/** טקסט אחד לפופאובר קומפקטי (סולם) */
export function formatActualInsightPlain(
  t: I18nT,
  currentIdx: number,
  emotions: string[],
  thought: string | undefined,
  actionActual: string | undefined,
): string {
  const rows = buildActualInsightSections(t, currentIdx, emotions, thought, actionActual);
  return rows.map((r) => `${r.heading}\n${r.body}`).join('\n\n');
}

export function formatDesiredInsightPlain(
  t: I18nT,
  ad: string | undefined,
  ed: string | undefined,
  td: string | undefined,
): string {
  const rows = buildDesiredInsightSections(t, ad, ed, td);
  return rows.map((r) => `${r.heading}\n${r.body}`).join('\n\n');
}
