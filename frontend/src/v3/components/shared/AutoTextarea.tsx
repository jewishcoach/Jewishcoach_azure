import { useLayoutEffect, useRef, type TextareaHTMLAttributes } from 'react';

// A textarea that grows with its text — a prefilled stance was cut after two lines on the phone
export function AutoTextarea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const ref = useRef<HTMLTextAreaElement>(null);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${el.scrollHeight + 2}px`;
  }, [props.value]);
  return <textarea ref={ref} {...props} />;
}
