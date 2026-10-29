import { getApiBase } from '../../config';
import { fetchWithAuthRetry } from '../services/api';

type GetToken = (opts?: { skipCache?: boolean }) => Promise<string | null>;
export type Checkpoint = 'mirror' | 'commitment';
export type Gender = 'male' | 'female';

export interface ShareLine {
  id: string;
  text: string;
}

export interface CoupleStatus {
  session_id: number;
  event_title: string;
  status: 'invited' | 'active' | 'cancelled';
  role: 'inviter' | 'invitee';
  conversation_id: number | null;
  me: { name: string; gender: Gender | null; mirror_done: boolean; commitment_done: boolean; left: boolean };
  partner: { name: string; gender: Gender | null; mirror_done: boolean; commitment_done: boolean } | null;
  mirror_open: boolean;
  commitment_open: boolean;
  mirror_seen: boolean;
  commitment_seen: boolean;
  invite_expired: boolean;
}

export interface InvitePreview {
  state: 'valid' | 'own' | 'joined' | 'used' | 'expired' | 'not_found';
  session_id?: number;
  conversation_id?: number;
  inviter_name?: string;
  inviter_gender?: Gender | null;
  event_title?: string;
}

export interface SharedSide {
  name: string;
  gender: Gender | null;
  lines: ShareLine[];
}

export interface SharedScreenData {
  event_title: string;
  me: SharedSide;
  partner: SharedSide;
}

/** Server rejected the input — `message` is user-facing Hebrew when the server sent one. */
export class CoupleApiError extends Error {
  status: number;
  code?: string;

  constructor(status: number, code?: string, message?: string) {
    super(message || `Couple API ${status}`);
    this.status = status;
    this.code = code;
  }
}

async function call<T>(path: string, getToken: GetToken, init?: RequestInit): Promise<T> {
  const res = await fetchWithAuthRetry(`${getApiBase()}/couple${path}`, getToken, init);
  if (res.ok) return res.json();
  const body = await res.json().catch(() => null);
  const detail = body?.detail;
  throw new CoupleApiError(res.status, detail?.code ?? detail?.error, detail?.message);
}

const post = (body?: unknown): RequestInit => ({ method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) });

export const coupleApi = {
  enabled: (t: GetToken) => call<{ can_start: boolean }>('/enabled', t),
  start: (t: GetToken, eventTitle: string, displayName: string, gender: Gender | null) =>
    call<{ session_id: number; conversation_id: number; invite_token: string }>(
      '/sessions', t, post({ event_title: eventTitle, display_name: displayName, gender })),
  renewInvite: (t: GetToken, sessionId: number) =>
    call<{ invite_token: string }>(`/sessions/${sessionId}/invite`, t, post()),
  invite: async (t: GetToken, token: string): Promise<InvitePreview> => {
    try {
      return await call<InvitePreview>(`/invites/${encodeURIComponent(token)}`, t);
    } catch (e) {
      if (e instanceof CoupleApiError && e.status === 404) return { state: 'not_found' };
      throw e;
    }
  },
  accept: (t: GetToken, token: string, displayName: string, gender: Gender | null) =>
    call<{ session_id: number; conversation_id: number }>(
      `/invites/${encodeURIComponent(token)}/accept`, t, post({ display_name: displayName, gender })),
  sessions: (t: GetToken) => call<CoupleStatus[]>('/sessions', t),
  status: (t: GetToken, sessionId: number) => call<CoupleStatus>(`/sessions/${sessionId}`, t),
  draft: (t: GetToken, sessionId: number, cp: Checkpoint) =>
    call<{ lines: ShareLine[]; approved: ShareLine[] | null; locked: boolean }>(`/sessions/${sessionId}/${cp}/draft`, t),
  approve: (t: GetToken, sessionId: number, cp: Checkpoint, lines: { id: string; text: string; visible: boolean }[]) =>
    call<CoupleStatus>(`/sessions/${sessionId}/${cp}`, t, post({ lines })),
  shared: (t: GetToken, sessionId: number, cp: Checkpoint) => call<SharedScreenData>(`/sessions/${sessionId}/${cp}`, t),
  cancel: (t: GetToken, sessionId: number) => call<CoupleStatus>(`/sessions/${sessionId}/cancel`, t, post()),
};

/** The link the partner opens: `v3` switches them to the V3 app, `couple` carries the one-time token. */
export function inviteLink(token: string): string {
  return `${window.location.origin}/?v3&couple=${encodeURIComponent(token)}`;
}
