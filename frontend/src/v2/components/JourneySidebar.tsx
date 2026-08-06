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
      <aside className="w-[330px] bg-[#3c5465] hidden lg:flex lg:flex-col flex-shrink-0 order-first" dir="rtl">
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
        <div className="flex-1 overflow-y-auto p-5 space-y-6">
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
        <div className="border-t border-[rgba(3,255,230,0.47)] p-5 pt-8 space-y-6">
          <h3 className="text-sm font-semibold text-[#03ffe6] text-end pe-2" style={{ fontFamily: "'Heebo', sans-serif" }}>
            {isHe ? 'מה שגיליתי בדרך' : 'What I discovered'}
          </h3>
          <DiscoveryCounter icon={<Lightbulb size={16} />} count={0} label={isHe ? 'תובנות שהתגלו' : 'Insights'} />
          <DiscoveryCounter icon={<Sparkles size={16} />} count={0} label={isHe ? 'דפוסים שזיהיתי' : 'Patterns'} />
          <DiscoveryCounter icon={<Heart size={16} />} count={0} label={isHe ? 'החלטות שקיבלתי' : 'Decisions'} />
        </div>
      </aside>

      {/* Mobile bottom bar */}
      <div className="fixed bottom-0 inset-x-0 lg:hidden bg-[#2d4658]/95 backdrop-blur-sm border-t border-[#3c5465] z-10">
        <div className="flex items-center justify-center gap-3 py-2.5 px-4">
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

const INSIGHT_LABELS_HE: Record<string, string> = {
  topic: 'נושא האימון',
  event_description: 'האירוע',
  emotions: 'רגשות',
  thought: 'המחשבה הפנימית',
  action_actual: 'מה עשיתי (מצוי)',
  action_desired: 'מה הייתי רוצה לעשות (רצוי)',
  emotion_desired: 'איך הייתי רוצה להרגיש',
  thought_desired: 'מה הייתי רוצה לחשוב',
  gap_name: 'שם הפער',
  gap_score: 'ציון הפער',
  pattern: 'הדפוס',
  paradigm: 'הפרדיגמה',
  renewal: 'הבחירה החדשה',
  vision: 'החזון',
  commitment: 'המחויבות',
};

function formatInsightValue(value: unknown): string | null {
  if (value == null || value === '') return null;
  if (Array.isArray(value)) {
    const filtered = value.filter(Boolean);
    return filtered.length > 0 ? filtered.join(', ') : null;
  }
  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>).filter(([, v]) => {
      if (Array.isArray(v)) return v.length > 0;
      return v != null && v !== '';
    });
    if (entries.length === 0) return null;
    return entries.map(([k, v]) => {
      const label = INSIGHT_LABELS_HE[k] || k;
      const formatted = Array.isArray(v) ? (v as string[]).join(', ') : String(v);
      return `${label}: ${formatted}`;
    }).join('\n');
  }
  return String(value);
}

const HIDDEN_KEYS = ['entities', 'stance', 'forces', 'gap_booklet_moves', 'offer_trait_picker'];

function countInsights(collectedData?: CollectedData): number {
  if (!collectedData) return 0;
  return Object.entries(collectedData)
    .filter(([k]) => !HIDDEN_KEYS.includes(k))
    .filter(([, v]) => formatInsightValue(v) !== null).length;
}

function InsightsPanel({ collectedData, isHe }: { collectedData?: CollectedData; isHe: boolean }) {
  if (!collectedData || Object.keys(collectedData).length === 0) {
    return (
      <div className="flex items-center justify-center h-40">
        <p className="text-sm text-[rgba(255,255,255,0.4)]" style={{ fontFamily: "'Heebo', sans-serif" }}>
          {isHe ? 'התובנות יתווספו במהלך המסע' : 'Insights will appear during the journey'}
        </p>
      </div>
    );
  }

  const entries = Object.entries(collectedData)
    .filter(([key]) => !HIDDEN_KEYS.includes(key))
    .map(([key, value]) => ({ key, formatted: formatInsightValue(value) }))
    .filter((e) => e.formatted !== null);

  return (
    <div className="space-y-4">
      {entries.map(({ key, formatted }) => (
        <div key={key} className="space-y-1">
          <p className="text-xs font-semibold text-[#03ffe6]" style={{ fontFamily: "'Heebo', sans-serif" }}>
            {INSIGHT_LABELS_HE[key] || key}
          </p>
          <p className="text-sm text-white leading-relaxed whitespace-pre-line" style={{ fontFamily: "'Heebo', sans-serif" }}>
            {formatted}
          </p>
        </div>
      ))}
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
    <div className="flex items-center gap-6 pe-2">
      <div className="w-8 h-8 rounded-lg bg-[rgba(3,255,230,0.2)] flex items-center justify-center text-[#03ffe6]">
        {icon}
      </div>
      <div className="flex flex-col items-end flex-1">
        <span className="text-2xl font-semibold text-[#03ffe6]" style={{ fontFamily: "'Heebo', sans-serif" }}>{count}</span>
        <span className="text-xs text-[rgba(255,255,255,0.33)]" style={{ fontFamily: "'Heebo', sans-serif" }}>{label}</span>
      </div>
    </div>
  );
}
