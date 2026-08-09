import { getApiBase } from '../../config';
import type { ChatResponseV2, StageIntroPayload, StageSummaryPayload } from '../types';

const UX_VERSION_HEADER = { 'X-UX-Version': '2' };

async function authHeaders(getToken: () => Promise<string | null>): Promise<HeadersInit> {
  const token = await getToken();
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...UX_VERSION_HEADER,
  };
}

export async function sendMessageV2(
  message: string,
  conversationId: number,
  language: string,
  getToken: () => Promise<string | null>,
): Promise<ChatResponseV2> {
  const base = getApiBase();
  const res = await fetch(`${base}/chat/v2/message`, {
    method: 'POST',
    headers: await authHeaders(getToken),
    body: JSON.stringify({ message, conversation_id: conversationId, language }),
  });
  if (!res.ok) throw new Error(`Chat failed: ${res.status}`);
  return res.json();
}

export async function fetchStageIntro(
  conversationId: number,
  targetMacroStage: string,
  language: string,
  getToken: () => Promise<string | null>,
): Promise<StageIntroPayload> {
  const base = getApiBase();
  const res = await fetch(`${base}/chat/v2/stage-intro`, {
    method: 'POST',
    headers: await authHeaders(getToken),
    body: JSON.stringify({
      conversation_id: conversationId,
      target_macro_stage: targetMacroStage,
      language,
    }),
  });
  if (!res.ok) throw new Error(`Stage intro failed: ${res.status}`);
  return res.json();
}

export async function submitStageIntroAnswers(
  conversationId: number,
  macroStage: string,
  answers: Record<string, string[]>,
  language: string,
  getToken: () => Promise<string | null>,
): Promise<void> {
  const base = getApiBase();
  const res = await fetch(`${base}/chat/v2/stage-intro-answers`, {
    method: 'POST',
    headers: await authHeaders(getToken),
    body: JSON.stringify({
      conversation_id: conversationId,
      macro_stage: macroStage,
      answers,
      language,
    }),
  });
  if (!res.ok) throw new Error(`Stage intro answers failed: ${res.status}`);
}

export async function fetchStageSummary(
  conversationId: number,
  macroStage: string,
  language: string,
  getToken: () => Promise<string | null>,
): Promise<StageSummaryPayload> {
  const base = getApiBase();
  const res = await fetch(`${base}/chat/v2/stage-summary`, {
    method: 'POST',
    headers: await authHeaders(getToken),
    body: JSON.stringify({
      conversation_id: conversationId,
      target_macro_stage: macroStage,
      language,
    }),
  });
  if (!res.ok) throw new Error(`Stage summary failed: ${res.status}`);
  return res.json();
}

export interface ConversationListItem {
  id: number;
  title: string;
  created_at: string;
  current_phase: string;
  message_count: number;
}

export interface ConversationLoadData {
  conversation_id: number;
  current_step: string;
  messages: { id: string; role: 'user' | 'assistant'; content: string }[];
  collected_data?: Record<string, unknown> | null;
}

export async function loadConversation(
  conversationId: number,
  getToken: () => Promise<string | null>,
): Promise<ConversationLoadData> {
  const base = getApiBase();
  const res = await fetch(`${base}/chat/v2/conversation/${conversationId}`, {
    method: 'GET',
    headers: await authHeaders(getToken),
  });
  if (!res.ok) throw new Error(`Load conversation failed: ${res.status}`);
  return res.json();
}

export async function listConversations(
  getToken: () => Promise<string | null>,
): Promise<ConversationListItem[]> {
  const base = getApiBase();
  const res = await fetch(`${base}/chat/conversations`, {
    method: 'GET',
    headers: await authHeaders(getToken),
  });
  if (!res.ok) return [];
  return res.json();
}

export async function createConversation(
  language: string,
  getToken: () => Promise<string | null>,
): Promise<number> {
  const base = getApiBase();
  const res = await fetch(`${base}/chat/conversations`, {
    method: 'POST',
    headers: await authHeaders(getToken),
    body: JSON.stringify({ language }),
  });
  if (!res.ok) throw new Error(`Create conversation failed: ${res.status}`);
  const data = await res.json();
  return data.id;
}
