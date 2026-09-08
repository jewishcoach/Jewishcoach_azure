import { useState, useRef } from 'react';

interface MiniVoiceNoteProps {
  src: string;
  label: string;
}

export function MiniVoiceNote({ src, label }: MiniVoiceNoteProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);

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
      } catch (e) {
        console.error('Voice note play failed:', e);
      }
    }
  };

  return (
    <button
      type="button"
      onClick={toggle}
      className="inline-flex items-center gap-1.5 h-6 px-2 rounded-full bg-[rgba(3,255,230,0.12)] hover:bg-[rgba(3,255,230,0.25)] transition-colors cursor-pointer border-none"
      title={label}
    >
      <audio
        ref={audioRef}
        src={src}
        preload="none"
        onTimeUpdate={() => {
          const el = audioRef.current;
          if (el && el.duration) setProgress((el.currentTime / el.duration) * 100);
        }}
        onEnded={() => { setPlaying(false); setProgress(0); }}
      />
      {playing ? (
        <svg width={10} height={10} viewBox="0 0 24 24" fill="#2A9D8F">
          <rect x="6" y="4" width="4" height="16" rx="1" />
          <rect x="14" y="4" width="4" height="16" rx="1" />
        </svg>
      ) : (
        <svg width={10} height={10} viewBox="0 0 24 24" fill="#2A9D8F">
          <path d="M8 5v14l11-7z" />
        </svg>
      )}
      <div className="w-12 h-1 rounded-full bg-[rgba(3,255,230,0.3)] overflow-hidden">
        <div
          className="h-full bg-[#2A9D8F] rounded-full transition-all duration-200"
          style={{ width: `${progress}%` }}
        />
      </div>
      <span className="text-[10px] text-[#2A9D8F] font-medium whitespace-nowrap" style={{ fontFamily: "'Heebo', sans-serif" }}>
        {label}
      </span>
    </button>
  );
}
