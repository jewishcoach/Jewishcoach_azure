import { useEffect, useRef } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { apiClient } from '../services/api';
import { clearIntroDraft, loadIntroDraft } from '../lib/introDraftStorage';

/** Push acquaintance draft collected before Clerk login into profile + preferences (once). */
export function IntroDraftSync() {
  const { isSignedIn, isLoaded, getToken } = useAuth();
  const done = useRef(false);

  useEffect(() => {
    if (!isLoaded || !isSignedIn || done.current) return;
    const draft = loadIntroDraft();
    if (!draft?.completed) return;
    done.current = true;

    void (async () => {
      try {
        const token = await getToken();
        if (!token) {
          done.current = false;
          return;
        }
        apiClient.setToken(token);

        const dn = draft.displayName.trim();
        if (draft.gender === 'female' || draft.gender === 'male') {
          await apiClient.updateProfile({
            display_name: dn || undefined,
            gender: draft.gender,
          });
        } else {
          await apiClient.updateProfile({
            display_name: dn || undefined,
            gender: '',
          });
        }

        const prefs: Record<string, unknown> = {};
        if (draft.age != null) prefs.intro_age = draft.age;
        if (draft.intentions?.length) prefs.intro_intentions = draft.intentions;
        if (draft.gender === 'non_binary') prefs.intro_gender_choice = 'non_binary';
        if (draft.gender === 'prefer_not') prefs.intro_gender_choice = 'prefer_not';

        if (Object.keys(prefs).length > 0) {
          await apiClient.updateUserPreferences(prefs);
        }

        clearIntroDraft();
      } catch (e) {
        console.error('[IntroDraftSync]', e);
        done.current = false;
      }
    })();
  }, [isLoaded, isSignedIn, getToken]);

  return null;
}
