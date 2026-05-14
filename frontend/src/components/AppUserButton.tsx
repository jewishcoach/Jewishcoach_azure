import { UserButton, useAuth, useClerk } from '@clerk/clerk-react';
import { LogOut } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { apiClient } from '../services/api';

/**
 * Wraps Clerk UserButton: resets onboarding completion on the server before signing out
 * so the next login shows BSD onboarding again.
 */
export function AppUserButton() {
  const { signOut } = useClerk();
  const { getToken } = useAuth();
  const { t } = useTranslation();

  const handleSignOut = async () => {
    try {
      const token = await getToken();
      if (token) {
        apiClient.setToken(token);
        await apiClient.patchUserPreferences({ bsd_intro_screens_completed: false });
      }
    } catch {
      /* Sign out even if preference reset fails */
    }
    await signOut({ redirectUrl: '/' });
  };

  return (
    <UserButton
      afterSignOutUrl="/"
      appearance={{
        elements: {
          /** Replaced by custom MenuItems action so we can PATCH prefs first */
          userButtonPopoverActionButton__signOut: '!hidden',
        },
      }}
    >
      <UserButton.MenuItems>
        <UserButton.Action
          label={t('app.signOut')}
          labelIcon={<LogOut className="h-4 w-4" aria-hidden />}
          onClick={() => void handleSignOut()}
        />
      </UserButton.MenuItems>
    </UserButton>
  );
}
