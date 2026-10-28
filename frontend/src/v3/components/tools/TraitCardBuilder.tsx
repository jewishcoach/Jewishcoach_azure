import { useMemo, useState } from 'react';
import { TagInput } from '../shared/TagInput';

// כרטיס כמ"ז (S12, spec "כמ"ז בתוך אימון 3+3"). Screen 1: the client builds 6 source + 6 nature — from the traits
// that came up in his answers (each shown with the words it came from), from the bank, or in his own words
// (booklet p.28: he gathers them). Screen 2: from his 6+6, the 1–2 source forces and one nature force for this event;
// the suggestion (event_rank) is preselected gently and he confirms.
interface BankTrait { group: string; label: string; short: string }
interface Found { trait: string; quote: string }
type Side = 'source' | 'nature';

interface TraitCardBuilderProps {
  data?: {
    bank?: Record<Side, BankTrait[]>;
    suggested?: Record<Side, Found[]>;
    event_rank?: Record<Side, string[]>;
    suggestions?: Record<Side, string[]>;  // the previous card version
  };
  onSubmit: (toolType: string, data: {
    source_forces: string[]; nature_forces: string[]; selected_source: string[]; selected_nature: string[];
  }) => void;
  isSubmitting: boolean;
}

const PER_SIDE = 6;
const MAX_EVENT: Record<Side, number> = { source: 2, nature: 1 };
const HEEBO = { fontFamily: "'Heebo', sans-serif" };
const SIDE_UI: Record<Side, { title: string; subtitle: string; accent: string; soft: string; placeholder: string }> = {
  source: { title: 'כוחות מקור', subtitle: 'האור, הערכים והמתנות שבאת לתת', accent: '#2f5fd0', soft: 'rgba(47,95,208,0.06)', placeholder: 'תכונת מקור במילים שלך...' },
  nature: { title: 'כוחות טבע', subtitle: 'הצרכים והנטיות הטבעיות שלך', accent: '#c93c3c', soft: 'rgba(201,60,60,0.05)', placeholder: 'תכונת טבע במילים שלך...' },
};

