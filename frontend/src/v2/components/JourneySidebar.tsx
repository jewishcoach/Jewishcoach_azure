import { Heart, Lightbulb, Sparkles } from 'lucide-react';
import { MACRO_STAGES } from '../types';
import type { CollectedData } from '../types';
import { useState } from 'react';

const STAGE_STEP_RANGES: Record<string, { start: number; end: number }> = {
  identification: { start: 0, end: 8 },
  discovery: { start: 9, end: 11 },
  kamaz: { start: 12, end: 12 },
  choice: { start: 13, end: 13 },
  vision: { start: 14, end: 15 },
};

interface JourneySidebarProps {
  currentMacroStage: string;
  currentStep: string;
  collectedData?: CollectedData;
  language: string;
}

export function JourneySidebar({ currentMacroStage, currentStep, collectedData, language }: JourneySidebarProps) {
  const isHe = language.startsWith('he');
  const currentIdx = MACRO_STAGES.findIndex((s) => s.id === currentMacroStage);
  const [activeTab, setActiveTab] = useState<'journey' | 'insights'>('journey');

  const currentStepNum = parseInt(currentStep.replace('S', ''), 10) || 0;

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="w-[330px] bg-[#3c5465] hidden lg:flex lg:flex-col flex-shrink-0 order-first min-h-0" dir="rtl">
        {/* Tabs */}
        <div className="flex border-b border-[#4a4440]">
          <button
            type="button"
            onClick={() => setActiveTab('insights')}
            className={`flex-1 flex flex-col items-center gap-2 py-4 text-xs font-semibold transition-colors
              ${activeTab === 'insights' ? 'text-[#03ffe6]' : 'text-[rgba(3,255,230,0.4)]'}`}
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            <Lightbulb size={20} />
            <span>{isHe ? `התובנות שלי (${countInsights(collectedData)})` : `My Insights (${countInsights(collectedData)})`}</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('journey')}
            className={`flex-1 flex flex-col items-center gap-2 py-4 text-xs font-semibold transition-colors relative
              ${activeTab === 'journey' ? 'text-[#03ffe6] bg-[#2d4658]' : 'text-[rgba(3,255,230,0.4)]'}`}
            style={{ fontFamily: "'Heebo', sans-serif" }}
          >
            <Sparkles size={20} />
            <span>{isHe ? 'המסע שלי' : 'My Journey'}</span>
            {activeTab === 'journey' && (
              <div className="absolute bottom-0 inset-x-0 h-0.5 bg-[#03ffe6]" />
            )}
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-6 scrollbar-hide" style={{ scrollbarWidth: 'none' }}>
          {activeTab === 'journey' && (
            <>
              {/* Section title */}
              <div className="flex items-center justify-center h-[50px]">
                <h3 className="text-base font-semibold text-[#03ffe6]" style={{ fontFamily: "'Heebo', sans-serif" }}>
                  {isHe ? 'איפה אני במסע' : 'Where am I'}
                </h3>
              </div>

              {/* Stage list */}
              <div className="space-y-6 pe-7">
                {MACRO_STAGES.map((stage, idx) => {
                  const isActive = idx === currentIdx;
                  const isCompleted = idx < currentIdx;
                  const isFuture = idx > currentIdx;

                  return (
                    <div
                      key={stage.id}
                      className={`flex items-center gap-6 ${isFuture ? 'opacity-50' : ''}`}
                    >
                      {/* Progress circle */}
                      <StageProgressCircle
                        stageId={stage.id}
                        isActive={isActive}
                        isCompleted={isCompleted}
                        currentStepNum={currentStepNum}
                      />

                      {/* Stage text — left of circle (end in RTL) */}
                      <div className="flex-1 min-w-0 text-right">
                        <p
                          className="text-sm font-semibold text-[#03ffe6]"
                          style={{ fontFamily: "'Heebo', sans-serif" }}
                        >
                          {isHe ? stage.title_he : stage.title_en}
                        </p>
                        <p
                          className="text-xs mt-0.5 text-white"
                          style={{ fontFamily: "'Heebo', sans-serif" }}
                        >
                          {isHe ? stage.description_he : stage.description_en}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          )}

          {activeTab === 'insights' && (
            <InsightsPanel collectedData={collectedData} isHe={isHe} />
          )}
        </div>

        {/* Bottom stats section */}
        <div className="border-t border-[rgba(3,255,230,0.47)] p-5 pt-8 space-y-6" dir="rtl">
          <h3 className="text-[14px] font-semibold text-[#03ffe6] text-right" style={{ fontFamily: "'Heebo', sans-serif" }}>
            {isHe ? 'מה שגיליתי בדרך' : 'What I discovered'}
          </h3>
          <DiscoveryCounter icon={<Lightbulb size={16} />} count={countInsights(collectedData)} label={isHe ? 'תובנות שהתגלו' : 'Insights'} />
          <DiscoveryCounter icon={<Sparkles size={16} />} count={countPatterns(collectedData)} label={isHe ? 'דפוסים שזיהיתי' : 'Patterns'} />
          <DiscoveryCounter icon={<Heart size={16} />} count={countDecisions(collectedData)} label={isHe ? 'החלטות שקיבלתי' : 'Decisions'} />
        </div>
      </aside>

      {/* Mobile bottom bar */}
      <div className="fixed bottom-0 inset-x-0 lg:hidden bg-[#2d4658]/95 backdrop-blur-sm border-t border-[#3c5465] z-10">
        <div className="flex items-center justify-start gap-3 py-2.5 px-4" dir="ltr">
          {MACRO_STAGES.map((stage, idx) => {
            const isActive = idx === currentIdx;
            const isCompleted = idx < currentIdx;

            return (
              <div key={stage.id} className="flex flex-col items-center gap-1">
                <div
                  className={`
                    w-3 h-3 rounded-full transition-all duration-300
                    ${isCompleted ? 'bg-[#03ffe6]' : ''}
                    ${isActive ? 'bg-[#03ffe6] ring-2 ring-[#03ffe6]/40 scale-125' : ''}
                    ${!isActive && !isCompleted ? 'bg-[#3c5465]' : ''}
                  `}
                />
                {isActive && (
                  <span className="text-[10px] text-[#03ffe6] font-medium" style={{ fontFamily: "'Heebo', sans-serif" }}>
                    {isHe ? stage.title_he : stage.title_en}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
}

// Ordered list of insight fields, grouped by stage progression
const INSIGHT_DISPLAY_ORDER: { key: string; label: string; group: string }[] = [
  // Identification (S0-S8)
  { key: 'topic', label: 'נושא האימון', group: 'זיהוי' },
  { key: 'event_description', label: 'האירוע', group: 'זיהוי' },
  { key: 'emotions', label: 'רגשות שזיהיתי', group: 'זיהוי' },
  { key: 'thought', label: 'המחשבה הפנימית', group: 'זיהוי' },
  { key: 'action_actual', label: 'מה עשיתי (מצוי)', group: 'זיהוי' },
  { key: 'action_desired', label: 'מה הייתי רוצה לעשות', group: 'זיהוי' },
  { key: 'emotion_desired', label: 'איך הייתי רוצה להרגיש', group: 'זיהוי' },
  { key: 'thought_desired', label: 'מה הייתי רוצה לחשוב', group: 'זיהוי' },
  { key: 'gap_name', label: 'שם הפער', group: 'זיהוי' },
  { key: 'gap_score', label: 'ציון הפער', group: 'זיהוי' },
  { key: 'pattern', label: 'הדפוס החוזר', group: 'זיהוי' },
  // Discovery (S9-S11)
  { key: 'paradigm', label: 'הפרדיגמה', group: 'גילוי' },
  { key: 'stance.reality_belief', label: 'תפיסת המציאות', group: 'גילוי' },
  { key: 'stance.trigger', label: 'הטריגר', group: 'גילוי' },
  { key: 'stance.gains', label: 'רווחים מהדפוס', group: 'גילוי' },
  { key: 'stance.losses', label: 'הפסדים מהדפוס', group: 'גילוי' },
  // KaMaZ (S12)
  { key: 'forces.source', label: 'כוחות מקור', group: 'כרטיס מהות זהות' },
  { key: 'forces.nature', label: 'כוחות טבע', group: 'כרטיס מהות זהות' },
  // Choice (S13)
  { key: 'renewal', label: 'הבחירה החדשה', group: 'בחירה' },
  // Vision (S14-S15)
  { key: 'vision', label: 'החזון', group: 'חזון' },
  { key: 'commitment', label: 'המחויבות', group: 'חזון' },
];

function getNestedValue(data: Record<string, unknown>, path: string): unknown {
  const parts = path.split('.');
  let current: unknown = data;
  for (const part of parts) {
    if (current == null || typeof current !== 'object') return null;
    current = (current as Record<string, unknown>)[part];
  }
  return current;
}

function formatSimpleValue(value: unknown): string | null {
  if (value == null || value === '') return null;
  if (Array.isArray(value)) {
    const filtered = value.filter(Boolean);
    return filtered.length > 0 ? filtered.join(', ') : null;
  }
  if (typeof value === 'number') return String(value);
  if (typeof value === 'string') return value;
  return null;
}

const SKIP_KEYS = new Set(['entities', 'gap_booklet_moves', 'offer_trait_picker']);

function getOrderedInsights(collectedData?: CollectedData): { key: string; label: string; group: string; value: string }[] {
  if (!collectedData) return [];
  const results: { key: string; label: string; group: string; value: string }[] = [];
  for (const item of INSIGHT_DISPLAY_ORDER) {
    const raw = getNestedValue(collectedData as Record<string, unknown>, item.key);
    const formatted = formatSimpleValue(raw);
    if (formatted) {
      results.push({ ...item, value: formatted });
    }
  }
  return results;
}

function countInsights(collectedData?: CollectedData): number {
  return getOrderedInsights(collectedData).length;
}

function countPatterns(collectedData?: CollectedData): number {
  if (!collectedData) return 0;
  let count = 0;
  if (collectedData.pattern) count++;
  if (collectedData.paradigm) count++;
  if (collectedData.gap_name) count++;
  const stance = (collectedData as Record<string, unknown>).stance as Record<string, unknown> | undefined;
  if (stance?.reality_belief) count++;
  return count;
}

function countDecisions(collectedData?: CollectedData): number {
  if (!collectedData) return 0;
  let count = 0;
  if (collectedData.renewal) count++;
  if (collectedData.commitment) count++;
  if (collectedData.vision) count++;
  return count;
}

function InsightsPanel({ collectedData, isHe }: { collectedData?: CollectedData; isHe: boolean }) {
  const insights = getOrderedInsights(collectedData);

  if (insights.length === 0) {
    return (
      <div className="flex items-center justify-center h-40">
        <p className="text-sm text-[rgba(255,255,255,0.4)]" style={{ fontFamily: "'Heebo', sans-serif" }}>
          {isHe ? 'התובנות יתווספו במהלך המסע' : 'Insights will appear during the journey'}
        </p>
      </div>
    );
  }

  let lastGroup = '';
  return (
    <div className="space-y-3">
      {insights.map(({ key, label, group, value }) => {
        const showGroupHeader = group !== lastGroup;
        lastGroup = group;
        return (
          <div key={key}>
            {showGroupHeader && (
              <p className="text-[10px] font-bold uppercase tracking-wider text-[rgba(3,255,230,0.5)] mt-4 mb-2" style={{ fontFamily: "'Heebo', sans-serif" }}>
                {group}
              </p>
            )}
            <div className="bg-[rgba(255,255,255,0.08)] rounded-lg p-3 space-y-1">
              <p className="text-[10px] font-semibold text-[#03ffe6] uppercase tracking-wide" style={{ fontFamily: "'Heebo', sans-serif" }}>
                {label}
              </p>
              <p className="text-sm text-[rgba(245,243,240,0.85)] leading-relaxed" style={{ fontFamily: "'Heebo', sans-serif" }}>
                {value}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function StageProgressCircle({ stageId, isActive, isCompleted, currentStepNum }: {
  stageId: string; isActive: boolean; isCompleted: boolean; currentStepNum: number;
}) {
  const range = STAGE_STEP_RANGES[stageId];
  const totalSteps = range ? range.end - range.start + 1 : 1;

  let progress = 0;
  if (isCompleted) {
    progress = 1;
  } else if (isActive && range) {
    const stepsCompleted = Math.max(0, currentStepNum - range.start);
    progress = Math.min(stepsCompleted / totalSteps, 1);
  }

  const size = 24;
  const strokeWidth = 3;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference * (1 - progress);

  return (
    <div className="relative flex-shrink-0 w-6 h-6">
      {/* Background ring (white/transparent) */}
      <svg className="absolute inset-0" width={size} height={size}>
        <circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.3)"
          strokeWidth={strokeWidth}
        />
        {/* Progress arc */}
        {(isActive || isCompleted) && (
          <circle
            cx={size / 2} cy={size / 2} r={radius}
            fill="none"
            stroke="#03ffe6"
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            strokeLinecap="round"
            transform={`rotate(-90 ${size / 2} ${size / 2})`}
            className="transition-all duration-500"
          />
        )}
      </svg>
      {/* Inner dot */}
      <div className={`absolute inset-[5px] rounded-full ${isCompleted || isActive ? 'bg-[#03ffe6]' : 'bg-[rgba(3,255,230,0.4)]'}`} />
    </div>
  );
}

function DiscoveryCounter({ icon, count, label }: { icon: React.ReactNode; count: number; label: string }) {
  return (
    <div className="flex items-center gap-4 w-full">
      <div className="w-8 h-8 rounded-lg bg-[rgba(3,255,230,0.2)] flex items-center justify-center text-[#03ffe6] shrink-0">
        {icon}
      </div>
      <div className="flex flex-col items-start">
        <span className="text-2xl font-semibold text-[#03ffe6]" style={{ fontFamily: "'Heebo', sans-serif" }}>{count}</span>
        <span className="text-[13px] text-[rgba(255,255,255,0.33)] whitespace-nowrap" style={{ fontFamily: "'Heebo', sans-serif" }}>{label}</span>
      </div>
    </div>
  );
}
