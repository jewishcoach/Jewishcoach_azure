import { Heart } from 'lucide-react';

const SAFE_REPLIES = ['אני בסדר, אפשר להמשיך', 'קשה לי עכשיו'];

// Help-line numbers in the backend's safety text (1201, 101, 988, 911, 112, 999, 000, 13 11 14…) become tel: links
const PHONE_RE = /(13 11 14|\b\d{3,4}\b)/g;

function linkifyPhones(line: string) {
  const parts = line.split(PHONE_RE);
  return parts.map((part, i) =>
    i % 2 === 1 ? (
      <a key={i} href={`tel:${part.replace(/\s/g, '')}`} className="font-semibold text-[#9747ff] underline underline-offset-2">
        {part}
      </a>
    ) : (
      part
    ),
  );
}

interface SafetyMessageProps {
  content: string;
  /** Only on the latest message: quick answers so the user doesn't have to phrase one in a hard moment */
  onQuickReply?: (text: string) => void;
}

/** Backend safety response (risk check-in) — same coach voice, visually set apart, help lines tappable. */
export function SafetyMessage({ content, onQuickReply }: SafetyMessageProps) {
  const lines = content.split('\n');
  return (
    <div className="flex flex-col gap-3 w-full" dir="rtl">
      <div className="flex items-center gap-2 justify-start">
        <Heart size={16} className="text-[#9747ff]" />
        <span className="text-sm text-[#2d4658]" style={{ fontFamily: "'Heebo', sans-serif" }}>בני</span>
      </div>
      <div className="w-full rounded-xl py-4 px-4 bg-[#faf7ff] border border-[#d9c8ff] text-[15px] lg:text-base text-[#2d4658] text-right leading-[22.75px] space-y-1">
        {lines.map((line, i) =>
          line.startsWith('• ') ? (
            <p key={i} className="rounded-lg bg-white border border-[#e7dcff] px-3 py-2 my-1">{linkifyPhones(line.slice(2))}</p>
          ) : (
            <p key={i} className={line.trim() ? '' : 'h-2'}>{linkifyPhones(line)}</p>
          ),
        )}
      </div>
      {onQuickReply && (
        <div className="flex flex-wrap gap-2 w-full">
          {SAFE_REPLIES.map((reply) => (
            <button
              key={reply}
              type="button"
              onClick={() => onQuickReply(reply)}
              className="px-4 h-[34px] rounded-xl border-[0.8px] border-[#9747ff] bg-[rgba(151,71,255,0.05)] text-sm text-[#2d4658] hover:bg-[rgba(151,71,255,0.12)] transition-colors"
              style={{ fontFamily: "'Heebo', sans-serif" }}
            >
              {reply}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
