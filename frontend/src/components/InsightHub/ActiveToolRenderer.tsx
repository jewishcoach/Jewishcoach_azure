import { motion } from 'framer-motion';
import type { ToolCall } from '../../types';
import { ProfitLossTool } from './tools/ProfitLossTool';
import { TraitPickerTool } from './tools/TraitPickerTool';
import { VisionBoardTool } from './tools/VisionBoardTool';
import { GapVisualizer } from './tools/GapVisualizer';
import { ReflectionCard } from './ReflectionCard';
import { GapWidget } from './widgets/GapWidget';
import { PatternWidget } from './widgets/PatternWidget';
import { ListWidget } from './widgets/ListWidget';

interface ActiveToolRendererProps {
  tool: ToolCall;
  onSubmit: (submission: { tool_type: string; data: any }) => Promise<void>;
  language: 'he' | 'en';
}

export const ActiveToolRenderer = ({ tool, onSubmit, language }: ActiveToolRendererProps) => {
  // NEW: Handle Reflection widgets (Real-Time Mirror)
  if (tool.type === 'reflection') {
    const title = language === 'he' ? tool.title_he : tool.title_en;
    const status = tool.status || 'draft';
    const stage = tool.stage || '';
    
    // Determine which widget to render based on stage
    let widgetContent = null;
    
    switch (stage) {
      case 'Gap':
        widgetContent = <GapWidget data={tool.data || {}} language={language} />;
        break;
      case 'Pattern':
        widgetContent = <PatternWidget data={tool.data || {}} language={language} />;
        break;
      case 'Situation':
      case 'Stance':
      case 'Paradigm':
        widgetContent = <ListWidget data={tool.data || {}} stage={stage} language={language} />;
        break;
      default:
        widgetContent = (
          <div className="text-sm text-gray-500 text-center py-4">
            {language === 'he' 
              ? `אין תצוגה מוגדרת לשלב: ${stage}` 
              : `No reflection view defined for stage: ${stage}`}
          </div>
        );
    }
    
    return (
      <ReflectionCard status={status} title={title || ''} language={language}>
        {widgetContent}
      </ReflectionCard>
    );
  }
  
  // LEGACY: Handle interactive tools (the old way)
  const title = language === 'he' ? tool.title_he : tool.title_en;
  const instruction = language === 'he' ? tool.instruction_he : tool.instruction_en;

  const renderTool = () => {
    switch (tool.tool_type) {
      case 'profit_loss':
        return <ProfitLossTool onSubmit={onSubmit} language={language} />;
      case 'trait_picker':
        return <TraitPickerTool onSubmit={onSubmit} language={language} />;
      case 'vision_board_input':
        return <VisionBoardTool onSubmit={onSubmit} language={language} />;
      case 'gap_visualizer':
        return <GapVisualizer language={language} data={tool.data} />;
      default:
        return (
          <div className="text-center py-8 text-gray-500">
            {language === 'he' 
              ? `כלי לא ידוע: ${tool.tool_type}` 
              : `Unknown tool: ${tool.tool_type}`}
          </div>
        );
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
      className="space-y-4"
    >
      {/* Tool Header */}
      <div className="bg-accent/10 border border-accent/30 rounded-xl p-4">
        <h3 className="text-lg font-semibold text-primary mb-2">{title}</h3>
        <p className="text-sm text-primary-dark opacity-80">{instruction}</p>
      </div>

      {/* Tool Content */}
      <div>
        {renderTool()}
      </div>
    </motion.div>
  );
};

