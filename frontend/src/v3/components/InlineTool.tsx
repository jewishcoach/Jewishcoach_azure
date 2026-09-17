import type { ActiveInlineTool } from '../types';
import { CardShell } from './shared/CardShell';

interface InlineToolProps {
  tool: ActiveInlineTool;
  onSubmit: (toolType: string, data: Record<string, unknown>) => void;
  isSubmitting: boolean;
}

export function InlineTool({ tool, onSubmit, isSubmitting }: InlineToolProps) {
  return (
    <CardShell titleHe={tool.title_he} instructionHe={tool.instruction_he}>
      {/* Placeholder — real tool components replace this per tool_type in later phases */}
      <div className="text-center py-8 space-y-4">
        <div className="w-12 h-12 rounded-full bg-[rgba(3,255,230,0.15)] flex items-center justify-center mx-auto">
          <span className="text-[#03ffe6] text-lg">✦</span>
        </div>
        <p
          className="text-sm text-[rgba(45,70,88,0.5)]"
          style={{ fontFamily: "'Heebo', sans-serif" }}
        >
          {tool.tool_type}
        </p>
        <button
          type="button"
          disabled={isSubmitting}
          onClick={() => onSubmit(tool.tool_type, {})}
          className="px-6 py-2.5 rounded-xl bg-[#9747ff] text-white text-sm hover:bg-[#8035e6] transition-colors disabled:opacity-50"
          style={{ fontFamily: "'Heebo', sans-serif" }}
        >
          {isSubmitting ? '...' : 'שלח'}
        </button>
      </div>
    </CardShell>
  );
}
