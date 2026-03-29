import { ClerkProvider } from '@clerk/clerk-react';
import { heIL, enUS } from '@clerk/localizations';
import { useTranslation } from 'react-i18next';
import type { ReactNode } from 'react';
import { bsdClerkAppearance } from './clerkAppearance';

const PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

if (!PUBLISHABLE_KEY) {
  throw new Error('Missing Publishable Key');
}

type Props = { children: ReactNode };

/**
 * Clerk localization follows i18n language; appearance matches BSD branding.
 */
export function ClerkProviderBridge({ children }: Props) {
  const { i18n } = useTranslation();
  const localization = i18n.language.startsWith('he') ? heIL : enUS;

  return (
    <ClerkProvider
      publishableKey={PUBLISHABLE_KEY}
      localization={localization}
      appearance={bsdClerkAppearance}
    >
      {children}
    </ClerkProvider>
  );
}
