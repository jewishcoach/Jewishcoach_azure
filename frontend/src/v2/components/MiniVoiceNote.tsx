import { useState, useRef } from 'react';
import { Headphones } from 'lucide-react';

interface MiniVoiceNoteProps {
  src: string;
  label: string;
}

// Benny's recorded explanation of a concept (המצוי, הדפוס …). It was a 24px pill with 10px text beside "בני", and
// people missed it (user, Nov 9) — now a card of its own above the message: a 44px play button, "בני מסביר: …"
// and the length, so it reads as something to press.
export function MiniVoiceNote({ src, label }: MiniVoiceNoteProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState<number | null>(null);
  const [played, setPlayed] = useState(false);

  const toggle = async () => {
    const el = audioRef.current;
    if (!el) return;
    if (playing) {
      el.pause();
      setPlaying(false);
    } else {
      try {
        await el.play();
        setPlaying(true);
        setPlayed(true);
      } catch (e) {
        console.error('Voice note play failed:', e);
      }
    }
  };

  const fmt = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;

  return (
    <button
      type="button"
      onClick={toggle}
      className="group flex items-center gap-3 self-stretch sm:self-start sm:w-[400px] max-w-full px-3 py-2.5 rounded-2xl
                 bg-[#e8fffc] border border-[#7ff5e9] hover:bg-[#d6fbf6] transition-colors cursor-pointer text-right
                 shadow-[0_2px_8px_rgba(42,157,143,0.15)]"
      aria-label={`${playing ? 'עצירת' : 'השמעת'} ההקלטה של בני: ${label}`}
    >
      <audio
        ref={audioRef}
        src={src}
        preload="metadata"
        onLoadedMetadata={() => { const el = audioRef.current; if (el && Number.isFinite(el.duration)) setDuration(el.duration); }}
        onTimeUpdate={() => {
          const el = audioRef.current;
          if (el && el.duration) setProgress((el.currentTime / el.duration) * 100);
        }}
        onEnded={() => { setPlaying(false); setProgress(0); }}
      />
      <span className={`relative w-11 h-11 shrink-0 rounded-full bg-[#2A9D8F] flex items-center justify-center shadow-md
                        group-hover:bg-[#23877b] transition-colors`}>
        {!played && <span className="absolute inset-0 rounded-full bg-[#2A9D8F] opacity-40 animate-ping" />}
        {playing ? (
          <svg width={18} height={18} viewBox="0 0 24 24" fill="white" className="relative">
            <rect x="6" y="4" width="4" height="16" rx="1" />
            <rect x="14" y="4" width="4" height="16" rx="1" />
          </svg>
        ) : (
          <svg width={18} height={18} viewBox="0 0 24 24" fill="white" className="relative" style={{ marginInlineStart: 2 }}>
            <path d="M8 5v14l11-7z" />
          </svg>
        )}
      </span>
      <span className="flex-1 min-w-0" style={{ fontFamily: "'Heebo', sans-serif" }}>
        <span className="flex items-center gap-1.5 text-[12px] text-[#2A9D8F] font-medium">
          <Headphones size={13} /> הקלטה קצרה
        </span>
        <span className="block text-[15px] font-semibold text-[#1f3444] truncate">בני מסביר: {label}</span>
        <span className="mt-1.5 flex items-center gap-2">
          <span className="flex-1 h-1.5 rounded-full bg-[rgba(42,157,143,0.2)] overflow-hidden">
            <span className="block h-full bg-[#2A9D8F] rounded-full transition-all duration-200" style={{ width: `${progress}%` }} />
          </span>
          {duration != null && (
            <span className="text-[12px] text-[#4a6070] tabular-nums" dir="ltr">{fmt(duration)}</span>
          )}
        </span>
      </span>
    </button>
  );
}
