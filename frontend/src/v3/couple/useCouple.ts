import { useCallback, useEffect, useState } from 'react';
import {
  coupleApi, CoupleApiError, inviteLink,
  type Checkpoint, type CoupleStatus, type Gender, type InvitePreview, type SharedScreenData, type ShareLine,
} from './coupleApi';
import { inviteMessage } from './lines';
import { pendingInvite } from './pendingInvite';

type GetToken = (opts?: { skipCache?: boolean }) => Promise<string | null>;

/** A couple screen shown instead of the regular flow; null = the regular flow */
export type CoupleView =
  | { kind: 'start' }
  | { kind: 'invite'; sessionId: number; conversationId: number; token: string; title: string; name: string; gender: Gender | null }
  | { kind: 'join'; token: string; preview: InvitePreview | null }
  | { kind: 'preview'; checkpoint: Checkpoint; sessionId: number; lines: ShareLine[] }
  | { kind: 'waiting'; checkpoint: Checkpoint; sessionId: number }
  | { kind: 'shared'; checkpoint: Checkpoint; sessionId: number; data: SharedScreenData };

interface UseCoupleOptions {
  getToken: GetToken;
  isSignedIn: boolean | undefined;
  /** opens the member's own (already created) conversation with its first message */
  startConversationWith: (conversationId: number, firstMessage: string) => Promise<void>;
  /** the intro of a macro-stage (after the mirror screen: כמ"ז) */
  goToStage: (stageId: string) => Promise<void>;
  resumeConversation: (conversationId: number) => Promise<void>;
}

const POLL_MS = 15_000;
const firstMessage = (title: string) => `תהליך זוגי — האירוע: ${title}`;
const stepNum = (step: string | undefined) => Number(String(step || 'S0').replace('S', '')) || 0;

