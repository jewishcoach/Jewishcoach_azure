/** Shared char-by-char reveal for onboarding / workspace welcome sequences. */

export const STAGGERED_BLOCK_PAUSE_MS = 420;
export const STAGGERED_CHAR_MS = 26;
export const STAGGERED_CHARS_PER_TICK = 2;

/** Workspace welcome — one bubble, slightly slower than onboarding blocks. */
export const WORKSPACE_WELCOME_CHAR_MS = 38;
export const WORKSPACE_WELCOME_CHARS_PER_TICK = 1;

export type RevealTypedOptions = {
  charMs?: number;
  charsPerTick?: number;
};

export function sleep(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise<void>((resolve) => {
    if (signal.aborted) {
      resolve();
      return;
    }
    const id = window.setTimeout(() => resolve(), ms);
    signal.addEventListener(
      'abort',
      () => {
        window.clearTimeout(id);
        resolve();
      },
      { once: true },
    );
  });
}

export async function revealTypedBlock(
  fullText: string,
  onPartial: (partial: string) => void,
  signal: AbortSignal,
  options?: RevealTypedOptions,
): Promise<void> {
  const charMs = options?.charMs ?? STAGGERED_CHAR_MS;
  const charsPerTick = options?.charsPerTick ?? STAGGERED_CHARS_PER_TICK;
  for (let i = 0; i < fullText.length; i += charsPerTick) {
    if (signal.aborted) return;
    onPartial(fullText.slice(0, Math.min(i + charsPerTick, fullText.length)));
    await sleep(charMs, signal);
  }
  onPartial(fullText);
}
