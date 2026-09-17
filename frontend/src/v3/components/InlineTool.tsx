import type { ActiveInlineTool } from '../types';
import { CardShell } from './shared/CardShell';
import { TraitCardBuilder } from './tools/TraitCardBuilder';
import { EventForm } from './tools/EventForm';
import { EmotionSelector } from './tools/EmotionSelector';
import { ActionField } from './tools/ActionField';
import { MatzuiSummary } from './tools/MatzuiSummary';
import { ComparisonCard } from './tools/ComparisonCard';
import { GapCard } from './tools/GapCard';
import { DeclarationCard } from './tools/DeclarationCard';
import { CommitmentCard } from './tools/CommitmentCard';
import { SentenceBuilder } from './tools/SentenceBuilder';
import { BalanceScale } from './tools/BalanceScale';

interface InlineToolProps {
  tool: ActiveInlineTool;
  onSubmit: (toolType: string, data: Record<string, unknown>) => void;
  isSubmitting: boolean;
}

export function InlineTool({ tool, onSubmit, isSubmitting }: InlineToolProps) {
  switch (tool.tool_type) {
    case 'event_form':
      return (
        <EventForm
          onSubmit={onSubmit}
          isSubmitting={isSubmitting}
        />
      );

    case 'emotion_selector':
      return (
        <EmotionSelector
          onSubmit={onSubmit}
          isSubmitting={isSubmitting}
        />
      );

    case 'action_field':
      return (
        <ActionField
          onSubmit={onSubmit}
          isSubmitting={isSubmitting}
        />
      );

    case 'matzui_summary':
      return (
        <MatzuiSummary
          data={tool.data as { emotions?: string[]; thought?: string; action?: string } | undefined}
          onSubmit={onSubmit}
          isSubmitting={isSubmitting}
        />
      );

    case 'comparison_card':
      return (
        <ComparisonCard
          data={tool.data as { emotions?: string[]; thought?: string; action_actual?: string } | undefined}
          onSubmit={onSubmit}
          isSubmitting={isSubmitting}
        />
      );

    case 'sentence_builder':
      return (
        <SentenceBuilder
          data={tool.data as { pattern?: string } | undefined}
          onSubmit={onSubmit}
          isSubmitting={isSubmitting}
        />
      );

    case 'balance_scale':
      return (
        <BalanceScale
          onSubmit={onSubmit}
          isSubmitting={isSubmitting}
        />
      );

    case 'trait_card_builder':
      return (
        <CardShell>
          <TraitCardBuilder
            data={tool.data as { suggestions?: { source: string[]; nature: string[] }; existing_source?: string[]; existing_nature?: string[] } | undefined}
            onSubmit={onSubmit}
            isSubmitting={isSubmitting}
          />
        </CardShell>
      );

    case 'gap_card':
      return (
        <GapCard
          onSubmit={onSubmit}
          isSubmitting={isSubmitting}
        />
      );

    case 'declaration_card':
      return (
        <DeclarationCard
          data={tool.data as { old_pattern?: string; old_paradigm?: string } | undefined}
          onSubmit={onSubmit}
          isSubmitting={isSubmitting}
        />
      );

    case 'commitment_card':
      return (
        <CommitmentCard
          onSubmit={onSubmit}
          isSubmitting={isSubmitting}
        />
      );

    default:
      return (
        <CardShell titleHe={tool.title_he} instructionHe={tool.instruction_he}>
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
}
