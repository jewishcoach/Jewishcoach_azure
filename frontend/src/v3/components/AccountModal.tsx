import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { fetchMyProfile, updateMyProfile, type MyProfile } from '../services/api';

// "החשבון שלי": the client's name and how the coach and the cards address them. V3 never asked the gender (the
// old onboarding did), so most V3 users had none and got the masculine everywhere.
interface AccountModalProps {
  open: boolean;
  onClose: () => void;
  getToken: (opts?: { skipCache?: boolean }) => Promise<string | null>;
  onSaved: (profile: MyProfile) => void;
}

const HEEBO = { fontFamily: "'Heebo', sans-serif" };

export function AccountModal({ open, onClose, getToken, onSaved }: AccountModalProps) {
  const [profile, setProfile] = useState<MyProfile | null>(null);
  const [name, setName] = useState('');
  const [gender, setGender] = useState<'male' | 'female' | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!open) return;
    setError(false);
    fetchMyProfile(getToken)
      .then((p) => { setProfile(p); setName(p.display_name || ''); setGender(p.gender); })
      .catch(() => setError(true));
  }, [open, getToken]);

  if (!open) return null;

  const changed = !!profile && (name.trim() !== (profile.display_name || '') || gender !== profile.gender);

  const save = async () => {
    if (!changed || saving) return;
    setSaving(true); setError(false);
    try {
      const update: { display_name?: string; gender?: 'male' | 'female' } = {};
      if (name.trim() !== (profile?.display_name || '')) update.display_name = name.trim();
      if (gender && gender !== profile?.gender) update.gender = gender;
      const saved = await updateMyProfile(getToken, update);
      onSaved(saved);
      onClose();
    } catch {
      setError(true);
    } finally {
      setSaving(false);
    }
  };

  const choice = (value: 'male' | 'female', label: string) => (
    <button
      type="button"
      onClick={() => setGender(value)}
      className={`flex-1 h-[52px] rounded-xl border text-base transition-all
        ${gender === value ? 'bg-[#9747ff] border-[#9747ff] text-white' : 'bg-white border-[#e0ddd8] text-[#2d4658] hover:border-[#9747ff]'}`}
      style={HEEBO}
    >
      {label}
    </button>
  );

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center" dir="rtl">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-xl w-[92%] max-w-[440px] p-6 space-y-5 animate-[fadeIn_0.2s_ease-out]">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-[#2d4658]" style={HEEBO}>החשבון שלי</h2>
          <button type="button" onClick={onClose} className="p-1 rounded-lg hover:bg-[#f6f4f0]" aria-label="סגירה">
            <X size={20} className="text-[#2d4658]" />
          </button>
        </div>

        {!profile && !error && <p className="text-sm text-[rgba(45,70,88,0.6)]" style={HEEBO}>טוען…</p>}

        {profile && (
          <>
            <div className="space-y-1.5">
              <label htmlFor="acc-name" className="block text-sm font-medium text-[#2d4658]" style={HEEBO}>שם</label>
              <input
                id="acc-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full h-[46px] px-3 rounded-xl border border-[#e0ddd8] text-base text-[#2d4658] text-right
                           focus:outline-none focus:border-[#03ffe6]"
                style={HEEBO}
              />
            </div>

            {profile.email && (
              <div className="space-y-1">
                <p className="text-sm font-medium text-[#2d4658]" style={HEEBO}>אימייל</p>
                <p className="text-sm text-[rgba(45,70,88,0.7)] break-all" dir="ltr" style={{ ...HEEBO, textAlign: 'right' }}>{profile.email}</p>
              </div>
            )}

            <div className="space-y-2">
              <p className="text-sm font-medium text-[#2d4658]" style={HEEBO}>איך לפנות אליך?</p>
              <div className="flex gap-3">
                {choice('male', 'אתה')}
                {choice('female', 'את')}
              </div>
              <p className="text-xs text-[rgba(45,70,88,0.55)]" style={HEEBO}>כך המאמן והכרטיסים יפנו אליך.</p>
            </div>
          </>
        )}

        {error && <p className="text-sm text-[#c93c3c]" style={HEEBO}>משהו השתבש. נסו שוב.</p>}

        <div className="flex gap-3 pt-1">
          <button type="button" onClick={onClose}
            className="h-[48px] px-5 rounded-xl border border-[#e0ddd8] text-[#2d4658] text-sm hover:bg-[#f6f4f0]" style={HEEBO}>
            ביטול
          </button>
          <button type="button" disabled={!changed || saving} onClick={save}
            className="flex-1 h-[48px] rounded-xl bg-[#9747ff] text-white text-base hover:bg-[#8035e6] disabled:opacity-40" style={HEEBO}>
            {saving ? '...' : 'שמירה'}
          </button>
        </div>
      </div>
    </div>
  );
}
