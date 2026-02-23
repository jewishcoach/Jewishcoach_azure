/**
 * מיפוי שלב (S0-S12) → סרטוני YouTube להעשרה
 * YouTube embed: https://www.youtube.com/embed/VIDEO_ID
 * TODO: להחליף ב-videoId אמיתיים מסרטוני העשרה
 */
export const STAGE_VIDEOS: Record<string, { videoId: string; titleHe: string; titleEn: string }[]> = {
  S0: [
    { videoId: 'dQw4w9WgXcQ', titleHe: 'קבלת רשות לאימון', titleEn: 'Getting permission for coaching' },
  ],
  S1: [
    { videoId: 'dQw4w9WgXcQ', titleHe: 'מצוי - נושא ואירוע', titleEn: 'Actual - topic and event' },
  ],
  S2: [
    { videoId: 'dQw4w9WgXcQ', titleHe: 'תיאור אירוע', titleEn: 'Describing the event' },
  ],
  S3: [
    { videoId: 'dQw4w9WgXcQ', titleHe: 'מסך הרגש', titleEn: 'Emotion screen' },
  ],
  S4: [
    { videoId: 'dQw4w9WgXcQ', titleHe: 'מסך המחשבה', titleEn: 'Thought screen' },
  ],
  S5: [
    { videoId: 'dQw4w9WgXcQ', titleHe: 'מסך המעשה', titleEn: 'Action screen' },
  ],
  S6: [
    { videoId: 'dQw4w9WgXcQ', titleHe: 'ניתוח הפער', titleEn: 'Gap analysis' },
  ],
  S7: [
    { videoId: 'dQw4w9WgXcQ', titleHe: 'דפוס ופרדיגמה', titleEn: 'Pattern and paradigm' },
  ],
  S8: [
    { videoId: 'dQw4w9WgXcQ', titleHe: 'עמדה ורצון', titleEn: 'Stance and desire' },
  ],
  S9: [
    { videoId: 'dQw4w9WgXcQ', titleHe: 'כמ"ז - כוחות מקור וטבע', titleEn: 'KaMaZ - source and nature forces' },
  ],
  S10: [
    { videoId: 'dQw4w9WgXcQ', titleHe: 'התחדשות ובחירה', titleEn: 'Renewal and choice' },
  ],
  S11: [
    { videoId: 'dQw4w9WgXcQ', titleHe: 'חזון', titleEn: 'Vision' },
  ],
  S12: [
    { videoId: 'dQw4w9WgXcQ', titleHe: 'מחויבות', titleEn: 'Commitment' },
  ],
};

/** Fallback when stage has no video */
const DEFAULT_VIDEO = { videoId: 'dQw4w9WgXcQ', titleHe: 'העשרה', titleEn: 'Enrichment' };

export function getVideosForStage(stage: string): { videoId: string; titleHe: string; titleEn: string }[] {
  return STAGE_VIDEOS[stage] || [DEFAULT_VIDEO];
}
