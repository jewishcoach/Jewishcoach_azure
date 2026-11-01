import type { CSSProperties } from 'react';

// A card's continue button. While something is missing it says what ("כדי להמשיך — תני שם לפער") instead of a
// silently faded button — a client sat in front of a locked gap card not knowing the name field was required
// (Nov 1). A tap on it brings the missing field into view, focuses it and marks it for a moment.
interface SubmitButtonProps {
  label: string;
  missing?: string | null;              // what is still missing, in the client's words; empty = ready
  target?: () => HTMLElement | null;    // the first missing field
  onSubmit: () => void;
  isSubmitting?: boolean;
  className: string;
  style?: CSSProperties;
}

const MARK = ['ring-2', 'ring-[#9747ff]', 'ring-offset-2'];

export function SubmitButton({ label, missing, target, onSubmit, isSubmitting, className, style }: SubmitButtonProps) {
  const blocked = !!missing;
  const handleClick = () => {
    if (isSubmitting) return;
    if (!blocked) { onSubmit(); return; }
    const el = target?.();
    if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    el.focus({ preventScroll: true });
    el.classList.add(...MARK);
    window.setTimeout(() => el.classList.remove(...MARK), 1600);
  };
  return (
    <button
      type="button"
      aria-disabled={blocked || isSubmitting}
      onClick={handleClick}
      className={`${className} ${blocked || isSubmitting ? 'opacity-60' : ''}`}
      style={style}
    >
      {isSubmitting ? '...' : blocked ? missing : label}
    </button>
  );
}
