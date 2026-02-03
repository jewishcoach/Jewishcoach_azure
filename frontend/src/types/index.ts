export interface User {
  id: number;
  clerk_id: string;
  email: string;
  isAdmin: boolean;
}

export interface Message {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  meta?: {
    sources?: any;
  };
}

export interface Conversation {
  id: number;
  title: string;
  created_at: string;
  messages: Message[];
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

