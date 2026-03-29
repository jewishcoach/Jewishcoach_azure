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

/** API when the SPA is served from the production custom domain (see scripts/setup_jewishcoacher_domain.sh). */
const PRODUCTION_API_CUSTOM_DOMAIN = 'https://api.jewishcoacher.com/api';

/** Legacy Azure default hostname (SWA + App Service *.azurewebsites.net). */
const PRODUCTION_API_AZURE_DEFAULT = 'https://jewishcoach-api.azurewebsites.net/api';

function isJewishcoacherHost(hostname: string): boolean {
  return hostname === 'jewishcoacher.com' || hostname === 'www.jewishcoacher.com';
}

/** Normalize API base URL - backend expects /api prefix. Exported for api.ts */
export function getApiBase(): string {
  let base: string | undefined;

  if (typeof window !== 'undefined') {
    const h = window.location.hostname;
    if (isJewishcoacherHost(h)) {
      base = PRODUCTION_API_CUSTOM_DOMAIN;
    }
  }

  if (!base) {
    base = import.meta.env.VITE_API_URL;
  }

  if (!base || base.trim() === '') {
    if (typeof window !== 'undefined' && !window.location.hostname.includes('localhost')) {
      base = PRODUCTION_API_AZURE_DEFAULT;
    } else {
      base = 'http://localhost:8000/api';
    }
  }
  return base.endsWith('/api') ? base : `${base.replace(/\/$/, '')}/api`;
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
