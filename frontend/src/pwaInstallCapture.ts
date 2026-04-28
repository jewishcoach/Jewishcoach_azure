/**
 * Capture `beforeinstallprompt` as early as possible.
 * If the listener only lived inside Dashboard, the event could fire while the user
 * was on Chat — we'd miss preventDefault() and lose the programmatic prompt (Chrome
 * still shows Install in the omnibox, but our card had no button).
 */

export interface PwaDeferredPrompt extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

export const PWA_INSTALL_READY_EVENT = 'jewishcoach:pwa-install-ready';
export const PWA_INSTALLED_EVENT = 'jewishcoach:pwa-installed';

let captured: PwaDeferredPrompt | null = null;

export function getCapturedInstallPrompt(): PwaDeferredPrompt | null {
  return captured;
}

export function clearCapturedInstallPrompt(): void {
  captured = null;
}

function attach(): void {
  if (typeof window === 'undefined') return;

  window.addEventListener('beforeinstallprompt', (e: Event) => {
    e.preventDefault();
    captured = e as PwaDeferredPrompt;
    window.dispatchEvent(new CustomEvent(PWA_INSTALL_READY_EVENT));
  });

  window.addEventListener('appinstalled', () => {
    captured = null;
    window.dispatchEvent(new CustomEvent(PWA_INSTALLED_EVENT));
  });
}

attach();
