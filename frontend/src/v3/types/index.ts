// Re-export all V2 types — V3 extends, never duplicates
export type {
  IntroAnswerOption,
  IntroQuestion,
  StageIntroPayload,
  StageSummaryPayload,
  MacroStage,
  FlowPhase,
  FlowState,
  ChatMessage,
  CollectedData,
  ChatResponseV2,
} from '../../v2/types';

export { MACRO_STAGES, stepToMacroStage } from '../../v2/types';

// ---------------------------------------------------------------------------
// V3-specific types
// ---------------------------------------------------------------------------

export interface ToolCallV3 {
  id: string;
  type: string;
  tool_type: string;
  title_he: string;
  instruction_he: string;
  data?: Record<string, unknown>;
}

export interface ActiveInlineTool {
  id: string;
  tool_type: string;
  data?: Record<string, unknown>;
  title_he?: string;
  instruction_he?: string;
}

export interface CompletedToolResult {
  tool_type: string;
  data: Record<string, unknown>;
  summary?: string;
}

export interface ToolSubmitResponse {
  coach_message: string;
  current_step: string;
  saturation_score: number;
  tool_call?: ToolCallV3 | null;
  collected_data?: Record<string, unknown> | null;
}

export interface V3ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'tool_result';
  content: string;
  timestamp?: string;
  phase?: string;
  suggestions?: string[];
  toolResult?: CompletedToolResult;
}
