import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { Download, Smartphone } from 'lucide-react';

/** Chromium `beforeinstallprompt` (not in TS DOM lib). */
interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

function isStandalone(): boolean {
  return (
    window.matchMedia('(display-mode: standalone)').matches ||
    window.matchMedia('(display-mode: fullscreen)').matches ||
    (window.navigator as Navigator & { standalone?: boolean }).standalone === true
  );
}

function isIosTouch(): boolean {
  const ua = navigator.userAgent;
  const iOS = /iPad|iPhone|iPod/.test(ua);
  const iPadOs13Plus = navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1;
  return iOS || iPadOs13Plus;
}

type Palette = {
  card: string;
  text: string;
  textMuted: string;
  accent: string;
  border: string;
  shadow: string;
};

interface PwaInstallCardProps {
  colors: Palette;
}

export function PwaInstallCard({ colors }: PwaInstallCardProps) {
  const { t } = useTranslation();
  const [installed, setInstalled] = useState(() => isStandalone());
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setInstalled(isStandalone());
  }, []);

  useEffect(() => {
    const onBeforeInstall = (e: Event) => {
      e.preventDefault();
      setDeferred(e as BeforeInstallPromptEvent);
    };
    const onInstalled = () => {
      setInstalled(true);
      setDeferred(null);
    };
    window.addEventListener('beforeinstallprompt', onBeforeInstall);
    window.addEventListener('appinstalled', onInstalled);
    return () => {
      window.removeEventListener('beforeinstallprompt', onBeforeInstall);
      window.removeEventListener('appinstalled', onInstalled);
    };
  }, []);

  const promptInstall = useCallback(async () => {
    if (!deferred) return;
    setBusy(true);
    try {
      await deferred.prompt();
      await deferred.userChoice;
      setDeferred(null);
    } finally {
      setBusy(false);
    }
  }, [deferred]);

  if (installed) {
    return (
      <PwaCardShell colors={colors}>
        <p className="text-sm" style={{ color: colors.textMuted }}>
          {t('pwa.installedHint')}
        </p>
      </PwaCardShell>
    );
  }

  const ios = isIosTouch();

  return (
    <PwaCardShell colors={colors}>
      <div className="flex items-start gap-3 mb-3">
        <div
          className="p-2 rounded-lg flex-shrink-0"
          style={{ background: `${colors.accent}14` }}
          aria-hidden
        >
          <Smartphone className="w-5 h-5" style={{ color: colors.accent }} />
        </div>
        <div>
          <h3 className="text-base font-semibold mb-1" style={{ color: colors.text }}>
            {t('pwa.title')}
          </h3>
          <p className="text-xs leading-snug" style={{ color: colors.textMuted }}>
            {t('pwa.subtitle')}
          </p>
        </div>
      </div>

      {ios ? (
        <div className="space-y-2 text-sm" style={{ color: colors.text }}>
          <p className="font-medium text-xs" style={{ color: colors.textMuted }}>
            {t('pwa.iosTitle')}
          </p>
          <ol className="list-decimal list-inside space-y-1.5 text-[13px] leading-relaxed ps-1">
            <li>{t('pwa.iosStep1')}</li>
            <li>{t('pwa.iosStep2')}</li>
          </ol>
        </div>
      ) : (
        <div className="space-y-3">
          {deferred ? (
            <button
              type="button"
              disabled={busy}
              onClick={() => void promptInstall()}
              className="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-lg text-white disabled:opacity-50 transition-opacity"
              style={{ background: colors.accent }}
            >
              <Download className="w-4 h-4" />
              {busy ? t('pwa.installing') : t('pwa.installButton')}
            </button>
          ) : (
            <p className="text-[13px] leading-relaxed" style={{ color: colors.textMuted }}>
              {t('pwa.chromeManualHint')}
            </p>
          )}
        </div>
      )}
    </PwaCardShell>
  );
}

function PwaCardShell({
  colors,
  children,
}: {
  colors: Palette;
  children: ReactNode;
}) {
  return (
    <div
      className="rounded-xl p-5 md:p-6"
      style={{
        background: colors.card,
        boxShadow: colors.shadow,
        borderWidth: 1,
        borderStyle: 'solid',
        borderColor: colors.border,
      }}
    >
      {children}
    </div>
  );
}