export function useCouple({ getToken, isSignedIn, startConversationWith, goToStage, resumeConversation }: UseCoupleOptions) {
  const [canStart, setCanStart] = useState(false);
  const [view, setView] = useState<CoupleView | null>(null);
  const [status, setStatus] = useState<CoupleStatus | null>(null);  // the process of the open conversation
  const [sessions, setSessions] = useState<CoupleStatus[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [remind, setRemind] = useState<{ text: string; link: string } | null>(null);

  // Pilot flag + an invite link that waited through sign-in
  useEffect(() => {
    if (!isSignedIn) return;
    coupleApi.enabled(getToken).then((r) => setCanStart(r.can_start)).catch(() => setCanStart(false));
    const token = pendingInvite.get();
    if (token) setView({ kind: 'join', token, preview: null });
  }, [isSignedIn, getToken]);

  const joinToken = view?.kind === 'join' && !view.preview ? view.token : null;
  useEffect(() => {
    if (!joinToken) return;
    coupleApi.invite(getToken, joinToken)
      .then((preview) => setView((v) => (v?.kind === 'join' ? { ...v, preview } : v)))
      .catch(() => setView((v) => (v?.kind === 'join' ? { ...v, preview: { state: 'not_found' } } : v)));
  }, [joinToken, getToken]);

  const fail = (e: unknown) => setError(
    e instanceof CoupleApiError && e.status === 422 && e.message ? e.message : 'משהו השתבש. נסה שוב בעוד רגע.');

  const openStart = useCallback(() => { setError(null); setView({ kind: 'start' }); }, []);
  const close = useCallback(() => { setError(null); setView(null); }, []);

  const start = useCallback(async (title: string, name: string, gender: Gender | null) => {
    setBusy(true); setError(null);
    try {
      const r = await coupleApi.start(getToken, title, name, gender);
      setView({ kind: 'invite', sessionId: r.session_id, conversationId: r.conversation_id, token: r.invite_token, title, name, gender });
    } catch (e) { fail(e); } finally { setBusy(false); }
  }, [getToken]);

  const beginMyPart = useCallback(async (conversationId: number, sessionId: number, title: string) => {
    setView(null);
    coupleApi.status(getToken, sessionId).then(setStatus).catch(() => {});
    await startConversationWith(conversationId, firstMessage(title));
  }, [getToken, startConversationWith]);

  const join = useCallback(async (name: string, gender: Gender | null) => {
    if (view?.kind !== 'join' || !view.preview?.event_title) return;
    const { token, preview } = view;
    setBusy(true); setError(null);
    try {
      const r = await coupleApi.accept(getToken, token, name, gender);
      pendingInvite.clear();
      await beginMyPart(r.conversation_id, r.session_id, preview.event_title as string);
    } catch (e) { fail(e); } finally { setBusy(false); }
  }, [view, getToken, beginMyPart]);

  const dismissJoin = useCallback(() => { pendingInvite.clear(); setView(null); }, []);

  const continueJoined = useCallback(async (conversationId: number) => {
    pendingInvite.clear();
    setView(null);
    await resumeConversation(conversationId);
  }, [resumeConversation]);

  const showShared = useCallback(async (sessionId: number, checkpoint: Checkpoint) => {
    const data = await coupleApi.shared(getToken, sessionId, checkpoint);
    setView({ kind: 'shared', checkpoint, sessionId, data });
  }, [getToken]);

  /** The couple step at the end of discovery / of the process. False = not a couple step now (continue normally). */
  const openCheckpoint = useCallback(async (checkpoint: Checkpoint, sid: number): Promise<boolean> => {
    setBusy(true); setError(null); setRemind(null);
    try {
      const st = await coupleApi.status(getToken, sid);
      setStatus(st);
      if (st.status === 'cancelled' || st.me.left) return false;
      if (checkpoint === 'mirror' ? st.mirror_open : st.commitment_open) {
        await showShared(sid, checkpoint);
        return true;
      }
      if (checkpoint === 'mirror' ? st.me.mirror_done : st.me.commitment_done) {
        setView({ kind: 'waiting', checkpoint, sessionId: sid });
        return true;
      }
      const draft = await coupleApi.draft(getToken, sid, checkpoint);
      setView({ kind: 'preview', checkpoint, sessionId: sid, lines: draft.lines });
      return true;
    } catch (e) {
      if (!(e instanceof CoupleApiError && e.code === 'not_ready')) console.error('[Couple] openCheckpoint', e);
      return false;
    } finally { setBusy(false); }
  }, [getToken, showShared]);

  const approve = useCallback(async (lines: { id: string; text: string; visible: boolean }[]) => {
    if (view?.kind !== 'preview') return;
    const { sessionId, checkpoint } = view;
    setBusy(true); setError(null);
    try {
      const st = await coupleApi.approve(getToken, sessionId, checkpoint, lines);
      setStatus(st);
      if (checkpoint === 'mirror' ? st.mirror_open : st.commitment_open) await showShared(sessionId, checkpoint);
      else setView({ kind: 'waiting', checkpoint, sessionId });
    } catch (e) { fail(e); } finally { setBusy(false); }
  }, [view, getToken, showShared]);

  // Waiting: only the status is polled; the shared screen opens by itself once both approved
  const waitingFor = view?.kind === 'waiting' ? `${view.sessionId}:${view.checkpoint}` : null;
  useEffect(() => {
    if (!waitingFor) return;
    const [sid, checkpoint] = waitingFor.split(':') as [string, Checkpoint];
    let stopped = false;
    const id = setInterval(async () => {
      try {
        const st = await coupleApi.status(getToken, Number(sid));
        if (stopped) return;
        setStatus(st);
        if (checkpoint === 'mirror' ? st.mirror_open : st.commitment_open) await showShared(Number(sid), checkpoint);
      } catch { /* next tick */ }
    }, POLL_MS);
    return () => { stopped = true; clearInterval(id); };
  }, [waitingFor, getToken, showShared]);

  const prepareRemind = useCallback(async () => {
    if (!status) return;
    try {
      if (!status.partner && status.role === 'inviter') {
        const { invite_token } = await coupleApi.renewInvite(getToken, status.session_id);
        const link = inviteLink(invite_token);
        setRemind({ text: inviteMessage(status.me.name, status.me.gender, status.event_title, link), link });
      } else {
        const link = `${window.location.origin}/?v3`;
        setRemind({ text: `סיימתי את החלק שלי בתהליך שלנו על ״${status.event_title}״. מחכה לך כשיתאים לך 🙂\n${link}`, link });
      }
    } catch (e) { fail(e); }
  }, [status, getToken]);

  /** Leaves the shared part; after the discovery stage the member goes on to כמ"ז alone */
  const afterShared = useCallback(async (checkpoint: Checkpoint) => {
    setView(null);
    if (checkpoint === 'mirror') await goToStage('kamaz');
  }, [goToStage]);

  const cancel = useCallback(async () => {
    if (!status) return;
    try { setStatus(await coupleApi.cancel(getToken, status.session_id)); } catch (e) { fail(e); }
  }, [status, getToken]);

  /** The open conversation changed (start, resume, reload): find its process and, at a couple step, show it */
  const syncConversation = useCallback(async (conversationId: number, currentStep: string) => {
    let list: CoupleStatus[] = [];
    try { list = await coupleApi.sessions(getToken); } catch { /* not critical */ }
    setSessions(list);
    const mine = list.find((s) => s.conversation_id === conversationId) ?? null;
    setStatus(mine);
    if (!mine || mine.status === 'cancelled' || mine.me.left) return;
    const n = stepNum(currentStep);
    if (n === 11) await openCheckpoint('mirror', mine.session_id);
    else if (n >= 15) await openCheckpoint('commitment', mine.session_id);
  }, [getToken, openCheckpoint]);

  /** No open conversation (new conversation screen) — nothing couple-related applies */
  const clearStatus = useCallback(() => setStatus(null), []);

  const refreshSessions = useCallback(async () => {
    try { setSessions(await coupleApi.sessions(getToken)); } catch { /* */ }
  }, [getToken]);

  return {
    canStart, view, status, sessions, busy, error, remind,
    openStart, close, start, beginMyPart, join, dismissJoin, continueJoined,
    openCheckpoint, approve, prepareRemind, afterShared, cancel, syncConversation, refreshSessions, clearStatus,
  };
}
