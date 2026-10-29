import { useMemo, useState } from 'react';
import { CardShell } from '../shared/CardShell';
import { useG } from '../shared/gender';
import { AutoTextarea } from '../shared/AutoTextarea';

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
  selected_source?: string[];  // the forces he chose for this event at S12
  selected_nature?: string[];
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

// Same rules as the backend composer (bsd_v2/coaching_request.py): a first-person sentence ("אני מאמין ש…") reads
// inside the template only as a quote; a "כש…" situation becomes "הרגעים ש…"
function difficultyPhrase(text: string): string {
  const t = text.trim().replace(/\.+$/, '');
  if (!t) return 'הקושי להתמודד עם …';
  const first = t.split(/\s+/)[0];
  if (t.startsWith('כש')) return `הקושי להתמודד עם הרגעים ש${t.replace(/,\s*(?:אז\s+|ואז\s+)?(?:אני|אז)\s.*$/, '').slice(2)}`;
  if (first.startsWith('ל') && first.length >= 4 && !['לחץ', 'לחצים', 'לילה', 'לילות', 'לימודים'].includes(first)) return `הקושי שלי ${t}`;
  if (first === 'לא') return `הקושי שלי ש${t}`;
  return `הקושי להתמודד עם ${t}`;
}

function clause(text: string): string {
  const t = text.trim().replace(/^(כן|נכון|אכן)[,.]?\s+/, '').replace(/\.+$/, '');
  if (!t) return '…';
  return t.startsWith('העמדה שלי') || t.split(/\s+/).slice(0, 4).includes('אני') ? `"${t}"` : t;
}

// Same as the backend composer: "כנות ונאמנות" — the last one joined with ו
function heList(items: string[]): string {
  return items.length <= 1 ? items.join('') : `${items.slice(0, -1).join(', ')} ו${items[items.length - 1]}`;
}

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
  const g = useG();
  const opener = g('אני מבקש', 'אני מבקשת');
  // Always the stance floor — "קומת העמדה היא קומת השינוי" (booklet p.36); the backend enforces it too
  const floor: Floor = 'stance';
  const [situation, setSituation] = useState('');
  const [oldText, setOldText] = useState(data?.old?.stance ?? '');
  const [newText, setNewText] = useState(data?.new?.stance ?? '');
  // The forces he chose for this event at S12 (spec "כמ"ז בתוך אימון") are the ones the coach reflected — preselected
  // so the request carries the same forces (still editable); older sessions: the first of each list
  const [source, setSource] = useState<string[]>(data?.selected_source?.length ? data.selected_source
    : data?.forces_source?.length ? [data.forces_source[0]] : []);
  const [nature, setNature] = useState<string[]>(data?.selected_nature?.length ? data.selected_nature
    : data?.forces_nature?.length ? [data.forces_nature[0]] : []);
  const [result, setResult] = useState('');

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
    const parts = [`${opener} להתאמן על ${difficultyPhrase(situation)}`];
    parts.push(`שכאשר מופיע${f.feminine ? 'ה' : ''} ה${noun} ${f.oldAdj} שלי, ${f.that} ${clause(oldText)}`);
    if (source.length) parts.push(`אפעל מתוך המקור שלי, שהוא ${heList(source)}`);
    if (nature.length) parts.push(`ומתוך הטבע שלי, שהוא ${heList(nature)}`);
    parts.push(`ומתוך ה${noun} ${f.newAdj} שבחרתי, ${f.that} ${clause(newText)}`);
    parts.push(`כדי שהתוצאה שאשיג תהיה: ${result.trim() || '…'}`);
    return parts.join(', ') + '.';
  }, [situation, oldText, newText, source, nature, result, f, noun, opener]);

  return (
    <CardShell
      titleHe="הבקשה שלך לאימון"
      instructionHe={g('בקשה לאימון היא הדרך שלך לקחת אחריות על השינוי — לבקש אותו מעצמך, מתוך הכוחות שלך. היא שלך, ואתה זה שמממש אותה.', 'בקשה לאימון היא הדרך שלך לקחת אחריות על השינוי — לבקש אותו מעצמך, מתוך הכוחות שלך. היא שלך, ואת זו שמממשת אותה.')}
    >
      <div className="space-y-5">
        <div>
          <label className={LABEL} style={HEEBO}>{opener} להתאמן על הקושי להתמודד עם…</label>
          <AutoTextarea value={situation} onChange={(e) => setSituation(e.target.value)} rows={2} className={FIELD} style={HEEBO}
            placeholder="הסיטואציה עצמה — למשל: ויכוחים על כסף בבית, שיחות כנות מול הבוס" />
        </div>

        <div>
          <label className={LABEL} style={HEEBO}>שכאשר מופיע{f.feminine ? 'ה' : ''} ה{noun} {f.oldAdj} שלי, {f.that}…</label>
          <AutoTextarea value={oldText} onChange={(e) => setOldText(e.target.value)} rows={2} className={FIELD} style={HEEBO} />
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
          <AutoTextarea value={newText} onChange={(e) => setNewText(e.target.value)} rows={2} className={FIELD} style={HEEBO} />
        </div>

        <div>
          <label className={LABEL} style={HEEBO}>כדי שהתוצאה שאשיג תהיה…</label>
          <p className="text-xs text-[rgba(45,70,88,0.55)] text-right mb-1" style={HEEBO}>תוצאה מדידה <strong>שתלויה בך</strong> — {g('מה אתה תעשה או איך תהיה', 'מה את תעשי או איך תהיי')}, לא איך אחרים יגיבו.</p>
          <AutoTextarea value={result} onChange={(e) => setResult(e.target.value)} rows={2} className={FIELD} style={HEEBO}
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
