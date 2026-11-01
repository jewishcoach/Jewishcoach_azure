import { useEffect, useMemo, useRef, useState } from 'react';
import { CardShell } from '../shared/CardShell';
import { useG } from '../shared/gender';
import { SubmitButton } from '../shared/SubmitButton';

// הבזקי מקור וטבע (S12, spec "כמ"ז בתוך אימון 3+3"): 3 completion sentences for the source (blue) and 3 for the
// nature (red), based on booklet p.25. The example chips are hidden by default — the client first answers in his
// own words; a chip only inserts text into the field for him to edit, and the ids used are reported.
interface DiscoveryQuestion {
  id: string;
  side: 'source' | 'nature';
  title: string;
  prompt: string;
  chips: { id: string; text: string }[];
}

interface KamazDiscoveryCardProps {
  data?: { questions?: DiscoveryQuestion[] };
  onSubmit: (toolType: string, data: { answers: { id: string; side: string; text: string; chips_used: string[] }[] }) => void;
  isSubmitting: boolean;
}

const HEEBO = { fontFamily: "'Heebo', sans-serif" };
const SIDES = {
  source: { title: 'המקור שלי', accent: '#2f5fd0', soft: 'rgba(47,95,208,0.07)', border: 'rgba(47,95,208,0.35)' },
  nature: { title: 'הטבע שלי', accent: '#c93c3c', soft: 'rgba(201,60,60,0.06)', border: 'rgba(201,60,60,0.35)' },
} as const;
const ORDER = ['source', 'nature'] as const;
const MIN_CHARS = 2;

