import { useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import { AutoTextarea } from '../components/shared/AutoTextarea';
import type { Checkpoint, Gender, ShareLine } from './coupleApi';
import { FONT, gFor, LINE_HEADINGS } from './lines';
import { CoupleScreen, ErrorText, Note, Panel, PrimaryButton, ScreenTitle } from './ui';

interface SharePreviewScreenProps {
  checkpoint: Checkpoint;
  lines: ShareLine[];
  partnerName: string | null;
  partnerGender: Gender | null;
  myGender: Gender | null;
  busy: boolean;
  error: string | null;
  onApprove: (lines: { id: string; text: string; visible: boolean }[]) => void;
}

/** Exactly what the partner will see — the member's own words, each line editable or hidden */
export function SharePreviewScreen({ checkpoint, lines, partnerName, partnerGender, myGender, busy, error, onApprove }: SharePreviewScreenProps) {
  const [draft, setDraft] = useState(() => lines.map((l) => ({ ...l, visible: true })));
  const g = gFor(myGender);
  const gp = gFor(partnerGender);
  const who = partnerName || 'בן/בת הזוג';
  const sees = partnerName ? gp('יראה', 'תראה') : 'יראו';
  const update = (id: string, patch: Partial<{ text: string; visible: boolean }>) =>
    setDraft((prev) => prev.map((l) => (l.id === id ? { ...l, ...patch } : l)));
  const anyVisible = draft.some((l) => l.visible && l.text.trim());

  return (
    <CoupleScreen>
      <ScreenTitle sub={`אלה המילים שלך מהשיחה. אפשר לתקן כל שורה או להסתיר אותה. ${who} ${sees} אותן רק כששניכם תאשרו.`}>
        {`מה ${sees} ${who}`}
      </ScreenTitle>

      <div className="space-y-3">
        {draft.map((line) => (
          <Panel key={line.id} className={line.visible ? '' : 'opacity-50'}>
            <div className="flex items-center justify-between gap-3 mb-2">
              <p className="text-[11px] font-semibold uppercase text-[#01897b]" style={FONT}>
                {LINE_HEADINGS[checkpoint][line.id] ?? line.id}
              </p>
              <button
                type="button"
                onClick={() => update(line.id, { visible: !line.visible })}
                className="flex items-center gap-1 text-xs text-[#2d4658] hover:text-[#01897b]"
                style={FONT}
              >
                {line.visible ? <EyeOff size={14} /> : <Eye size={14} />}
                <span>{line.visible ? 'להסתיר' : 'להציג'}</span>
              </button>
            </div>
            {line.visible ? (
              <AutoTextarea
                dir="auto"
                rows={1}
                value={line.text}
                maxLength={checkpoint === 'mirror' ? 300 : 600}
                onChange={(e) => update(line.id, { text: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-[#e0ddd8] text-sm text-[#2d4658] text-right resize-none
                           focus:outline-none focus:border-[#03ffe6] transition-colors"
                style={FONT}
              />
            ) : (
              <Note>{`השורה הזו לא תוצג ל${who}.`}</Note>
            )}
          </Panel>
        ))}
      </div>

      {!anyVisible && <Note>{`אפשר גם לא לשתף אף שורה — ${who} ${sees} שבחרת לא לשתף.`}</Note>}
      <ErrorText>{error}</ErrorText>

      <div className="flex justify-center">
        <PrimaryButton disabled={busy} onClick={() => onApprove(draft)}>
          {busy
            ? <span className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
            : checkpoint === 'mirror' ? 'אישרתי — אפשר לשתף' : `${g('אני מתחייב', 'אני מתחייבת')} לחלק שלי`}
        </PrimaryButton>
      </div>
    </CoupleScreen>
  );
}
