import { useState } from 'react';
import { motion } from 'framer-motion';
import { Plus, X, Send } from 'lucide-react';

interface ProfitLossToolProps {
  onSubmit: (submission: { tool_type: string; data: any }) => Promise<void>;
  language: 'he' | 'en';
}

export const ProfitLossTool = ({ onSubmit, language }: ProfitLossToolProps) => {
  const [gains, setGains] = useState<string[]>(['']);
  const [losses, setLosses] = useState<string[]>(['']);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const isRTL = language === 'he';

  const addGain = () => setGains([...gains, '']);
  const addLoss = () => setLosses([...losses, '']);

  const updateGain = (index: number, value: string) => {
    const newGains = [...gains];
    newGains[index] = value;
    setGains(newGains);
  };

  const updateLoss = (index: number, value: string) => {
    const newLosses = [...losses];
    newLosses[index] = value;
    setLosses(newLosses);
  };

  const removeGain = (index: number) => {
    setGains(gains.filter((_, i) => i !== index));
  };

  const removeLoss = (index: number) => {
    setLosses(losses.filter((_, i) => i !== index));
  };

  const handleSubmit = async () => {
    // Filter out empty entries
    const filteredGains = gains.filter((g) => g.trim() !== '');
    const filteredLosses = losses.filter((l) => l.trim() !== '');

    if (filteredGains.length === 0 && filteredLosses.length === 0) {
      alert(language === 'he' ? 'אנא הוסף לפחות פריט אחד' : 'Please add at least one item');
      return;
    }

    setIsSubmitting(true);
    try {
      await onSubmit({
        tool_type: 'profit_loss',
        data: {
          gains: filteredGains,
          losses: filteredLosses
        }
      });
      setSubmitted(true);
    } catch (error) {
      console.error('Error submitting profit/loss:', error);
      alert(language === 'he' ? 'שגיאה בשליחת הטופס' : 'Error submitting form');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-green-50 border border-green-300 rounded-xl p-6 text-center"
      >
        <div className="text-green-600 mb-2">✓</div>
        <p className="text-green-700 font-medium">
          {language === 'he' ? 'הטבלה נשלחה בהצלחה למאמן!' : 'Table submitted successfully to your coach!'}
        </p>
      </motion.div>
    );
  }

  return (
    <form
      className="bg-gradient-to-b from-slate-50 to-white rounded-2xl p-5 sm:p-6 shadow-md border border-slate-200/90"
      onSubmit={(e) => {
        e.preventDefault();
        void handleSubmit();
      }}
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-5 mb-6">
        {/* Gains Column */}
        <Column
          title={language === 'he' ? 'מה אני מרוויח?' : 'What do I gain?'}
          items={gains}
          onUpdate={updateGain}
          onRemove={removeGain}
          onAdd={addGain}
          color="green"
          isRTL={isRTL}
        />

        {/* Losses Column */}
        <Column
          title={language === 'he' ? 'מה אני מפסיד?' : 'What do I lose?'}
          items={losses}
          onUpdate={updateLoss}
          onRemove={removeLoss}
          onAdd={addLoss}
          color="red"
          isRTL={isRTL}
        />
      </div>

      {/* Solid primary CTA: guaranteed contrast (gradient accent was invisible when --color-accent was missing from @theme) */}
      <motion.button
        type="submit"
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        disabled={isSubmitting}
        className="w-full flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl font-semibold text-base
          bg-primary text-white shadow-sm border border-primary-dark/30
          hover:bg-primary-light hover:text-white
          focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-500
          disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-primary transition-colors [&_svg]:shrink-0"
      >
        <Send size={18} className="opacity-95" aria-hidden />
        <span className="text-white">
          {isSubmitting
            ? (language === 'he' ? 'שולח…' : 'Submitting…')
            : (language === 'he' ? 'שלח למאמן' : 'Send to coach')}
        </span>
      </motion.button>
    </form>
  );
};

interface ColumnProps {
  title: string;
  items: string[];
  onUpdate: (index: number, value: string) => void;
  onRemove: (index: number) => void;
  onAdd: () => void;
  color: 'green' | 'red';
  isRTL: boolean;
}

const Column = ({ title, items, onUpdate, onRemove, onAdd, color, isRTL }: ColumnProps) => {
  const accentRing = color === 'green' ? 'focus-within:ring-emerald-500/25' : 'focus-within:ring-rose-400/25';
  const topStripe = color === 'green' ? 'from-emerald-500/90 to-emerald-600/80' : 'from-rose-500/85 to-rose-600/75';
  const addHover = color === 'green' ? 'hover:bg-emerald-50 hover:text-emerald-800' : 'hover:bg-rose-50 hover:text-rose-900';

  return (
    <div
      className="relative rounded-xl border border-slate-200/90 bg-white p-4 shadow-sm"
      dir={isRTL ? 'rtl' : 'ltr'}
    >
      <div className={`absolute inset-x-0 top-0 h-1 rounded-t-xl bg-gradient-to-r ${topStripe}`} aria-hidden />
      <h4 className="font-semibold text-slate-800 text-sm tracking-tight mb-3.5 pt-0.5">
        {title}
      </h4>
      <div className="space-y-2.5 mb-3.5">
        {items.map((item, index) => (
          <div
            key={index}
            className={`
              flex min-h-[2.75rem] items-stretch overflow-hidden rounded-lg border border-slate-200 bg-white
              shadow-[0_1px_2px_rgba(15,23,42,0.04)] transition-shadow
              focus-within:border-slate-300 focus-within:shadow-md focus-within:ring-2 ${accentRing}
            `}
          >
            <input
              type="text"
              value={item}
              onChange={(e) => onUpdate(index, e.target.value)}
              placeholder={isRTL ? 'הקלד כאן…' : 'Type here…'}
              className="min-w-0 flex-1 border-0 bg-transparent px-3 py-2.5 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-0"
            />
            {items.length > 1 ? (
              <button
                type="button"
                onClick={() => onRemove(index)}
                title={isRTL ? 'הסר שורה' : 'Remove row'}
                aria-label={isRTL ? 'הסר שורה' : 'Remove row'}
                className="flex shrink-0 items-center justify-center border-s border-slate-100 px-3 text-slate-400 transition-colors hover:bg-red-50 hover:text-red-600"
              >
                <X size={17} strokeWidth={2} />
              </button>
            ) : null}
          </div>
        ))}
      </div>
      <button
        type="button"
        onClick={onAdd}
        className={`inline-flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-slate-200 bg-slate-50/80 py-2.5 text-sm font-medium text-slate-600 transition-colors ${addHover}`}
      >
        <Plus size={17} strokeWidth={2} className="text-slate-500" />
        {isRTL ? 'הוסף שורה' : 'Add row'}
      </button>
    </div>
  );
};




