interface ConceptAudio {
  file: string;
  label: string;
}

// ?v=2: the recordings were denoised on Nov 11 (highpass 70 Hz + afftdn nr=20 nf=-44, the "medium" take the user
// chose); the version makes browsers fetch the new files. Bump it whenever the files change.
const CONCEPT_AUDIO_MAP: Record<string, ConceptAudio[]> = {
  S0: [{ file: '/voice/01_request.mp3?v=2', label: 'בקשה לאימון' }],
  S1: [{ file: '/voice/01_request.mp3?v=2', label: 'בקשה לאימון' }],
  S2: [{ file: '/voice/02_matzui.mp3?v=2', label: 'המצוי' }],
  S3: [],
  S4: [],
  S5: [],
  S6: [
    { file: '/voice/03_ratzui.mp3?v=2', label: 'הרצוי' },
  ],
  S7: [],
  S8: [
    { file: '/voice/04_dfus.mp3?v=2', label: 'הדפוס' },
  ],
  S9: [
    { file: '/voice/05_paradigma.mp3?v=2', label: 'הפרדיגמא' },
  ],
  S10: [
    { file: '/voice/06_emda.mp3?v=2', label: 'העמדה' },
  ],
  S11: [
    { file: '/voice/07_revach.mp3?v=2', label: 'רווח והפסד' },
    { file: '/voice/08_kupsa.mp3?v=2', label: 'הקופסא' },
  ],
  S12: [
    { file: '/voice/09_makor.mp3?v=2', label: 'קומת המקור' },
    { file: '/voice/10_teva.mp3?v=2', label: 'קומת הטבע' },
    { file: '/voice/11_kamaz.mp3?v=2', label: 'הכמ"ז' },
  ],
  S13: [
    { file: '/voice/12_bhira.mp3?v=2', label: 'בחירה חדשה' },
  ],
  S14: [
    { file: '/voice/14_hazon.mp3?v=2', label: 'תמונת עתיד' },
  ],
  S15: [
    { file: '/voice/13_bakasha.mp3?v=2', label: 'נוסחת המחויבות' },
  ],
};

const CONCEPT_KEYWORDS: Record<string, string[]> = {
  '/voice/01_request.mp3?v=2': ['בקשה לאימון', 'סיטואציה', 'הנושא'],
  '/voice/02_matzui.mp3?v=2': ['מצוי', 'המצוי', 'מה שקרה'],
  '/voice/03_ratzui.mp3?v=2': ['רצוי', 'הרצוי', 'היית רוצה'],
  '/voice/04_dfus.mp3?v=2': ['דפוס', 'הדפוס', 'תגובה חוזרת'],
  '/voice/05_paradigma.mp3?v=2': ['פרדיגמ', 'ככה זה אצלי', 'טייס אוטומטי'],
  '/voice/06_emda.mp3?v=2': ['עמדה', 'העמדה', 'תפיסת המציאות'],
  '/voice/07_revach.mp3?v=2': ['רווח', 'הפסד', 'מחיר'],
  '/voice/08_kupsa.mp3?v=2': ['קופסא', 'הקופסא', 'לצאת מה'],
  '/voice/09_makor.mp3?v=2': ['מקור', 'המקור', 'נפש אלוקית'],
  '/voice/10_teva.mp3?v=2': ['טבע', 'הטבע', 'נפש טבעית'],
  '/voice/11_kamaz.mp3?v=2': ['כמ"ז', 'כרטיס מהות', 'מהות-זהות'],
  '/voice/12_bhira.mp3?v=2': ['בחירה חדשה', 'התחדשות', 'פרדיגמא חדשה'],
  '/voice/14_hazon.mp3?v=2': ['חזון', 'חפץ הלב', 'תמונת עתיד'],
  '/voice/13_bakasha.mp3?v=2': ['נוסחת המחויבות', 'מחויבות מעשית'],
};

export function getConceptAudioForMessage(
  step: string,
  messageContent: string,
  playedFiles: Set<string>,
): ConceptAudio | null {
  const candidates = CONCEPT_AUDIO_MAP[step] || [];

  for (const candidate of candidates) {
    if (playedFiles.has(candidate.file)) continue;

    const keywords = CONCEPT_KEYWORDS[candidate.file] || [];
    const found = keywords.some((kw) => messageContent.includes(kw));

    if (found) return candidate;
  }

  if (candidates.length > 0 && !playedFiles.has(candidates[0].file)) {
    return candidates[0];
  }

  return null;
}
