export interface User {
  id: number;
  clerk_id: string;
  email: string;
  isAdmin: boolean;
}

/** V2 station checkpoint payload (API + optional message meta) */
export interface StationCheckpointPayload {
  station_id: string;
  step: string;
  floor_title: string;
  homework_title: string;
  homework_body: string;
  language: string;
}

export interface Message {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  meta?: {
    sources?: any;
    phase?: string;  // Stage (S0-S15) when message was sent - for smart scroll
    station_checkpoint?: StationCheckpointPayload;
  };
}

export interface Conversation {
  id: number;
  title: string;
  created_at: string;
  /** Present on full fetch; omitted on list endpoint */
  messages?: Message[];
  current_phase?: string;
  message_count?: number;
}

export interface SpeechToken {
  token: string;
  region: string;
}

export interface VoiceMessage {
  role: 'user' | 'assistant';
  content: string;
  isPartial?: boolean;  // For live transcription
}

export interface UserPreferences {
  voice_gender: 'male' | 'female';
  voice_language: 'he' | 'en';
}

export interface ToolCall {
  type?: 'reflection' | 'tool'; // NEW: type discriminator
  tool_type?: string; // For legacy/interactive tools
  id?: string; // Widget ID
  stage?: string; // Current stage (for reflection widgets)
  status?: 'draft' | 'final'; // NEW: Reflection status
  title_he?: string;
  title_en?: string;
  instruction_he?: string;
  instruction_en?: string;
  data?: any; // Extracted/tool data
}

export interface ToolSubmission {
  tool_type: string;
  data: any;
}

export interface JournalEntry {
  id: number;
  conversation_id: number;
  content: string;
  updated_at: string;
}

