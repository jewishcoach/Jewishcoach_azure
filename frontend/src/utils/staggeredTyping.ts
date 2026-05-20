/** Shared char-by-char reveal for onboarding / workspace welcome sequences. */

export const STAGGERED_BLOCK_PAUSE_MS = 420;
export const STAGGERED_CHAR_MS = 26;
export const STAGGERED_CHARS_PER_TICK = 2;

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
): Promise<void> {
  for (let i = 0; i < fullText.length; i += STAGGERED_CHARS_PER_TICK) {
    if (signal.aborted) return;
    onPartial(fullText.slice(0, Math.min(i + STAGGERED_CHARS_PER_TICK, fullText.length)));
    await sleep(STAGGERED_CHAR_MS, signal);
  }
  onPartial(fullText);
}
