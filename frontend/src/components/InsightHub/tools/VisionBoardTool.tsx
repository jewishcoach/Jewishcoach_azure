import { motion } from 'framer-motion';
import { Send } from 'lucide-react';

interface VisionBoardToolProps {
  onSubmit: (submission: { tool_type: string; data: any }) => Promise<void>;
  language: 'he' | 'en';
}

export const VisionBoardTool = ({ onSubmit, language }: VisionBoardToolProps) => {
  const isRTL = language === 'he';

  // Placeholder - to be implemented later
  return (
    <div className="bg-white rounded-xl p-6 shadow-lg border border-gray-200 text-center">
      <div className="text-4xl mb-4">🔮</div>
      <h3 className="text-lg font-semibold text-primary mb-2">
        {isRTL ? 'לוח החזון שלי' : 'My Vision Board'}
      </h3>
      <p className="text-sm text-gray-600 mb-4">
        {isRTL
          ? 'כלי זה יאפשר לך לתאר את החזון שלך בפירוט'
          : 'This tool will help you describe your vision in detail'}
      </p>
      <div className="text-xs text-gray-400">
        {isRTL ? '(בפיתוח)' : '(Coming Soon)'}
      </div>
    </div>
  );
};