export function KamazDiscoveryCard({ data, onSubmit, isSubmitting }: KamazDiscoveryCardProps) {
  const g = useG();
  const questions = useMemo(() => data?.questions ?? [], [data?.questions]);
  const [screen, setScreen] = useState<'source' | 'nature'>('source');
  const [texts, setTexts] = useState<Record<string, string>>({});
  const [chipsUsed, setChipsUsed] = useState<Record<string, string[]>>({});
  const [openChips, setOpenChips] = useState<string | null>(null);

  const onScreen = questions.filter((q) => q.side === screen);
  const answered = (q: DiscoveryQuestion) => (texts[q.id] || '').trim().length >= MIN_CHARS;
  const countOf = (s: 'source' | 'nature') => {
    const qs = questions.filter((q) => q.side === s);
    return { done: qs.filter(answered).length, all: qs.length };
  };
  const firstOpen = onScreen.find((q) => !answered(q));
  const openCount = onScreen.filter((q) => !answered(q)).length;
  const missing = !firstOpen ? null : openCount === 1 ? 'חסרה תשובה למשפט אחד' : `חסרות תשובות ל-${openCount} משפטים`;
  const side = SIDES[screen];

  // The switch to the red screen kept the scroll at the bottom: red boxes appeared with no heading, and the blue
  // answers seemed gone (user, Nov 1). Bring the top of the card — the two-part bar and the explanation — into view.
  const topRef = useRef<HTMLDivElement>(null);
  const firstRender = useRef(true);
  useEffect(() => {
    if (firstRender.current) { firstRender.current = false; return; }
    topRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [screen]);
  const goTo = (s: 'source' | 'nature') => { setScreen(s); setOpenChips(null); };

  const applyChip = (q: DiscoveryQuestion, chip: { id: string; text: string }) => {
    setTexts((prev) => {
      const cur = (prev[q.id] || '').trim();
      return { ...prev, [q.id]: cur ? `${cur}, ${chip.text}` : chip.text };
    });
    setChipsUsed((prev) => ({ ...prev, [q.id]: Array.from(new Set([...(prev[q.id] || []), chip.id])) }));
  };

  const submit = () => {
    if (isSubmitting || !questions.every(answered)) return;
    onSubmit('kamaz_discovery', {
      answers: questions.map((q) => ({ id: q.id, side: q.side, text: (texts[q.id] || '').trim(), chips_used: chipsUsed[q.id] || [] })),
    });
  };

  return (
    <CardShell titleHe="הבזקי מקור וטבע" instructionHe={g('השלם כל משפט במילים שלך — קצר, מה שעולה ראשון.', 'השלימי כל משפט במילים שלך — קצר, מה שעולה ראשון.')}>
      <div className="space-y-5 scroll-mt-24" dir="rtl" ref={topRef}>
        {/* the two parts, always visible: where you are, what is done, what comes next */}
        <div className="grid grid-cols-2 gap-2">
          {ORDER.map((s, i) => {
            const st = SIDES[s];
            const current = s === screen;
            const { done, all } = countOf(s);
            const finished = all > 0 && done === all && !current;
            return (
              <button
                key={s}
                type="button"
                onClick={() => !current && (s === 'source' || countOf('source').done === countOf('source').all) && goTo(s)}
                className="rounded-xl px-3 py-2 text-right transition-all"
                style={{ ...HEEBO, border: `1.5px solid ${current ? st.accent : st.border}`,
                         background: current ? st.accent : finished ? st.soft : '#fff', color: current ? '#fff' : st.accent }}
              >
                <span className="block text-[11px] opacity-80">חלק {i + 1}{finished ? ' ✓' : ''}</span>
                <span className="block text-sm font-semibold">{st.title}</span>
                <span className="block text-[11px] opacity-80">{done}/{all} תשובות</span>
              </button>
            );
          })}
        </div>

        <p className="text-sm text-[#2d4658] leading-relaxed rounded-lg px-3 py-2" style={{ ...HEEBO, background: side.soft }}>
          {screen === 'source'
            ? <>שני חלקים קצרים: קודם <strong style={{ color: SIDES.source.accent }}>המקור</strong> שלך — האור, הערכים והמתנות שלך. אחר כך <strong style={{ color: SIDES.nature.accent }}>הטבע</strong> שלך — הצרכים והנטיות הטבעיות.</>
            : <>✓ חלק המקור נשמר ({countOf('source').done} תשובות) — אפשר לחזור אליו בלחיצה למעלה. עכשיו החלק השני: <strong style={{ color: SIDES.nature.accent }}>הטבע</strong> שלך — הצרכים והנטיות הטבעיות שלך.</>}
        </p>

        {onScreen.map((q) => (
          <div key={q.id} className="rounded-xl p-3 space-y-2" style={{ background: side.soft, border: `1px solid ${side.border}` }}>
            <p className="text-[11px] font-semibold text-[rgba(45,70,88,0.55)]" style={HEEBO}>{q.title}</p>
            <label htmlFor={`kq-${q.id}`} className="block text-sm text-[#2d4658] leading-relaxed" style={HEEBO}>
              {q.prompt}
            </label>
            <textarea
              id={`kq-${q.id}`}
              value={texts[q.id] || ''}
              onChange={(e) => setTexts((prev) => ({ ...prev, [q.id]: e.target.value }))}
              onFocus={() => setOpenChips((cur) => (cur === q.id ? cur : null))}
              rows={2}
              className="w-full px-3 py-2 rounded-lg border border-[#e0ddd8] bg-white text-sm text-[#2d4658] text-right
                         resize-none focus:outline-none focus:border-[#03ffe6] transition-colors"
              style={HEEBO}
            />
            {openChips === q.id ? (
              <div className="flex flex-wrap gap-1.5">
                {q.chips.map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => applyChip(q, c)}
                    className="px-2.5 py-1 rounded-full text-xs bg-white border border-[#e0ddd8] text-[#2d4658]
                               hover:border-[#9747ff] active:scale-95 transition-all"
                    style={HEEBO}
                  >
                    {c.text}
                  </button>
                ))}
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setOpenChips(q.id)}
                className="text-xs text-[rgba(45,70,88,0.55)] hover:text-[#2d4658] underline-offset-2 hover:underline"
                style={HEEBO}
              >
                💡 נתקעת? {g('לחץ', 'לחצי')} להצגת דוגמאות
              </button>
            )}
          </div>
        ))}

        <div className="flex justify-center gap-3 pt-1">
          {screen === 'nature' && (
            <button
              type="button"
              onClick={() => goTo('source')}
              className="h-[53px] px-5 whitespace-nowrap shrink-0 rounded-xl border border-[#e0ddd8] text-[#2d4658] text-sm hover:bg-[#f6f4f0]"
              style={HEEBO}
            >
              חזרה למקור
            </button>
          )}
          <SubmitButton
            label={screen === 'source' ? 'המשך לחלק 2: הטבע' : 'סיימתי'}
            missing={missing}
            target={() => (firstOpen ? document.getElementById(`kq-${firstOpen.id}`) : null)}
            isSubmitting={isSubmitting}
            onSubmit={() => (screen === 'source' ? goTo('nature') : submit())}
            className="w-full max-w-[300px] h-[53px] rounded-xl text-white text-base bg-[#9747ff] hover:bg-[#8035e6]
                       transition-all drop-shadow-[0px_8px_2.9px_rgba(0,0,0,0.12)]"
            style={HEEBO}
          />
        </div>
      </div>
    </CardShell>
  );
}
