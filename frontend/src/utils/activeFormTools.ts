import type { ToolCall } from '../types';

/** Interactive workspace forms where free-text chat must not hit the model. */
export const CHAT_BLOCKED_TOOL_TYPES = ['profit_loss', 'trait_picker'] as const;

export function isChatBlockedByActiveTool(activeTool: ToolCall | null | undefined): boolean {
  const tt = activeTool?.tool_type;
  return !!tt && (CHAT_BLOCKED_TOOL_TYPES as readonly string[]).includes(tt);
}
