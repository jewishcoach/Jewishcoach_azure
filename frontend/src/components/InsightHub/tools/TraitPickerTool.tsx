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
  }: {
    title: string;
    subtitle: string;
    emoji: string;
    input: string;
    setInput: (v: string) => void;
    traits: string[];
    setTraits: (v: string[]) => void;
    placeholder: string;
  }) => (
    <div className="bg-gray-50 rounded-xl p-4 space-y-3">
      <div className={`flex items-center gap-2 ${isRTL ? 'flex-row-reverse' : ''}`}>
        <span className="text-2xl">{emoji}</span>
        <div className={isRTL ? 'text-right' : 'text-left'}>
          <div className="font-semibold text-primary text-sm">{title}</div>
          <div className="text-xs text-gray-500">{subtitle}</div>
        </div>
      </div>

      {/* Tag list */}
      {traits.length > 0 && (
        <div className={`flex flex-wrap gap-2 ${isRTL ? 'flex-row-reverse' : ''}`}>
          {traits.map(trait => (
            <motion.span
              key={trait}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex items-center gap-1 bg-accent/20 text-primary text-xs px-3 py-1 rounded-full"
            >
              {trait}
              <button
                onClick={() => removeTrait(trait, traits, setTraits)}
                className="text-gray-400 hover:text-red-500 transition-colors ml-1"
              >
                <X size={12} />
              </button>
            </motion.span>
          ))}
        </div>
      )}

      {/* Input */}
      <div className={`flex gap-2 ${isRTL ? 'flex-row-reverse' : ''}`}>
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => handleKeyDown(e, input, setInput, traits, setTraits)}
          placeholder={placeholder}
          dir={isRTL ? 'rtl' : 'ltr'}
          className="flex-1 text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-accent/40 bg-white"
        />
        <button
          onClick={() => addTrait(input, setInput, traits, setTraits)}
          disabled={!input.trim()}
          className="p-2 rounded-lg bg-accent/20 text-primary hover:bg-accent/40 disabled:opacity-40 transition-colors"
        >
          <Plus size={16} />
        </button>
      </div>
    </div>
  );

  return (
    <div className={`bg-white rounded-xl p-5 shadow-lg border border-gray-200 space-y-4 ${isRTL ? 'text-right' : 'text-left'}`} dir={isRTL ? 'rtl' : 'ltr'}>
      <Section
        title={isRTL ? 'מקור – ערכים ואמונות' : 'Source – Values & Beliefs'}
        subtitle={isRTL ? 'מה מניע אותך? מה חשוב לך?' : 'What drives you? What matters to you?'}
        emoji="🌱"
        input={sourceInput}
        setInput={setSourceInput}
        traits={sourceTraits}
        setTraits={setSourceTraits}
        placeholder={isRTL ? 'למשל: אמת, צדק, משפחה...' : 'e.g. honesty, justice, family...'}
      />

      <Section
        title={isRTL ? 'טבע – יכולות וכישרונות' : 'Nature – Abilities & Talents'}
        subtitle={isRTL ? 'מה טבעי לך? במה אתה מצטיין?' : 'What comes naturally? What are you good at?'}
        emoji="💎"
        input={natureInput}
        setInput={setNatureInput}
        traits={natureTraits}
        setTraits={setNatureTraits}
        placeholder={isRTL ? 'למשל: יצירתיות, הקשבה, ניתוח...' : 'e.g. creativity, listening, analysis...'}
      />

      <button
        onClick={handleSubmit}
        disabled={isSubmitting || (sourceTraits.length === 0 && natureTraits.length === 0)}
        className="w-full flex items-center justify-center gap-2 bg-primary text-white py-3 rounded-xl font-medium text-sm hover:bg-primary/90 disabled:opacity-50 transition-colors"
      >
        <Send size={16} />
        {isRTL ? 'שלח' : 'Send'}
      </button>
    </div>
  );
};
