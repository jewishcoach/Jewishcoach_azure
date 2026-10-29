import { useAuth, useUser } from '@clerk/clerk-react';

/**
 * Clerk auth for V3, with a dev-only bypass for browser E2E tests (Playwright).
 * Enabled only in `vite dev` with localStorage `e2e_demo=true`; the backend accepts the
 * demo token only when ALLOW_DEMO_MODE + ALLOW_DEMO_LOCALHOST are set. `import.meta.env.DEV`
 * is false in production builds, so the bypass is dead code there.
 * `e2e_demo_user=<suffix>` makes a separate demo user per browser context (couple-process tests).
 */
const E2E_DEMO = import.meta.env.DEV && localStorage.getItem('e2e_demo') === 'true';
const E2E_USER = E2E_DEMO ? localStorage.getItem('e2e_demo_user') : null;

const demoToken = E2E_USER ? `demo_tunnel_token:${E2E_USER}` : 'demo_tunnel_token';
const demoGetToken = async () => demoToken;
const demoSignOut = async () => {};
const demoUser = { firstName: E2E_USER || 'E2E', lastName: 'Demo', primaryEmailAddress: { emailAddress: 'demo@tunnel.test' } };

export function useV3Auth() {
  const auth = useAuth();
  if (E2E_DEMO) {
    return { isSignedIn: true, isLoaded: true, getToken: demoGetToken, signOut: demoSignOut };
  }
  return auth;
}

export function useV3User() {
  const { user } = useUser();
  return { user: E2E_DEMO ? demoUser : user };
}
