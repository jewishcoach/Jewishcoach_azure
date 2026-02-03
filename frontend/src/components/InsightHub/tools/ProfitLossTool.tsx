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
    <div className="bg-white rounded-xl p-6 shadow-lg border border-gray-200">
      <div className="grid grid-cols-2 gap-4 mb-6">
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

      {/* Submit Button */}
      <motion.button
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        onClick={handleSubmit}
        disabled={isSubmitting}
        className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-accent to-accent-dark text-white rounded-xl font-semibold hover:shadow-glow transition-all disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <Send size={18} />
        {isSubmitting
          ? (language === 'he' ? 'שולח...' : 'Submitting...')
          : (language === 'he' ? 'שלח למאמן' : 'Send to Coach')}
      </motion.button>
    </div>
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
  const borderColor = color === 'green' ? 'border-green-300' : 'border-red-300';
  const bgColor = color === 'green' ? 'bg-green-50' : 'bg-red-50';

  return (
    <div className={`border-2 ${borderColor} ${bgColor} rounded-lg p-4`}>
      <h4 className="font-semibold text-primary mb-3" dir={isRTL ? 'rtl' : 'ltr'}>{title}</h4>
      <div className="space-y-2 mb-3">
        {items.map((item, index) => (
          <div key={index} className="flex items-center gap-2">
            <input
              type="text"
              value={item}
              onChange={(e) => onUpdate(index, e.target.value)}
              placeholder={isRTL ? 'הוסף פריט...' : 'Add item...'}
              className="flex-1 px-3 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-accent/30 text-sm"
              dir={isRTL ? 'rtl' : 'ltr'}
            />
            {items.length > 1 && (
              <button
                onClick={() => onRemove(index)}
                className="p-1 text-gray-400 hover:text-red-500 transition-colors"
              >
                <X size={16} />
              </button>
            )}
          </div>
        ))}
      </div>
      <button
        onClick={onAdd}
        className="flex items-center gap-1 text-sm text-accent hover:text-accent-dark font-medium"
      >
        <Plus size={16} />
        {isRTL ? 'הוסף פריט' : 'Add item'}
      </button>
    </div>
  );
};




