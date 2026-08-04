export interface IntroAnswerOption {
  id: string;
  label: string;
  emoji?: string;
}

export interface IntroQuestion {
  id: string;
  prompt: string;
  options: IntroAnswerOption[];
  multi_select: boolean;
  allow_free_text: boolean;
}

export interface StageIntroPayload {
  stage_id: string;
  stage_title: string;
  intro_text: string;
  questions: IntroQuestion[];
}

export interface StageSummaryPayload {
  stage_id: string;
  stage_title: string;
  insights: string[];
  next_stage_id: string | null;
  next_stage_title: string | null;
}

export interface MacroStage {
  id: string;
  title_he: string;
  title_en: string;
  description_he: string;
  description_en: string;
}

export const MACRO_STAGES: MacroStage[] = [
  {
    id: 'identification',
    title_he: 'זיהוי',
    title_en: 'Identification',
    description_he: 'עוצר לדעת כדי לראות מה באמת קורה בי',
    description_en: 'Stopping to know — seeing what\'s really happening inside',
  },
  {
    id: 'discovery',
    title_he: 'גילוי',
    title_en: 'Discovery',
    description_he: 'מגלה שיש דרך נוספת להסתכל על המציאות',
    description_en: 'Discovering there\'s another way to see reality',
  },
  {
    id: 'kamaz',
    title_he: 'כמ"ז',
    title_en: 'Forces (KMZ)',
    description_he: 'כוחות מקור וטבע — בונה האמן אישי',
    description_en: 'Source & Nature forces — building a personal identity card',
  },
  {
    id: 'choice',
    title_he: 'בחירה',
    title_en: 'Choice',
    description_he: 'בוחר מחדש — עמדה, פרדיגמה ודפוס חדשים',
    description_en: 'Choosing anew — a new stance, paradigm, and pattern',
  },
  {
    id: 'vision',
    title_he: 'חזון',
    title_en: 'Vision',
    description_he: 'בוחר את החיים שאני באמת רוצה לחיות',
    description_en: 'Choosing the life I truly want to live',
  },
];

export type FlowPhase =
  | 'onboarding'
  | 'chatting'
  | 'stage_complete'
  | 'loading_intro'
  | 'answering_intro'
  | 'submitting_answers';

export interface FlowState {
  phase: FlowPhase;
  currentMacroStage: string;
  currentStep: string;
  summary?: StageSummaryPayload;
  introPayload?: StageIntroPayload;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  phase?: string;
}

export interface ChatResponseV2 {
  coach_message: string;
  conversation_id: number;
  current_step: string;
  saturation_score: number;
  tool_call?: Record<string, unknown> | null;
  station_checkpoint?: Record<string, unknown> | null;
  stage_complete?: StageSummaryPayload | null;
}
