import { useState } from 'react';
import { motion } from 'framer-motion';
import { Plus, X, Send } from 'lucide-react';

interface TraitPickerToolProps {
  onSubmit: (submission: { tool_type: string; data: any }) => Promise<void>;
  language: 'he' | 'en';
}

export const TraitPickerTool = ({ onSubmit, language }: TraitPickerToolProps) => {
  const isRTL = language === 'he';
  const [sourceTraits, setSourceTraits] = useState<string[]>([]);
  const [natureTraits, setNatureTraits] = useState<string[]>([]);
  const [sourceInput, setSourceInput] = useState('');
  const [natureInput, setNatureInput] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const addTrait = (
    input: string,
    setInput: (v: string) => void,
    traits: string[],
    setTraits: (v: string[]) => void
  ) => {
    const val = input.trim();
    if (val && !traits.includes(val)) {
      setTraits([...traits, val]);
    }
    setInput('');
  };

  const removeTrait = (trait: string, traits: string[], setTraits: (v: string[]) => void) => {
    setTraits(traits.filter(t => t !== trait));
  };

  const handleKeyDown = (
    e: React.KeyboardEvent,
    input: string,
    setInput: (v: string) => void,
    traits: string[],
    setTraits: (v: string[]) => void
  ) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      addTrait(input, setInput, traits, setTraits);
    }
  };

  const handleSubmit = async () => {
    if (sourceTraits.length === 0 && natureTraits.length === 0) return;
    setIsSubmitting(true);
    await onSubmit({
      tool_type: 'trait_picker',
      data: {
        source_forces: sourceTraits,
        nature_forces: natureTraits,
      },
    });
    setIsSubmitting(false);
  };

  const Section = ({
    title,
    subtitle,
    emoji,
    input,
    setInput,
    traits,
    setTraits,
    placeholder,
    variant,
  }: {
    title: string;
    subtitle: string;
    emoji: string;
    input: string;
    setInput: (v: string) => void;
    traits: string[];
    setTraits: (v: string[]) => void;
    placeholder: string;
    variant: 'source' | 'nature';
  }) => {
    const stripe =
      variant === 'source'
        ? 'from-emerald-500/90 to-teal-600/80'
        : 'from-violet-500/85 to-indigo-600/75';
    const tagWrap =
      variant === 'source'
        ? 'border-emerald-200/70 bg-emerald-50/95 text-slate-800'
        : 'border-violet-200/70 bg-violet-50/95 text-slate-800';
    const addBtnHover =
      variant === 'source'
        ? 'hover:bg-emerald-50 hover:text-emerald-800 disabled:hover:bg-transparent'
        : 'hover:bg-violet-50 hover:text-violet-900 disabled:hover:bg-transparent';
    const focusRing =
      variant === 'source' ? 'focus-within:ring-emerald-500/20' : 'focus-within:ring-violet-500/20';

    return (
      <div className="relative rounded-xl border border-slate-200/90 bg-white p-4 shadow-sm space-y-3">
        <div className={`absolute inset-x-0 top-0 h-1 rounded-t-xl bg-gradient-to-r ${stripe}`} aria-hidden />
        <div className={`flex items-start gap-2.5 ${isRTL ? 'flex-row-reverse' : ''}`}>
          <span className="text-2xl leading-none shrink-0" aria-hidden>
            {emoji}
          </span>
          <div className={`min-w-0 flex-1 ${isRTL ? 'text-right' : 'text-left'}`}>
            <div className="font-semibold text-slate-800 text-sm tracking-tight">{title}</div>
            <div className="text-xs text-slate-500 mt-0.5 leading-snug">{subtitle}</div>
          </div>
        </div>

        {traits.length > 0 && (
          <div className={`flex flex-wrap gap-2 ${isRTL ? 'flex-row-reverse' : ''}`}>
            {traits.map(trait => (
              <motion.span
                key={trait}
                initial={{ opacity: 0, scale: 0.96 }}
                animate={{ opacity: 1, scale: 1 }}
                className={`inline-flex max-w-full items-center gap-1 rounded-full border pl-3 pr-1 py-1 text-xs font-medium shadow-[0_1px_2px_rgba(15,23,42,0.04)] ${tagWrap}`}
              >
                <span className="min-w-0 truncate py-0.5">{trait}</span>
                <button
                  type="button"
                  onClick={() => removeTrait(trait, traits, setTraits)}
                  title={isRTL ? 'הסר' : 'Remove'}
                  aria-label={isRTL ? `הסר את ${trait}` : `Remove ${trait}`}
                  className="flex size-7 shrink-0 items-center justify-center rounded-full text-slate-400 transition-colors hover:bg-red-100 hover:text-red-600"
                >
                  <X size={14} strokeWidth={2} />
                </button>
              </motion.span>
            ))}
          </div>
        )}

        <div
          className={`
            flex min-h-[2.75rem] items-stretch overflow-hidden rounded-lg border border-slate-200 bg-white
            shadow-[0_1px_2px_rgba(15,23,42,0.04)] transition-shadow
            focus-within:border-slate-300 focus-within:shadow-md focus-within:ring-2 ${focusRing}
          `}
        >
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => handleKeyDown(e, input, setInput, traits, setTraits)}
            placeholder={placeholder}
            dir={isRTL ? 'rtl' : 'ltr'}
            className="min-w-0 flex-1 border-0 bg-transparent px-3 py-2.5 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-0"
          />
          <button
            type="button"
            onClick={() => addTrait(input, setInput, traits, setTraits)}
            disabled={!input.trim()}
            title={isRTL ? 'הוסף לרשימה' : 'Add to list'}
            aria-label={isRTL ? 'הוסף לרשימה' : 'Add to list'}
            className={`flex shrink-0 items-center justify-center border-s border-slate-100 px-3.5 text-slate-500 transition-colors disabled:cursor-not-allowed disabled:opacity-35 ${addBtnHover}`}
          >
            <Plus size={18} strokeWidth={2} />
          </button>
        </div>
      </div>
    );
  };

  return (
    <form
      className={`space-y-4 rounded-2xl border border-slate-200/90 bg-gradient-to-b from-slate-50 to-white p-5 shadow-md ${isRTL ? 'text-right' : 'text-left'}`}
      dir={isRTL ? 'rtl' : 'ltr'}
      onSubmit={(e) => {
        e.preventDefault();
        if (sourceTraits.length === 0 && natureTraits.length === 0) return;
        void handleSubmit();
      }}
    >
      <Section
        variant="source"
        title={isRTL ? 'מקור (נפש אלוקית)' : 'Source (divine soul)'}
        subtitle={
          isRTL
            ? 'כוחות אור, ערכים, שליחות — הפריט הראשון הוא התכונה המובילה'
            : 'Light, values, mission — first item is your leading trait'
        }
        emoji="🌱"
        input={sourceInput}
        setInput={setSourceInput}
        traits={sourceTraits}
        setTraits={setSourceTraits}
        placeholder={isRTL ? 'למשל: אמת, שליחות, רחמים…' : 'e.g. truth, purpose, compassion…'}
      />

      <Section
        variant="nature"
        title={isRTL ? 'טבע (נפש טבעית/בהמית)' : 'Nature (natural/animal soul)'}
        subtitle={
          isRTL
            ? 'צרכים, הגנות, כבדות — כלי עבודה; הראשון = המובילה'
            : 'Needs, defenses, heaviness — working material; first = leading trait'
        }
        emoji="💎"
        input={natureInput}
        setInput={setNatureInput}
        traits={natureTraits}
        setTraits={setNatureTraits}
        placeholder={isRTL ? 'למשל: פחד מביקורת, שליטה, עייפות…' : 'e.g. fear of judgment, control, fatigue…'}
      />

      <button
        type="submit"
        disabled={isSubmitting || (sourceTraits.length === 0 && natureTraits.length === 0)}
        className="w-full flex items-center justify-center gap-2 py-3.5 rounded-xl font-semibold text-base
          bg-primary text-white shadow-sm border border-primary-dark/30
          hover:bg-primary-light hover:text-white
          focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-500
          disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-primary transition-colors [&_svg]:shrink-0"
      >
        <Send size={18} className="opacity-95" aria-hidden />
        <span className="text-white">
          {isSubmitting
            ? (isRTL ? 'שולח…' : 'Submitting…')
            : (isRTL ? 'שלח למאמן' : 'Send to coach')}
        </span>
      </button>
    </form>
  );
};
