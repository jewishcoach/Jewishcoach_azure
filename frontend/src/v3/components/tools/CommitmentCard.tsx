import { useState } from 'react';
import { CardShell } from '../shared/CardShell';

interface CommitmentCardProps {
  onSubmit: (toolType: string, data: {
    commitment: string;
    when: string;
    where_who: string;
  }) => void;
  isSubmitting: boolean;
}

export function CommitmentCard({ onSubmit, isSubmitting }: CommitmentCardProps) {
  const [commitment, setCommitment] = useState('');
  const [when, setWhen] = useState('');
  const [whereWho, setWhereWho] = useState('');
  const [signed, setSigned] = useState(false);

  const canSubmit = commitment.trim().length > 0 && when.trim().length > 0 && whereWho.trim().length > 0;

  const handleSign = () => {
    setSigned(true);
    onSubmit('commitment_card', {
      commitment: commitment.trim(),
      when: when.trim(),
      where_who: whereWho.trim(),
    });
  };

  return (
    <CardShell
      titleHe="המחויבות שלך"
      instructionHe="הצעד הראשון להפוך את הבחירה למציאות. מחויבות קונקרטית — מה, מתי, ואיפה."
    >
      <div className="space-y-5">
        {/* Commitment field */}
        <div>
          <label
            className="block text-sm font-medium text-[#2d4658] text-right mb-1"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            אני מתחייב ש:
          </label>
          <textarea
            value={commitment}
            onChange={(e) => setCommitment(e.target.value)}
            placeholder="מה הצעד הקונקרטי שאני לוקח על עצמי?"
            rows={2}
            disabled={signed}
            className="w-full px-3 py-2.5 rounded-xl border border-[#e0ddd8] text-sm text-[#2d4658] text-right
                       placeholder:text-[rgba(45,70,88,0.35)] resize-none
                       focus:outline-none focus:border-[#03ffe6] transition-colors
                       disabled:bg-[#f6f4f0] disabled:text-[rgba(45,70,88,0.7)]"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          />
        </div>

        {/* When */}
        <div>
          <label
            className="block text-sm font-medium text-[#2d4658] text-right mb-1"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            מתי:
          </label>
          <input
            type="text"
            value={when}
            onChange={(e) => setWhen(e.target.value)}
            placeholder="למשל: מחר בבוקר, בפגישה הבאה..."
            disabled={signed}
            className="w-full h-[44px] px-3 rounded-xl border border-[#e0ddd8] text-sm text-[#2d4658] text-right
                       placeholder:text-[rgba(45,70,88,0.35)]
                       focus:outline-none focus:border-[#03ffe6] transition-colors
                       disabled:bg-[#f6f4f0] disabled:text-[rgba(45,70,88,0.7)]"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          />
        </div>

        {/* Where / with whom */}
        <div>
          <label
            className="block text-sm font-medium text-[#2d4658] text-right mb-1"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            איפה / מול מי:
          </label>
          <input
            type="text"
            value={whereWho}
            onChange={(e) => setWhereWho(e.target.value)}
            placeholder="למשל: בבית, מול בן/בת הזוג..."
            disabled={signed}
            className="w-full h-[44px] px-3 rounded-xl border border-[#e0ddd8] text-sm text-[#2d4658] text-right
                       placeholder:text-[rgba(45,70,88,0.35)]
                       focus:outline-none focus:border-[#03ffe6] transition-colors
                       disabled:bg-[#f6f4f0] disabled:text-[rgba(45,70,88,0.7)]"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          />
        </div>

        {/* Sign button */}
        <div className="flex justify-center pt-3">
          {signed ? (
            <div className="flex flex-col items-center gap-2 animate-[fadeIn_0.5s_ease-out]">
              <div className="w-14 h-14 rounded-full bg-[rgba(3,255,230,0.2)] flex items-center justify-center">
                <span className="text-[#03ffe6] text-2xl">&#10003;</span>
              </div>
              <p
                className="text-sm font-medium text-[#009081]"
                style={{ fontFamily: "'Heebo', sans-serif" }}
              >
                המחויבות נחתמה
              </p>
            </div>
          ) : (
            <button
              type="button"
              disabled={!canSubmit || isSubmitting}
              onClick={handleSign}
              className="w-full max-w-[320px] h-[58px] rounded-xl bg-[#9747ff] text-white text-base font-semibold
                         hover:bg-[#8035e6] transition-all duration-200 disabled:opacity-50
                         drop-shadow-[0px_8px_2.9px_rgba(0,0,0,0.12)]
                         active:scale-[0.97]"
              style={{ fontFamily: "'Heebo', sans-serif" }}
            >
              {isSubmitting ? (
                <span className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
              ) : (
                'חותם על המחויבות שלי'
              )}
            </button>
          )}
        </div>
      </div>
    </CardShell>
  );
}
