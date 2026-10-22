import { useEffect, useMemo, useState } from 'react';
import { CardShell } from '../shared/CardShell';

// בקשה לאימון — the booklet's complex coaching request (p.37-38): choose a floor, then
// "אני מבקש להתאמן על הקושי להתמודד עם [...], שכאשר מופיע [הישן] [...], אפעל מתוך המקור [...]
// ומתוך הטבע [...], ומתוך [החדש] [...], כדי שהתוצאה שאשיג תהיה [תוצאה מדידה]".
type Floor = 'pattern' | 'paradigm' | 'stance';

// Stance first and default: "היית בקומת העמדה, היא קומת השינוי" (booklet p.36)
const FLOORS: { id: Floor; label: string; that: string; oldAdj: string; newAdj: string; feminine: boolean }[] = [
  { id: 'stance', label: 'העמדה', that: 'שהיא', oldAdj: 'הישנה', newAdj: 'החדשה', feminine: true },
  { id: 'paradigm', label: 'הפרדיגמה', that: 'שהיא', oldAdj: 'הישנה', newAdj: 'החדשה', feminine: true },
  { id: 'pattern', label: 'הדפוס', that: 'שהוא', oldAdj: 'הישן', newAdj: 'החדש', feminine: false },
];

interface CommitmentCardData {
  forces_source?: string[];
  forces_nature?: string[];
  old?: Partial<Record<Floor, string>>;
  new?: Partial<Record<Floor, string>>;
}

interface CommitmentCardProps {
  data?: CommitmentCardData;
  onSubmit: (toolType: string, data: {
    floor: Floor; situation: string; old: string; source: string[]; nature: string[]; new: string; result: string;
  }) => void;
  isSubmitting: boolean;
}

const FIELD = `w-full px-3 py-2.5 rounded-xl border border-[#e0ddd8] text-sm text-[#2d4658] text-right
  placeholder:text-[rgba(45,70,88,0.35)] resize-none focus:outline-none focus:border-[#03ffe6] transition-colors`;
const LABEL = 'block text-sm font-medium text-[#2d4658] text-right mb-1';
const HEEBO = { fontFamily: "'Heebo', sans-serif" };

function Chips({ options, selected, onToggle }: { options: string[]; selected: string[]; onToggle: (s: string) => void }) {
  return (
    <div className="flex flex-wrap gap-2 justify-start" dir="rtl">
      {options.map((o) => (
        <button
          key={o}
          type="button"
          onClick={() => onToggle(o)}
          className={`px-3 h-[32px] rounded-xl border text-sm transition-colors ${selected.includes(o)
            ? 'bg-[#9747ff] border-[#9747ff] text-white'
            : 'bg-white border-[#e0ddd8] text-[#2d4658] hover:border-[#9747ff]'}`}
          style={HEEBO}
        >
          {o}
        </button>
      ))}
    </div>
  );
}

