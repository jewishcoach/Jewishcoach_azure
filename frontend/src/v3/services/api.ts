import { getApiBase } from '../../config';
import type { ChatResponseV2, StageIntroPayload, StageSummaryPayload } from '../types';
import type { ToolSubmitResponse } from '../types';

// Re-export shared API functions that don't depend on UX version
export {
  QuotaExceededError,
  ConflictError,
  listConversations,
  loadConversation,
  createConversation,
  fetchUserGender,
  fetchDeepAnalysis,
  grantAnalysisConsent,
} from '../../v2/services/api';
export type { ConversationListItem, ConversationLoadData, DeepViewLetter } from '../../v2/services/api';

const UX_VERSION_HEADER = { 'X-UX-Version': '3' };

async function authHeaders(
  getToken: (opts?: { skipCache?: boolean }) => Promise<string | null>,
  skipCache = false,
): Promise<Record<string, string>> {
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
  const res = await fetch(url, { ...init, headers: { ...headers, ...((init?.headers as Record<string, string>) || {}) } });
  if (res.status === 401) {
    const freshHeaders = await authHeaders(getToken, true);
    return fetch(url, { ...init, headers: { ...freshHeaders, ...((init?.headers as Record<string, string>) || {}) } });
  }
  return res;
}

// ---------------------------------------------------------------------------
// Chat — identical to V2 but sends X-UX-Version: 3
// ---------------------------------------------------------------------------

import { QuotaExceededError, ConflictError } from '../../v2/services/api';

export async function sendMessageV3(
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

// ---------------------------------------------------------------------------
// Stage transitions — same endpoints, V3 header
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Tool submission — V3 specific
// ---------------------------------------------------------------------------

export async function submitToolResponse(
  conversationId: number,
  toolType: string,
  data: Record<string, unknown>,
  getToken: (opts?: { skipCache?: boolean }) => Promise<string | null>,
): Promise<ToolSubmitResponse> {
  const base = getApiBase();
  const res = await fetchWithAuthRetry(`${base}/tools/${conversationId}/submit`, getToken, {
    method: 'POST',
    body: JSON.stringify({ tool_type: toolType, data }),
  });
  if (!res.ok) throw new Error(`Tool submit failed: ${res.status}`);
  return res.json();
}
