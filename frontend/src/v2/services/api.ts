import { getApiBase } from '../../config';
import type { ChatResponseV2, StageIntroPayload, StageSummaryPayload } from '../types';

export class QuotaExceededError extends Error {
  constructor() {
    super('quota_exceeded');
    this.name = 'QuotaExceededError';
  }
}

export class ConflictError extends Error {
  constructor() {
    super('conflict');
    this.name = 'ConflictError';
  }
}

const UX_VERSION_HEADER = { 'X-UX-Version': '2' };

async function authHeaders(getToken: (opts?: { skipCache?: boolean }) => Promise<string | null>, skipCache = false): Promise<Record<string, string>> {
  const token = await getToken(skipCache ? { skipCache: true } : undefined);
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...UX_VERSION_HEADER,
  };
}

async function fetchWithAuthRetry(
  url: string,
  getToken: (opts?: { skipCache?: boolean }) => Promise<string | null>,
  init?: RequestInit,
): Promise<Response> {
  const headers = await authHeaders(getToken);
  const res = await fetch(url, { ...init, headers: { ...headers, ...(init?.headers as Record<string, string> || {}) } });
  if (res.status === 401) {
    const freshHeaders = await authHeaders(getToken, true);
    return fetch(url, { ...init, headers: { ...freshHeaders, ...(init?.headers as Record<string, string> || {}) } });
  }
  return res;
}

export async function sendMessageV2(
  message: string,
  conversationId: number,
  language: string,
  getToken: (opts?: { skipCache?: boolean }) => Promise<string | null>,
): Promise<ChatResponseV2> {
  const base = getApiBase();
  const body = JSON.stringify({ message, conversation_id: conversationId, language });

  let lastStatus = 0;
  for (let attempt = 0; attempt < 2; attempt++) {
    const res = await fetchWithAuthRetry(`${base}/chat/v2/message`, getToken, { method: 'POST', body });
    if (res.ok) return res.json();
    lastStatus = res.status;
    if (res.status === 429) throw new QuotaExceededError();
    if (res.status === 409) throw new ConflictError();
    if (res.status >= 500 && attempt === 0) {
      await new Promise((r) => setTimeout(r, 1500));
      continue;
    }
    break;
  }
  throw new Error(`Chat failed: ${lastStatus}`);
}

export async function fetchStageIntro(
  conversationId: number,
  targetMacroStage: string,
  language: string,
  getToken: (opts?: { skipCache?: boolean }) => Promise<string | null>,
): Promise<StageIntroPayload> {
  const base = getApiBase();
  const res = await fetchWithAuthRetry(`${base}/chat/v2/stage-intro`, getToken, {
    method: 'POST',
    body: JSON.stringify({ conversation_id: conversationId, target_macro_stage: targetMacroStage, language }),
  });
  if (!res.ok) throw new Error(`Stage intro failed: ${res.status}`);
  return res.json();
}

export async function submitStageIntroAnswers(
  conversationId: number,
  macroStage: string,
  answers: Record<string, string[]>,
  language: string,
  getToken: (opts?: { skipCache?: boolean }) => Promise<string | null>,
): Promise<{ opening_message?: string }> {
  const base = getApiBase();
  const res = await fetchWithAuthRetry(`${base}/chat/v2/stage-intro-answers`, getToken, {
    method: 'POST',
    body: JSON.stringify({ conversation_id: conversationId, macro_stage: macroStage, answers, language }),
  });
  if (!res.ok) throw new Error(`Stage intro answers failed: ${res.status}`);
  return res.json();
}

export async function fetchStageSummary(
  conversationId: number,
  macroStage: string,
  language: string,
  getToken: (opts?: { skipCache?: boolean }) => Promise<string | null>,
): Promise<StageSummaryPayload> {
  const base = getApiBase();
  const res = await fetchWithAuthRetry(`${base}/chat/v2/stage-summary`, getToken, {
    method: 'POST',
    body: JSON.stringify({ conversation_id: conversationId, target_macro_stage: macroStage, language }),
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
  getToken: (opts?: { skipCache?: boolean }) => Promise<string | null>,
): Promise<ConversationLoadData> {
  const base = getApiBase();
  const res = await fetchWithAuthRetry(`${base}/chat/v2/conversation/${conversationId}`, getToken);
  if (!res.ok) throw new Error(`Load conversation failed: ${res.status}`);
  return res.json();
}

export async function listConversations(
  getToken: (opts?: { skipCache?: boolean }) => Promise<string | null>,
): Promise<ConversationListItem[]> {
  const base = getApiBase();
  const res = await fetchWithAuthRetry(`${base}/chat/conversations`, getToken);
  if (!res.ok) {
    console.warn('[API] listConversations failed:', res.status);
    return [];
  }
  return res.json();
}

export async function createConversation(
  language: string,
  getToken: (opts?: { skipCache?: boolean }) => Promise<string | null>,
): Promise<number> {
  const base = getApiBase();
  const res = await fetchWithAuthRetry(`${base}/chat/conversations`, getToken, {
    method: 'POST',
    body: JSON.stringify({ language }),
  });
  if (!res.ok) throw new Error(`Create conversation failed: ${res.status}`);
  const data = await res.json();
  return data.id;
}

export async function fetchUserGender(
  getToken: (opts?: { skipCache?: boolean }) => Promise<string | null>,
): Promise<string | null> {
  const base = getApiBase();
  try {
    const headers = await authHeaders(getToken);
    const res = await fetch(`${base}/profile/me`, { headers });
    if (!res.ok) return null;
    const data = await res.json();
    return data.gender || null;
  } catch {
    return null;
  }
}