export function CommitmentCard({ data, onSubmit, isSubmitting }: CommitmentCardProps) {
  const [floor, setFloor] = useState<Floor>('stance');
  const [situation, setSituation] = useState('');
  const [oldText, setOldText] = useState(data?.old?.stance ?? '');
  const [newText, setNewText] = useState(data?.new?.stance ?? '');
  const [source, setSource] = useState<string[]>([]);
  const [nature, setNature] = useState<string[]>([]);
  const [result, setResult] = useState('');

  // Switching the floor refills old/new with the client's own words for that floor (still editable)
  useEffect(() => {
    setOldText(data?.old?.[floor] ?? '');
    setNewText(data?.new?.[floor] ?? '');
  }, [floor, data]);

  const f = FLOORS.find((x) => x.id === floor)!;
  const noun = f.label.slice(1);  // "הדפוס" → "דפוס"
  const toggle = (list: string[], set: (v: string[]) => void) => (s: string) =>
    set(list.includes(s) ? list.filter((x) => x !== s) : [...list, s]);

  const sourceOptions = data?.forces_source ?? [];
  const natureOptions = data?.forces_nature ?? [];
  const canSubmit = situation.trim().length > 2 && oldText.trim().length > 0 && newText.trim().length > 0
    && result.trim().length > 2
    && (sourceOptions.length === 0 || source.length > 0)
    && (natureOptions.length === 0 || nature.length > 0);

  const preview = useMemo(() => {
    const parts = [`אני מבקש/ת להתאמן על הקושי להתמודד עם ${situation.trim() || '…'}`];
    parts.push(`שכאשר מופיע${f.feminine ? 'ה' : ''} ה${noun} ${f.oldAdj} שלי, ${f.that} ${oldText.trim() || '…'}`);
    if (source.length) parts.push(`אפעל מתוך המקור שלי, שהוא ${source.join(', ')}`);
    if (nature.length) parts.push(`ומתוך הטבע שלי, שהוא ${nature.join(', ')}`);
    parts.push(`ומתוך ה${noun} ${f.newAdj} שבחרתי, ${f.that} ${newText.trim() || '…'}`);
    parts.push(`כדי שהתוצאה שאשיג תהיה: ${result.trim() || '…'}`);
    return parts.join(', ') + '.';
  }, [situation, oldText, newText, source, nature, result, f, noun]);

  return (
    <CardShell
      titleHe="הבקשה שלך לאימון"
      instructionHe="בקשה לאימון היא הדרך שלך לקחת אחריות על השינוי — לבקש אותו מעצמך, מתוך הכוחות שלך. היא שלך, ואתה זה שמממש אותה."
    >
      <div className="space-y-5">
        {/* Floor */}
        <div>
          <p className={LABEL} style={HEEBO}>על איזו קומה תרצה להתאמן? <span className="font-normal text-[rgba(45,70,88,0.6)]">(העמדה היא קומת השינוי)</span></p>
          <div className="flex gap-2 justify-start" dir="rtl">
            {FLOORS.map((x) => (
              <button
                key={x.id}
                type="button"
                onClick={() => setFloor(x.id)}
                className={`flex-1 h-[40px] rounded-xl border text-sm transition-colors ${floor === x.id
                  ? 'bg-[#2d4658] border-[#2d4658] text-white'
                  : 'bg-white border-[#e0ddd8] text-[#2d4658] hover:border-[#2d4658]'}`}
                style={HEEBO}
              >
                {x.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className={LABEL} style={HEEBO}>אני מבקש/ת להתאמן על הקושי להתמודד עם…</label>
          <textarea value={situation} onChange={(e) => setSituation(e.target.value)} rows={2} className={FIELD} style={HEEBO}
            placeholder="איזו סיטואציה קשה לך — למשל: ויכוחים על כסף בבית" />
        </div>

        <div>
          <label className={LABEL} style={HEEBO}>שכאשר מופיע{f.feminine ? 'ה' : ''} ה{noun} {f.oldAdj} שלי, {f.that}…</label>
          <textarea value={oldText} onChange={(e) => setOldText(e.target.value)} rows={2} className={FIELD} style={HEEBO} />
        </div>

        {sourceOptions.length > 0 && (
          <div>
            <p className={LABEL} style={HEEBO}>אפעל מתוך המקור שלי, שהוא…</p>
            <Chips options={sourceOptions} selected={source} onToggle={toggle(source, setSource)} />
          </div>
        )}

        {natureOptions.length > 0 && (
          <div>
            <p className={LABEL} style={HEEBO}>ומתוך הטבע שלי, שהוא…</p>
            <Chips options={natureOptions} selected={nature} onToggle={toggle(nature, setNature)} />
          </div>
        )}

        <div>
          <label className={LABEL} style={HEEBO}>ומתוך ה{noun} {f.newAdj} שבחרתי, {f.that}…</label>
          <textarea value={newText} onChange={(e) => setNewText(e.target.value)} rows={2} className={FIELD} style={HEEBO} />
        </div>

        <div>
          <label className={LABEL} style={HEEBO}>כדי שהתוצאה שאשיג תהיה…</label>
          <p className="text-xs text-[rgba(45,70,88,0.55)] text-right mb-1" style={HEEBO}>תוצאה מדידה <strong>שתלויה בך</strong> — מה אתה תעשה או איך תהיה, לא איך אחרים יגיבו.</p>
          <textarea value={result} onChange={(e) => setResult(e.target.value)} rows={2} className={FIELD} style={HEEBO}
            placeholder="למשל: בשבועיים הקרובים אסיים שני ויכוחים בלי לצעוק" />
        </div>

        {/* Live preview of the whole request */}
        <div className="bg-[#f6f4f0] rounded-lg p-4 text-right">
          <p className="text-xs font-semibold text-[rgba(45,70,88,0.6)] mb-1" style={HEEBO}>הבקשה שלך</p>
          <p className="text-sm text-[#2d4658] leading-relaxed" style={HEEBO}>{preview}</p>
        </div>

        <div className="flex justify-center pt-1">
          <button
            type="button"
            disabled={!canSubmit || isSubmitting}
            onClick={() => onSubmit('commitment_card', {
              floor, situation: situation.trim(), old: oldText.trim(), source, nature, new: newText.trim(), result: result.trim(),
            })}
            className="w-full max-w-[320px] h-[54px] rounded-xl bg-[#9747ff] text-white text-base font-semibold
                       hover:bg-[#8035e6] transition-all duration-200 disabled:opacity-50
                       drop-shadow-[0px_8px_2.9px_rgba(0,0,0,0.12)] active:scale-[0.97]"
            style={HEEBO}
          >
            {isSubmitting ? '...' : 'זו הבקשה שלי'}
          </button>
        </div>
      </div>
    </CardShell>
  );
}
