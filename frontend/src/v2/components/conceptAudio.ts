interface ConceptAudio {
  file: string;
  label: string;
}

const CONCEPT_AUDIO_MAP: Record<string, ConceptAudio[]> = {
  S0: [{ file: '/voice/01_request.mp3', label: 'בקשה לאימון' }],
  S1: [{ file: '/voice/01_request.mp3', label: 'בקשה לאימון' }],
  S2: [{ file: '/voice/02_matzui.mp3', label: 'המצוי' }],
  S3: [],
  S4: [],
  S5: [],
  S6: [
    { file: '/voice/03_ratzui.mp3', label: 'הרצוי' },
  ],
  S7: [
    { file: '/voice/04_dfus.mp3', label: 'הדפוס' },
    { file: '/voice/05_paradigma.mp3', label: 'הפרדיגמא' },
  ],
  S8: [
    { file: '/voice/06_emda.mp3', label: 'העמדה' },
    { file: '/voice/07_revach.mp3', label: 'רווח והפסד' },
  ],
  S9: [
    { file: '/voice/09_makor.mp3', label: 'קומת המקור' },
    { file: '/voice/10_teva.mp3', label: 'קומת הטבע' },
    { file: '/voice/11_kamaz.mp3', label: 'הכמ"ז' },
  ],
  S11: [
    { file: '/voice/08_kupsa.mp3', label: 'הקופסא' },
    { file: '/voice/12_bhira.mp3', label: 'בחירה חדשה' },
  ],
  S12: [{ file: '/voice/14_hazon.mp3', label: 'חזון' }],
  S10: [{ file: '/voice/13_bakasha.mp3', label: 'בקשה לאימון' }],
};

const CONCEPT_KEYWORDS: Record<string, string[]> = {
  '/voice/01_request.mp3': ['בקשה לאימון', 'סיטואציה', 'הנושא'],
  '/voice/02_matzui.mp3': ['מצוי', 'המצוי', 'מה שקרה'],
  '/voice/03_ratzui.mp3': ['רצוי', 'הרצוי', 'היית רוצה'],
  '/voice/04_dfus.mp3': ['דפוס', 'הדפוס', 'תגובה חוזרת'],
  '/voice/05_paradigma.mp3': ['פרדיגמ', 'ככה זה אצלי', 'טייס אוטומטי'],
  '/voice/06_emda.mp3': ['עמדה', 'העמדה', 'תפיסת המציאות'],
  '/voice/07_revach.mp3': ['רווח', 'הפסד', 'מחיר'],
  '/voice/08_kupsa.mp3': ['קופסא', 'הקופסא', 'לצאת מה'],
  '/voice/09_makor.mp3': ['מקור', 'המקור', 'נפש אלוקית'],
  '/voice/10_teva.mp3': ['טבע', 'הטבע', 'נפש טבעית'],
  '/voice/11_kamaz.mp3': ['כמ"ז', 'כרטיס מהות', 'מהות-זהות'],
  '/voice/12_bhira.mp3': ['בחירה חדשה', 'התחדשות', 'פרדיגמא חדשה'],
  '/voice/14_hazon.mp3': ['חזון', 'חפץ הלב', 'תמונת עתיד'],
  '/voice/13_bakasha.mp3': ['נוסחת המחויבות', 'מחויבות מעשית'],
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
