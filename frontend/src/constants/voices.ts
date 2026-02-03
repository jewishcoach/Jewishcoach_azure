export const COACH_VOICES = {
  he: {
    male: { 
      id: 'he-IL-AvriNeural', 
      name: 'Avri', 
      label: 'המאמן השקול' 
    },
    female: { 
      id: 'he-IL-HilaNeural', 
      name: 'Hila', 
      label: 'המאמנת המכילה' 
    }
  },
  en: {
    male: { 
      id: 'en-US-AndrewNeural', 
      name: 'Andrew', 
      label: 'Steady Coach' 
    },
    female: { 
      id: 'en-US-AvaNeural', 
      name: 'Ava', 
      label: 'Empathic Coach' 
    }
  }
};

export type VoiceGender = 'male' | 'female';
export type VoiceLanguage = 'he' | 'en';






