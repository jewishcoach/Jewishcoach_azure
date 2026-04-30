/**
 * Maps cognitive_data from conversation insights to ladder phase indices (0-10).
 * Used by HudPanel and VisionLadder compact for stage-specific insight display.
 */

import type { I18nT } from '../i18nT';
import { formatActualInsightPlain, formatDesiredInsightPlain } from './formatMezuyDesiredInsights';

export interface CognitiveData {
  topic?: string;
  emotions?: string[];
  event_actual?: {
    emotions_list?: string[];
    thought_content?: string;
    action_content?: string;
    action_desired?: string;
    emotion_desired?: string;
    thought_desired?: string;
  };
  thought?: string;
  action_actual?: string;
  action_desired?: string;
  emotion_desired?: string;
  thought_desired?: string;
  gap_name?: string;
  gap_score?: number;
  gap_analysis?: { name?: string; score?: number };
  pattern?: string;
  pattern_id?: { name?: string; paradigm?: string };
  paradigm?: string;
  stance?: {
    reality_belief?: string;
    activation_trigger?: string;
    gains?: string[];
    losses?: string[];
  };
  forces?: { source?: string[]; nature?: string[] };
  kmz_forces?: { source_forces?: string[]; nature_forces?: string[] };
}

export interface InsightItem {
  label: string;
  value: string;
}

const stepIndex = (s: string) => parseInt(s.replace('S', ''), 10) || 0;

/** Build map of phase index (0-10) to insight items for VisionLadder compact */
export function buildInsightsByPhase(
  data: CognitiveData | null | undefined,
  currentStage: string,
  t: I18nT
): Record<number, InsightItem[]> {
  const result: Record<number, InsightItem[]> = {};
  if (!data) return result;

  const currentIdx = stepIndex(currentStage);
  const emotions = data.emotions ?? data.event_actual?.emotions_list ?? [];
  const thought = data.thought ?? data.event_actual?.thought_content;
  const actionActual = data.action_actual ?? data.event_actual?.action_content;
  const gapName = data.gap_name ?? data.gap_analysis?.name;
  const gapScore = data.gap_score ?? data.gap_analysis?.score;
  const pattern = data.pattern ?? data.pattern_id?.name;
  const paradigm = data.paradigm ?? data.pattern_id?.paradigm;
  const stanceData = data.stance;
  const kmz = data.kmz_forces ?? data.forces;

  // p1 — נושא + כרטיס מצוי אחד (מעשה / רגשות / אמירה פנימית), כמו בהוד
  if (currentIdx >= 1 && data.topic) {
    (result[1] ??= []).push({ label: t('insights.label.topic'), value: data.topic });
  }
  const actualPlain = formatActualInsightPlain(t, currentIdx, emotions, thought, actionActual);
  if (actualPlain) {
    (result[1] ??= []).push({ label: t('insights.card.actual'), value: actualPlain });
  }

  // p2 — רצוי בכרטיסיה אחת
  if (currentIdx >= 5) {
    const ad = data.action_desired ?? data.event_actual?.action_desired;
    const ed = data.emotion_desired ?? data.event_actual?.emotion_desired;
    const td = data.thought_desired ?? data.event_actual?.thought_desired;
    const desiredPlain = formatDesiredInsightPlain(t, ad, ed, td);
    if (desiredPlain) {
      (result[2] ??= []).push({ label: t('insights.card.desiredBlock'), value: desiredPlain });
    }
  }

  // p3 - Gap
  if (gapName && currentIdx >= 6) {
    (result[3] ??= []).push({
      label: t('insights.label.gap'),
      value: `${gapName}${gapScore != null ? ` (${gapScore}/10)` : ''}`,
    });
  }

  // p4 - Pattern
  if (pattern && currentIdx >= 7) {
    (result[4] ??= []).push({ label: t('insights.label.pattern'), value: pattern });
  }

  // p5 - Paradigm
  if (paradigm && currentIdx >= 9) {
    (result[5] ??= []).push({ label: t('insights.label.paradigm'), value: paradigm });
  }

  // p6 - Stance (S10: תפיסת מציאות + טריגר)
  if (stanceData && currentIdx >= 10) {
    const rb = stanceData.reality_belief?.trim();
    const trig = stanceData.activation_trigger?.trim();
    const stanceParts: string[] = [];
    if (rb) stanceParts.push(`${t('insights.label.stanceReality')}: ${rb}`);
    if (trig) stanceParts.push(`${t('insights.label.stanceTrigger')}: ${trig}`);
    if (stanceParts.length) {
      (result[6] ??= []).push({ label: t('insights.label.stance'), value: stanceParts.join('\n') });
    }
  }

  // p6 - טבלת רווח והפסד (S11)
  if (stanceData && currentIdx >= 11) {
    const gains = stanceData.gains ?? [];
    const losses = stanceData.losses ?? [];
    const parts: string[] = [];
    if (gains.length) parts.push(`${t('insights.label.gains')}: ${gains.join(', ')}`);
    if (losses.length) parts.push(`${t('insights.label.losses')}: ${losses.join(', ')}`);
    if (parts.length) {
      (result[6] ??= []).push({ label: t('insights.label.profitLossTable'), value: parts.join('\n') });
    }
  }

  // p8 - Source
  if (currentIdx >= 12 && kmz) {
    const k = kmz as Record<string, string[] | undefined>;
    const source = k.source_forces ?? k.source ?? [];
    const nature = k.nature_forces ?? k.nature ?? [];
    const parts: string[] = [];
    if (source.length) parts.push(`${t('insights.label.source')}: ${source.join(', ')}`);
    if (nature.length) parts.push(`${t('insights.label.nature')}: ${nature.join(', ')}`);
    if (parts.length) {
      (result[8] ??= []).push({ label: t('insights.label.kmzForces'), value: parts.join('\n') });
    }
  }

  return result;
}
