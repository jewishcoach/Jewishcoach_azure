/**
 * Application Configuration
 * Centralized config for feature flags and environment settings.
 */

/**
 * BSD Version Toggle
 * 
 * V1: Multi-layer architecture (router → reasoner → coach → talker)
 * V2 (default): Single-agent conversational coach with Shehiya principles
 * 
 * To switch to V1, set BSD_VERSION=v1 in localStorage or change default here.
 */
export const BSD_VERSION = (localStorage.getItem('bsd_version') || 'v2') as 'v1' | 'v2';

/** Free (basic) plan monthly message cap — keep in sync with backend PLAN_LIMITS["basic"].messages_per_month */
export const BASIC_PLAN_MESSAGES_PER_MONTH = 1000;

/** Free (basic) plan Azure Speech minutes per month (-1 = unlimited). Keep in sync with backend PLAN_LIMITS["basic"].speech_minutes_per_month */
export const BASIC_PLAN_SPEECH_MINUTES_PER_MONTH = -1;

/**
 * Clerk user ids that may show the Admin UI entry without relying only on /users/me (comma-separated).
 * Keep in sync with Azure `ADMIN_CLERK_IDS`. Set at build time (`VITE_ADMIN_CLERK_IDS`).
 */
export function isClerkUiAdminAllowlisted(clerkUserId: string | undefined): boolean {
  if (!clerkUserId) return false;
  const raw = (import.meta.env.VITE_ADMIN_CLERK_IDS || '').trim();
  if (!raw) return false;
  const ids = raw.split(',').map((s: string) => s.trim()).filter(Boolean);
  return ids.includes(clerkUserId);
}

/** Production API host on App Service custom domain (TLS via Managed Certificate — see scripts/bind_app_service_api_hostname_tls.sh). */
const PRODUCTION_API_CUSTOM_DOMAIN = 'https://api.jewishcoacher.com/api';

/** Default Azure hostname when the SPA is not served from production custom domains (e.g. *.azurestaticapps.net only). */
const PRODUCTION_API_AZURE_DEFAULT = 'https://jewishcoach-api.azurewebsites.net/api';

/** Production sites whose SPA should call api.jewishcoacher.com when VITE_API_URL is unset. */
function isProductionFrontendHost(hostname: string): boolean {
  return (
    hostname === 'jewishcoacher.com' ||
    hostname === 'www.jewishcoacher.com' ||
    hostname === 'bsdcoach.com' ||
    hostname === 'www.bsdcoach.com'
  );
}

/** Session hint: browser couldn't complete TLS to api.jewishcoacher.com; use App Service hostname immediately on next load. */
export const SESSION_API_TLS_FALLBACK_KEY = 'bsd_api_use_appservice_tls';

export function shouldUsePersistedAppServiceApi(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    return sessionStorage.getItem(SESSION_API_TLS_FALLBACK_KEY) === '1';
  } catch {
    return false;
  }
}

export function persistUseAppServiceApiForSession(): void {
  try {
    sessionStorage.setItem(SESSION_API_TLS_FALLBACK_KEY, '1');
  } catch {
    /* private mode / blocked storage */
  }
}

/** Normalize API base URL - backend expects /api prefix. Exported for api.ts */
export function getApiBase(): string {
  const viteRaw = import.meta.env.VITE_API_URL;
  const vite = typeof viteRaw === 'string' ? viteRaw.trim() : '';
  if (vite) {
    let base = vite.endsWith('/api') ? vite : `${vite.replace(/\/$/, '')}/api`;
    try {
      if (new URL(base).hostname === 'api.jewishcoacher.com' && shouldUsePersistedAppServiceApi()) {
        base = PRODUCTION_API_AZURE_DEFAULT;
      }
    } catch {
      /* ignore */
    }
    return base;
  }

  if (typeof window !== 'undefined') {
    const h = window.location.hostname;
    if (isProductionFrontendHost(h)) {
      if (shouldUsePersistedAppServiceApi()) {
        return PRODUCTION_API_AZURE_DEFAULT;
      }
      return PRODUCTION_API_CUSTOM_DOMAIN;
    }
    if (!h.includes('localhost')) {
      return PRODUCTION_API_AZURE_DEFAULT;
    }
  }

  return 'http://localhost:8000/api';
}

/** Same App Service as api.jewishcoacher.com — retry target when browser TLS to custom hostname fails (local DNS/AV). */
export function apiTlsFallbackBase(currentApiBase: string): string | null {
  try {
    const u = new URL(currentApiBase);
    if (u.hostname !== 'api.jewishcoacher.com') return null;
    return PRODUCTION_API_AZURE_DEFAULT;
  } catch {
    return null;
  }
}

/**
 * Get BSD API endpoint based on version
 */
export function getBsdEndpoint(conversationId: number, version: 'v1' | 'v2' = BSD_VERSION): string {
  const baseUrl = getApiBase();
  
  if (version === 'v2') {
    return `${baseUrl}/chat/v2/message`;
  }
  
  // V1 (streaming)
  return `${baseUrl}/chat/conversations/${conversationId}/messages`;
}

/**
 * Toggle BSD version (for testing)
 */
export function setBsdVersion(version: 'v1' | 'v2') {
  localStorage.setItem('bsd_version', version);
  window.location.reload();  // Reload to apply changes
}

// Export for debugging
if (import.meta.env.DEV) {
  (window as any).setBsdVersion = setBsdVersion;
  console.log('🔧 [CONFIG] BSD Version:', BSD_VERSION);
  console.log('🔧 [CONFIG] To switch to V1: window.setBsdVersion("v1")');
  console.log('🔧 [CONFIG] To switch to V2: window.setBsdVersion("v2")');
}
