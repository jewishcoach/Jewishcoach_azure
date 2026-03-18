/**
 * Maps cognitive_data from conversation insights to ladder phase indices (0-10).
 * Used by HudPanel and VisionLadder compact for stage-specific insight display.
 */

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
  stance?: { gains?: string[]; losses?: string[] };
  forces?: { source?: string[]; nature?: string[] };
  kmz_forces?: { source_forces?: string[]; nature_forces?: string[] };
}

export interface InsightItem {
  label: string;
  value: string;
}

const stepIndex = (s: string) => parseInt(s.replace('S', ''), 10) || 0;

type TranslateFn = (key: string) => string;

/** Build map of phase index (0-10) to insight items for VisionLadder compact */
export function buildInsightsByPhase(
  data: CognitiveData | null | undefined,
  currentStage: string,
  t: TranslateFn
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

  const actionLabel = t('insights.label.action');
  const emotionLabel = t('insights.label.emotion');
  const thoughtLabel = t('insights.label.thought');

  // p1 - Current: topic, emotions, thought, action
  if (currentIdx >= 1 && data.topic) {
    (result[1] ??= []).push({ label: t('insights.label.topic'), value: data.topic });
  }
  if (currentIdx >= 2 && emotions.length > 0) {
    (result[1] ??= []).push({ label: emotionLabel, value: emotions.join(', ') });
  }
  if (currentIdx >= 3 && thought) {
    (result[1] ??= []).push({ label: thoughtLabel, value: thought });
  }
  if (currentIdx >= 4 && actionActual) {
    (result[1] ??= []).push({ label: t('insights.label.actionActual'), value: actionActual });
  }

  // p2 - Desired
  if (currentIdx >= 5) {
    const ad = data.action_desired ?? data.event_actual?.action_desired;
    const ed = data.emotion_desired ?? data.event_actual?.emotion_desired;
    const td = data.thought_desired ?? data.event_actual?.thought_desired;
    const parts: string[] = [];
    if (ad) parts.push(`${actionLabel}: ${ad}`);
    if (ed) parts.push(`${emotionLabel}: ${ed}`);
    if (td) parts.push(`${thoughtLabel}: ${td}`);
    if (parts.length) {
      (result[2] ??= []).push({ label: t('insights.label.desired'), value: parts.join('\n') });
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

  // p6 - Stance
  if (stanceData && currentIdx >= 11) {
    const gains = stanceData.gains ?? [];
    const losses = stanceData.losses ?? [];
    const parts: string[] = [];
    if (gains.length) parts.push(`${t('insights.label.gains')}: ${gains.join(', ')}`);
    if (losses.length) parts.push(`${t('insights.label.losses')}: ${losses.join(', ')}`);
    if (parts.length) {
      (result[6] ??= []).push({ label: t('insights.label.oldStance'), value: parts.join('\n') });
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