export function TraitCardBuilder({ data, onSubmit, isSubmitting }: TraitCardBuilderProps) {
  const [chosen, setChosen] = useState<Record<Side, string[]>>({ source: [], nature: [] });
  const [screen, setScreen] = useState<'build' | 'event'>('build');
  const [eventPick, setEventPick] = useState<Record<Side, string[]>>({ source: [], nature: [] });

  const labelOf = useMemo(() => {
    const m: Record<string, string> = {};
    (['source', 'nature'] as Side[]).forEach((s) => (data?.bank?.[s] || []).forEach((t) => { m[t.short] = t.label; }));
    return (v: string) => m[v] || v;
  }, [data?.bank]);

  const toggle = (side: Side, value: string) => setChosen((prev) => {
    const cur = prev[side];
    if (cur.includes(value)) return { ...prev, [side]: cur.filter((x) => x !== value) };
    if (cur.length >= PER_SIDE) return prev;
    return { ...prev, [side]: [...cur, value] };
  });

  const ready = chosen.source.length === PER_SIDE && chosen.nature.length === PER_SIDE;

  const goToEvent = () => {
    // the gentle default: the event-relevant suggestions that he kept in his card
    const pre = (side: Side) => (data?.event_rank?.[side] || []).filter((t) => chosen[side].includes(t)).slice(0, MAX_EVENT[side]);
    setEventPick({ source: pre('source'), nature: pre('nature') });
    setScreen('event');
  };

  const toggleEvent = (side: Side, value: string) => setEventPick((prev) => {
    const cur = prev[side];
    if (cur.includes(value)) return { ...prev, [side]: cur.filter((x) => x !== value) };
    if (side === 'nature') return { ...prev, nature: [value] };
    return { ...prev, source: cur.length >= MAX_EVENT.source ? [cur[1], value] : [...cur, value] };
  });

  const eventReady = eventPick.source.length >= 1 && eventPick.nature.length === 1;

  const submit = () => {
    if (!ready || !eventReady || isSubmitting) return;
    onSubmit('trait_card_builder', {
      source_forces: chosen.source, nature_forces: chosen.nature,
      selected_source: eventPick.source, selected_nature: eventPick.nature,
    });
  };

  if (screen === 'event') {
    return (
      <div className="space-y-5" dir="rtl">
        <div className="text-center space-y-1">
          <h3 className="text-[26px] text-[#2d4658]" style={{ fontFamily: "'Karantina', cursive", lineHeight: '1.3' }}>
            זהו כרטיס הכמ"ז שלך
          </h3>
          <p className="text-sm text-[rgba(45,70,88,0.7)] leading-relaxed" style={HEEBO}>
            כעת, בחר מתוכו 1–2 כוחות מקור וכוח טבע אחד שהכי נכון לך לגייס היום מול הסיטואציה שעליה אנחנו עובדים:
          </p>
        </div>
        {(['source', 'nature'] as Side[]).map((side) => (
          <div key={side} className="rounded-xl p-3 space-y-2" style={{ background: SIDE_UI[side].soft }}>
            <p className="text-sm font-semibold" style={{ ...HEEBO, color: SIDE_UI[side].accent }}>
              {SIDE_UI[side].title} — {side === 'source' ? 'עד 2' : 'אחד'}
            </p>
            <div className="flex flex-wrap gap-1.5">
              {chosen[side].map((v) => {
                const on = eventPick[side].includes(v);
                return (
                  <button key={v} type="button" onClick={() => toggleEvent(side, v)}
                    className={`px-3 py-1.5 rounded-full text-sm border transition-all active:scale-95 ${on ? 'text-white' : 'bg-white text-[#2d4658] border-[#e0ddd8]'}`}
                    style={{ ...HEEBO, ...(on ? { background: SIDE_UI[side].accent, borderColor: SIDE_UI[side].accent } : {}) }}>
                    {on ? '✓ ' : ''}{labelOf(v)}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
        <div className="flex justify-center gap-3 pt-1">
          <button type="button" onClick={() => setScreen('build')}
            className="h-[53px] px-5 rounded-xl border border-[#e0ddd8] text-[#2d4658] text-sm hover:bg-[#f6f4f0]" style={HEEBO}>
            חזרה לכרטיס
          </button>
          <button type="button" disabled={!eventReady || isSubmitting} onClick={submit}
            className="w-full max-w-[300px] h-[53px] rounded-xl text-white text-base bg-[#9747ff] hover:bg-[#8035e6]
                       transition-all disabled:opacity-40 drop-shadow-[0px_8px_2.9px_rgba(0,0,0,0.12)]" style={HEEBO}>
            {isSubmitting ? '...' : 'זה הכרטיס שלי'}
          </button>
        </div>
      </div>
    );
  }

  const missing = (['source', 'nature'] as Side[])
    .map((s) => [s, PER_SIDE - chosen[s].length] as const).filter(([, n]) => n > 0)
    .map(([s, n]) => `${n} ${s === 'source' ? 'מקור' : 'טבע'}`).join(' ו-');

  return (
    <div className="space-y-5" dir="rtl">
      <div className="text-center">
        <h3 className="text-[28px] text-[#2d4658]" style={{ fontFamily: "'Karantina', cursive", lineHeight: '1.3' }}>
          כרטיס כמ"ז — מקור וטבע
        </h3>
        <p className="text-sm text-[rgba(45,70,88,0.6)] mt-1" style={HEEBO}>
          בחר 6 מכל צד — ממה שעלה בתשובות שלך, מהרשימה, או במילים שלך
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {(['source', 'nature'] as Side[]).map((side) => (
          <ForceColumn
            key={side}
            side={side}
            bank={data?.bank?.[side] || []}
            found={data?.suggested?.[side] || []}
            legacy={data?.bank ? [] : data?.suggestions?.[side] || []}
            chosen={chosen[side]}
            labelOf={labelOf}
            onToggle={(v) => toggle(side, v)}
          />
        ))}
      </div>

      <div className="flex justify-center pt-2">
        <button type="button" disabled={!ready} onClick={goToEvent}
          className="w-full max-w-[300px] h-[53px] rounded-xl text-white text-base bg-[#9747ff] hover:bg-[#8035e6]
                     transition-all disabled:opacity-40 drop-shadow-[0px_8px_2.9px_rgba(0,0,0,0.12)]" style={HEEBO}>
          {ready ? 'המשך' : `צריך עוד ${missing}`}
        </button>
      </div>
    </div>
  );
}

interface ForceColumnProps {
  side: Side;
  bank: BankTrait[];
  found: Found[];
  legacy: string[];
  chosen: string[];
  labelOf: (v: string) => string;
  onToggle: (value: string) => void;
}

function ForceColumn({ side, bank, found, legacy, chosen, labelOf, onToggle }: ForceColumnProps) {
  const ui = SIDE_UI[side];
  const full = chosen.length >= PER_SIDE;
  const foundSet = new Set(found.map((f) => f.trait));
  const groups = bank.reduce<Record<string, BankTrait[]>>((acc, t) => {
    if (!foundSet.has(t.short)) (acc[t.group] ||= []).push(t);
    return acc;
  }, {});
  const custom = chosen.filter((v) => !bank.some((t) => t.short === v) && !legacy.includes(v));

  const chip = (value: string, text: string) => {
    const on = chosen.includes(value);
    return (
      <button key={value} type="button" disabled={!on && full} onClick={() => onToggle(value)}
        className={`px-2.5 py-1 rounded-full text-xs border transition-all active:scale-95 disabled:opacity-35
                    ${on ? 'text-white' : 'bg-white text-[#2d4658] border-[#e0ddd8] hover:border-[#9747ff]'}`}
        style={{ ...HEEBO, ...(on ? { background: ui.accent, borderColor: ui.accent } : {}) }}>
        {on ? '✓ ' : '+ '}{text}
      </button>
    );
  };

  return (
    <div className="rounded-xl overflow-hidden" style={{ background: ui.soft }}>
      <div className="px-4 py-3 flex items-start justify-between">
        <div>
          <h4 className="text-sm font-semibold" style={{ ...HEEBO, color: ui.accent }}>{ui.title}</h4>
          <p className="text-[11px] text-[rgba(45,70,88,0.5)] mt-0.5" style={{ fontFamily: "'Assistant', sans-serif" }}>{ui.subtitle}</p>
        </div>
        <span className={`text-xs font-semibold ${full ? 'text-[#009081]' : 'text-[rgba(45,70,88,0.45)]'}`} style={HEEBO}>
          {chosen.length}/{PER_SIDE}{full ? ' ✓' : ''}
        </span>
      </div>

      <div className="px-3 pb-3 space-y-3">
        {found.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-[11px] font-semibold text-[rgba(45,70,88,0.6)]" style={HEEBO}>✨ עלה מתוך מה שכתבת</p>
            {found.map((f) => (
              <div key={f.trait} className="flex items-start gap-2">
                <span className="shrink-0 whitespace-nowrap">{chip(f.trait, labelOf(f.trait))}</span>
                <span className="text-[11px] text-[rgba(45,70,88,0.55)] leading-snug pt-1" style={{ fontFamily: "'Assistant', sans-serif" }}>
                  מתוך: "{f.quote}"
                </span>
              </div>
            ))}
          </div>
        )}

        {Object.entries(groups).map(([group, traits]) => (
          <div key={group} className="space-y-1">
            <p className="text-[10px] text-[rgba(45,70,88,0.45)]" style={HEEBO}>{group}</p>
            <div className="flex flex-wrap gap-1.5">{traits.map((t) => chip(t.short, t.label))}</div>
          </div>
        ))}

        {legacy.length > 0 && <div className="flex flex-wrap gap-1.5">{legacy.map((t) => chip(t, t))}</div>}

        {custom.length > 0 && <div className="flex flex-wrap gap-1.5">{custom.map((t) => chip(t, t))}</div>}

        {!full && <TagInput tags={[]} onAdd={(v) => { if (!chosen.includes(v)) onToggle(v); }} onRemove={() => {}} placeholder={ui.placeholder} />}
      </div>
    </div>
  );
}
