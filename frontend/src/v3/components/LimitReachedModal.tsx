import { Sparkles, Ticket } from 'lucide-react';

// The window when the messages run out (Nov 8), in the style of "המנוי שלי". The old one (dark and gold, kept for
// V2) spoke in the masculine and promised "יומן אישי ותובנות עומק"; this one says the conversation is kept and
// offers the two ways on: full access (one payment) or a coupon — both open the subscription screen.

interface Props {
  open: boolean;
  gender?: string | null;
  onFullAccess: () => void;
  onCoupon: () => void;
  onClose: () => void;
}

const HEEBO = { fontFamily: "'Heebo', sans-serif" };
const INK = '#2d4658';
const MUTED = 'rgba(45,70,88,0.65)';
const PURPLE = '#9747ff';

export function LimitReachedModal({ open, gender, onFullAccess, onCoupon, onClose }: Props) {
  if (!open) return null;
  const g = (m: string, f: string) => (gender === 'female' ? f : m);
  return (
    <div className="fixed inset-0 z-[70] bg-[#1f2f3d]/60 backdrop-blur-sm flex items-end sm:items-center justify-center p-4"
      dir="rtl" style={HEEBO} onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="limit-title">
      <div className="w-full max-w-sm rounded-3xl bg-white shadow-2xl overflow-hidden animate-[fadeIn_0.2s_ease-out]"
        onClick={(e) => e.stopPropagation()}>
        <div className="h-1.5" style={{ background: `linear-gradient(90deg, ${PURPLE}, #03ffe6)` }} />
        <div className="px-6 pt-6 pb-5 text-center">
          <div className="mx-auto w-14 h-14 rounded-2xl flex items-center justify-center" style={{ background: 'rgba(151,71,255,0.10)' }}>
            <Sparkles size={26} style={{ color: PURPLE }} />
          </div>
          <h2 id="limit-title" className="mt-4 text-xl font-semibold" style={{ color: INK }}>ההודעות שלך נגמרו</h2>
          <p className="mt-2 text-sm leading-relaxed" style={{ color: MUTED }}>
            השיחה שמורה בדיוק איפה שעצרת. אפשר להמשיך מיד — עם גישה מלאה, בתשלום חד פעמי ובלי מנוי, או עם קוד קופון.
          </p>

          <button type="button" onClick={onFullAccess}
            className="mt-5 w-full h-[52px] rounded-2xl text-white text-base font-semibold transition-transform active:scale-[0.98] shadow-[0_10px_20px_-8px_rgba(151,71,255,0.6)]"
            style={{ background: `linear-gradient(135deg, ${PURPLE} 0%, #6b2fd6 100%)` }}>
            {g('להמשך — פתח גישה מלאה', 'להמשך — פתחי גישה מלאה')}
          </button>
          <button type="button" onClick={onCoupon}
            className="mt-2.5 w-full h-[48px] rounded-2xl border border-[#e0ddd8] text-sm font-medium flex items-center justify-center gap-2 hover:bg-[#f6f4f0]"
            style={{ color: INK }}>
            <Ticket size={16} style={{ color: PURPLE }} /> יש לי קוד קופון
          </button>
          <button type="button" onClick={onClose} className="mt-3 text-xs underline-offset-2 hover:underline" style={{ color: MUTED }}>
            אחר כך
          </button>
        </div>
      </div>
    </div>
  );
}
