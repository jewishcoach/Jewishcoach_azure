import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { Download, Smartphone, MonitorDown } from 'lucide-react';
import {
  clearCapturedInstallPrompt,
  getCapturedInstallPrompt,
  PWA_INSTALL_READY_EVENT,
  PWA_INSTALLED_EVENT,
} from '../pwaInstallCapture';

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
  /** True when Chromium exposed a deferred install prompt we captured early */
  const [hasDeferred, setHasDeferred] = useState(() => !!getCapturedInstallPrompt());
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setInstalled(isStandalone());
  }, []);

  useEffect(() => {
    const sync = () => setHasDeferred(!!getCapturedInstallPrompt());
    const onInstalledEvt = () => {
      setInstalled(true);
      setHasDeferred(false);
    };
    window.addEventListener(PWA_INSTALL_READY_EVENT, sync);
    window.addEventListener(PWA_INSTALLED_EVENT, onInstalledEvt);
    sync();
    return () => {
      window.removeEventListener(PWA_INSTALL_READY_EVENT, sync);
      window.removeEventListener(PWA_INSTALLED_EVENT, onInstalledEvt);
    };
  }, []);

  const promptInstall = useCallback(async () => {
    const d = getCapturedInstallPrompt();
    if (!d) return;
    setBusy(true);
    try {
      await d.prompt();
      await d.userChoice;
      clearCapturedInstallPrompt();
      setHasDeferred(false);
    } finally {
      setBusy(false);
    }
  }, []);

  if (installed) {
    return (
      <PwaCardShell colors={colors}>
        <div className="flex items-center gap-3 min-w-0">
          <div
            className="p-2.5 rounded-xl shrink-0"
            style={{ background: `${colors.accent}14` }}
            aria-hidden
          >
            <Smartphone className="w-5 h-5" style={{ color: colors.accent }} />
          </div>
          <p className="text-sm leading-snug min-w-0" style={{ color: colors.textMuted }}>
            {t('pwa.installedHint')}
          </p>
        </div>
      </PwaCardShell>
    );
  }

  const ios = isIosTouch();

  return (
    <PwaCardShell colors={colors}>
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between lg:gap-6">
        <div className="flex items-start gap-3 min-w-0 flex-1 lg:items-center">
          <div
            className="p-2.5 rounded-xl shrink-0"
            style={{ background: `${colors.accent}14` }}
            aria-hidden
          >
            <Smartphone className="w-[22px] h-[22px]" style={{ color: colors.accent }} />
          </div>
          <div className="min-w-0">
            <h3 className="text-[15px] font-semibold leading-tight mb-1" style={{ color: colors.text }}>
              {t('pwa.title')}
            </h3>
            <p className="text-[13px] leading-snug" style={{ color: colors.textMuted }}>
              {t('pwa.subtitle')}
            </p>
          </div>
        </div>

        {!ios && hasDeferred ? (
          <button
            type="button"
            disabled={busy}
            onClick={() => void promptInstall()}
            className="inline-flex items-center justify-center gap-2 h-10 px-6 rounded-[10px] text-[13.5px] font-semibold text-[#e8e4dc] shrink-0 w-full lg:w-auto disabled:opacity-50 transition-opacity"
            style={{ background: colors.accent }}
          >
            <Download className="w-4 h-4 shrink-0" />
            {busy ? t('pwa.installing') : t('pwa.installButton')}
          </button>
        ) : null}
      </div>

      {ios ? (
        <div className="mt-4 pt-4 border-t" style={{ borderColor: colors.border }}>
          <p className="font-medium text-xs mb-2" style={{ color: colors.textMuted }}>
            {t('pwa.iosTitle')}
          </p>
          <ol className="list-decimal list-inside space-y-1.5 text-[13px] leading-relaxed ps-1" style={{ color: colors.text }}>
            <li>{t('pwa.iosStep1')}</li>
            <li>{t('pwa.iosStep2')}</li>
          </ol>
        </div>
      ) : null}

      {!ios && !hasDeferred ? (
        <div className="mt-4 pt-4 border-t space-y-3" style={{ borderColor: colors.border }}>
          <div
            className="flex items-start gap-3 rounded-xl p-3.5 text-[13px] leading-relaxed"
            style={{
              background: `${colors.accent}08`,
              borderWidth: 1,
              borderStyle: 'solid',
              borderColor: colors.border,
              color: colors.text,
            }}
          >
            <MonitorDown className="w-5 h-5 shrink-0 mt-0.5" style={{ color: colors.accent }} aria-hidden />
            <div>
              <p className="font-semibold text-[13px] mb-1" style={{ color: colors.text }}>
                {t('pwa.omniboxTitle')}
              </p>
              <p style={{ color: colors.textMuted }}>{t('pwa.omniboxBody')}</p>
            </div>
          </div>
          <p className="text-[12px] leading-relaxed" style={{ color: colors.textMuted }}>
            {t('pwa.chromeManualHint')}
          </p>
        </div>
      ) : null}
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
      className="rounded-2xl px-5 py-4 md:px-6 md:py-5"
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
