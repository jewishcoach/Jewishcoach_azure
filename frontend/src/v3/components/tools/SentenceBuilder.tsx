import { useState } from 'react';
import { CardShell } from '../shared/CardShell';

interface SentenceBuilderProps {
  data?: { pattern?: string };
  onSubmit: (toolType: string, data: { paradigm: string; reality_belief: string }) => void;
  isSubmitting: boolean;
}

export function SentenceBuilder({ data, onSubmit, isSubmitting }: SentenceBuilderProps) {
  const [paradigm, setParadigm] = useState('');
  const [realityBelief, setRealityBelief] = useState('');

  const canSubmit = paradigm.trim().length > 0 && realityBelief.trim().length > 0 && !isSubmitting;

  return (
    <CardShell titleHe="מה החוק הפנימי שלך?">
      <div className="space-y-5">
        {/* Context: the pattern identified in S8 */}
        {data?.pattern && (
          <div className="bg-[#f6f4f0] rounded-lg p-4 text-right">
            <p
              className="text-[10px] font-semibold uppercase tracking-wider text-[rgba(45,70,88,0.5)] mb-1"
              style={{ fontFamily: "'Heebo', sans-serif" }}
            >
              הדפוס שזיהית
            </p>
            <p
              className="text-sm text-[#2d4658] leading-relaxed"
              style={{ fontFamily: "'Heebo', sans-serif" }}
            >
              {data.pattern}
            </p>
          </div>
        )}

        {/* Paradigm: "ככה זה אצלי —" */}
        <div className="space-y-2">
          <label
            className="block text-sm font-semibold text-[#2d4658] text-right"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            ככה זה אצלי —
          </label>
          <p
            className="text-xs text-[rgba(45,70,88,0.5)] text-right"
            style={{ fontFamily: "'Assistant', sans-serif" }}
          >
            מהו החוק הפנימי שמנהל אותך? השלם את המשפט
          </p>
          <textarea
            value={paradigm}
            onChange={(e) => setParadigm(e.target.value)}
            placeholder="כי... / כש... / תמיד..."
            rows={3}
            className="w-full px-4 py-3 rounded-xl border border-[#e0ddd8] text-sm text-[#2d4658]
                       placeholder:text-[rgba(45,70,88,0.3)] text-right resize-none
                       focus:outline-none focus:border-[#03ffe6] transition-colors"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          />
        </div>

        {/* Divider */}
        <div className="border-t border-[#e0ddd8]" />

        {/* Reality belief (stance) */}
        <div className="space-y-2">
          <label
            className="block text-sm font-semibold text-[#2d4658] text-right"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            מהי האמונה שמאחורי החוק?
          </label>
          <p
            className="text-xs text-[rgba(45,70,88,0.5)] text-right"
            style={{ fontFamily: "'Assistant', sans-serif" }}
          >
            מהי האמונה על העולם או על עצמך שגורמת לחוק הזה להרגיש אמיתי?
          </p>
          <textarea
            value={realityBelief}
            onChange={(e) => setRealityBelief(e.target.value)}
            placeholder="אני מאמין ש... / העולם הוא..."
            rows={3}
            className="w-full px-4 py-3 rounded-xl border border-[#e0ddd8] text-sm text-[#2d4658]
                       placeholder:text-[rgba(45,70,88,0.3)] text-right resize-none
                       focus:outline-none focus:border-[#03ffe6] transition-colors"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          />
        </div>

        {/* Submit */}
        <div className="flex justify-center pt-2">
          <button
            type="button"
            disabled={!canSubmit}
            onClick={() => onSubmit('sentence_builder', { paradigm: paradigm.trim(), reality_belief: realityBelief.trim() })}
            className="px-8 h-[53px] rounded-xl bg-[#9747ff] text-white text-base
                       hover:bg-[#8035e6] transition-colors disabled:opacity-50
                       drop-shadow-[0px_8px_2.9px_rgba(0,0,0,0.12)]"
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            {isSubmitting ? '...' : 'הבנתי את החוק שלי'}
          </button>
        </div>
      </div>
    </CardShell>
  );
}
