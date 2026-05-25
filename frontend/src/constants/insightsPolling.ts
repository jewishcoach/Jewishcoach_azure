/** Background poll for /insights/safe — was 3s; 12s cuts auth/DB load ~4× with little UX loss. */
export const INSIGHTS_POLL_INTERVAL_MS = 12_000;

/** Refresh Clerk JWT before insights fetch to avoid 401 storms after tab idle. */
export async function refreshInsightsAuthToken(
  getToken: (opts?: { skipCache?: boolean }) => Promise<string | null>,
  setToken: (token: string) => void,
): Promise<string | null> {
  const token = await getToken({ skipCache: true });
  if (token) setToken(token);
  return token;
}
