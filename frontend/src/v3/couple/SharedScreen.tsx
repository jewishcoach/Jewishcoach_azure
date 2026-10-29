import { ArrowDown, Download, RotateCcw, Share2 } from 'lucide-react';
import type { Checkpoint, SharedScreenData, SharedSide } from './coupleApi';
import { FONT, LINE_HEADINGS, LINE_ORDER } from './lines';
import { CoupleScreen, Note, Panel, PrimaryButton, ScreenTitle, SecondaryButton } from './ui';

interface SharedScreenProps {
  checkpoint: Checkpoint;
  data: SharedScreenData;
  onContinue: () => void;
}

// Guiding texts — drafts for the expert (backend/docs/COUPLES_PROCESS_SPEC_HE.md)
const INTRO: Record<Checkpoint, string> = {
  mirror: 'כל אחד מכם עבר את האירוע הזה מבפנים, לבד. כאן מופיע מה שכל אחד בחר לשתף. קראו לאט. אין כאן מי צודק — יש כאן שני עולמות פנימיים.',
  commitment: 'כל אחד מכם בחר עמדה חדשה, ומתוכה — איך ינהג בפעם הבאה. זו ההתחייבות של כל אחד לחלק שלו.',
};
const GEARS_TEXT = 'לכל אחד מכם יש כפתור — משהו שמדליק אצלו את העמדה. ולכל אחד יש דפוס — הדרך שבה הוא מגיב בלי לבחור. '
  + 'כאן רואים איך הדפוס של אחד נוגע בכפתור של השני.';
const MIRROR_END = 'מכאן כל אחד ממשיך לבד, לגלות מאיפה הוא יכול לבחור אחרת.';

const lineOf = (side: SharedSide, id: string) => side.lines.find((l) => l.id === id)?.text;

function GearBox({ label, text }: { label: string; text: string }) {
  return (
    <div className="w-full bg-[#f6f4f0] rounded-xl px-4 py-3 text-right">
      <p className="text-[11px] font-semibold text-[#01897b]" style={FONT}>{label}</p>
      <p className="text-sm text-[#2d4658] leading-relaxed" style={FONT}>{text}</p>
    </div>
  );
}

/** Each one's pattern next to the other's button — their own words in boxes and arrows, no composed sentences */
function Gears({ me, partner }: { me: SharedSide; partner: SharedSide }) {
  const steps = [
    { label: `הדפוס של ${me.name}`, text: lineOf(me, 'pattern') },
    { label: `הכפתור של ${partner.name}`, text: lineOf(partner, 'trigger') },
    { label: `הדפוס של ${partner.name}`, text: lineOf(partner, 'pattern') },
    { label: `הכפתור של ${me.name}`, text: lineOf(me, 'trigger') },
  ];
  if (steps.some((s) => !s.text)) return null;  // a hidden pattern or button — no cycle to draw
  return (
    <Panel className="space-y-3">
      <h3 className="text-lg font-semibold text-[#2d4658] text-right" style={FONT}>גלגלי השיניים</h3>
      <Note>{GEARS_TEXT}</Note>
      <div className="flex flex-col items-center gap-1">
        {steps.map((s, i) => (
          <div key={i} className="w-full flex flex-col items-center gap-1">
            <GearBox label={s.label} text={s.text as string} />
            {i < steps.length - 1 && <ArrowDown size={18} className="text-[#01897b]" />}
          </div>
        ))}
        <div className="flex items-center gap-2 pt-1 text-[#01897b]">
          <RotateCcw size={16} />
          <span className="text-xs" style={FONT}>וחוזר חלילה</span>
        </div>
      </div>
    </Panel>
  );
}

function shareText(checkpoint: Checkpoint, data: SharedScreenData) {
  const side = (s: SharedSide) => [s.name, ...s.lines.map((l) => `${LINE_HEADINGS[checkpoint][l.id] ?? l.id}: ${l.text}`)].join('\n');
  return [`״${data.event_title}״`, side(data.me), side(data.partner)].join('\n\n');
}

export function SharedScreen({ checkpoint, data, onContinue }: SharedScreenProps) {
  const { me, partner } = data;
  const rows = LINE_ORDER[checkpoint].filter((id) => lineOf(me, id) || lineOf(partner, id));

  return (
    <CoupleScreen>
      <ScreenTitle sub={`״${data.event_title}״`}>{checkpoint === 'mirror' ? 'מסך השיתוף' : 'ההתחייבות הזוגית'}</ScreenTitle>
      <Note>{INTRO[checkpoint]}</Note>

      <Panel className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          {[me, partner].map((s, i) => (
            <p key={i} className="text-base font-semibold text-[#2d4658] text-center border-b border-[#e0ddd8] pb-2" style={FONT}>{s.name}</p>
          ))}
        </div>
        {rows.length === 0 && <Note>שניכם בחרתם לא לשתף שורות.</Note>}
        {rows.map((id) => (
          <div key={id} className="space-y-1">
            <p className="text-[11px] font-semibold text-[#01897b] text-right" style={FONT}>{LINE_HEADINGS[checkpoint][id]}</p>
            <div className="grid grid-cols-2 gap-3">
              {[me, partner].map((s, i) => (
                <p key={i} className="text-sm text-[#2d4658] leading-relaxed text-right bg-[#f6f4f0] rounded-lg px-3 py-2" style={FONT}>
                  {lineOf(s, id) || '—'}
                </p>
              ))}
            </div>
          </div>
        ))}
      </Panel>

      {checkpoint === 'mirror' && <Gears me={me} partner={partner} />}

      {checkpoint === 'commitment' && (
        <div className="flex items-center justify-center gap-4">
          {typeof navigator.share === 'function' && (
            <SecondaryButton onClick={() => { navigator.share({ title: 'ההתחייבות הזוגית שלנו', text: shareText(checkpoint, data) }).catch(() => {}); }}>
              <Share2 size={16} className="text-[#03ffe6]" />
              <span>שיתוף</span>
            </SecondaryButton>
          )}
          <SecondaryButton
            onClick={() => {
              const url = URL.createObjectURL(new Blob([shareText(checkpoint, data)], { type: 'text/plain' }));
              const a = document.createElement('a');
              a.href = url;
              a.download = 'couple-commitment.txt';
              a.click();
              URL.revokeObjectURL(url);
            }}
          >
            <Download size={16} className="text-[#03ffe6]" />
            <span>שמירה</span>
          </SecondaryButton>
        </div>
      )}

      {checkpoint === 'mirror' && <Note>{MIRROR_END}</Note>}
      <div className="flex justify-center">
        <PrimaryButton onClick={onContinue}>{checkpoint === 'mirror' ? 'להמשך התהליך שלי' : 'סיום'}</PrimaryButton>
      </div>
    </CoupleScreen>
  );
}
