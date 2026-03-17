/**
 * Phase ↔ Stage mapping for Vision Ladder and smart scroll.
 * Phase index → stage IDs (S0-S15) for scroll-to-phase.
 */
export const PHASE_TO_STAGES: Record<number, string[]> = {
  0: ['S0'],
  1: ['S1', 'S2', 'S3', 'S4', 'S5'],
  2: ['S6'],
  3: ['S7'],
  4: ['S8'],
  5: ['S9'],
  6: ['S10', 'S11'],
  7: ['S11', 'S12'],  // שינוי - מעבר מעמדה לכמ"ז, גלילה ל-S11 או S12
  8: ['S12'],
  9: ['S13'],
  10: ['S14', 'S15'],
};
