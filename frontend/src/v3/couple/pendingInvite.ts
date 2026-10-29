// An invite link (/?v3&couple=<token>) is read once at load, before the login screen: Clerk's sign-up returns to "/"
// without the query, so the token waits in localStorage until the partner signs in and answers the invite.
const KEY = 'couple_invite';

if (typeof window !== 'undefined') {
  const url = new URL(window.location.href);
  const token = url.searchParams.get('couple');
  if (token) {
    try { localStorage.setItem(KEY, token); } catch { /* storage unavailable */ }
    url.searchParams.delete('couple');  // keep the token out of the address bar, screenshots and shares
    window.history.replaceState(null, '', url.pathname + url.search + url.hash);
  }
}

export const pendingInvite = {
  get: (): string | null => {
    try { return localStorage.getItem(KEY); } catch { return null; }
  },
  clear: () => {
    try { localStorage.removeItem(KEY); } catch { /* */ }
  },
};
