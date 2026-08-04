import { Heart, Lightbulb, Sparkles } from 'lucide-react';
import { MACRO_STAGES } from '../types';

interface JourneySidebarProps {
  currentMacroStage: string;
  language: string;
}

export function JourneySidebar({ currentMacroStage, language }: JourneySidebarProps) {
  const isHe = language.startsWith('he');
  const currentIdx = MACRO_STAGES.findIndex((s) => s.id === currentMacroStage);

  return (
    <>
      {/* Desktop sidebar — dark background, right side (start in RTL) */}
      <aside className="w-[280px] bg-slate-700 hidden lg:flex lg:flex-col flex-shrink-0 order-first">
        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-6">
          {/* Section title */}
          <h3 className="text-sm font-bold text-teal-300">
            {isHe ? 'איפה אני במסע' : 'Where am I'}
          </h3>

          {/* Stage list */}
          <div className="space-y-5">
            {MACRO_STAGES.map((stage, idx) => {
              const isActive = idx === currentIdx;
              const isCompleted = idx < currentIdx;
              const isFuture = idx > currentIdx;

              return (
                <div key={stage.id} className="flex items-start gap-3">
                  {/* Stage text (right side in RTL) */}
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm font-semibold ${isActive || isCompleted ? 'text-white' : 'text-gray-400'}`}>
                      {isHe ? stage.title_he : stage.title_en}
                    </p>
                    <p className={`text-xs mt-0.5 ${isActive || isCompleted ? 'text-gray-300' : 'text-gray-500'}`}>
                      {isHe ? stage.description_he : stage.description_en}
                    </p>
                  </div>

                  {/* Circle (left side in RTL = end) */}
                  <div
                    className={`
                      w-7 h-7 rounded-full flex-shrink-0 mt-0.5
                      ${isCompleted ? 'bg-teal-400' : ''}
                      ${isActive ? 'bg-teal-400 ring-4 ring-teal-400/30' : ''}
                      ${isFuture ? 'border-2 border-slate-400 bg-slate-600' : ''}
                    `}
                  />
                </div>
              );
            })}
          </div>

          {/* Divider */}
          <div className="border-t border-slate-600" />

          {/* Discovery counters */}
          <div className="space-y-4">
            <h3 className="text-sm font-bold text-teal-300">
              {isHe ? 'מה שגיליתי בדרך' : 'What I discovered'}
            </h3>
            <DiscoveryCounter icon={<Lightbulb size={16} />} count={0} label={isHe ? 'תובנות שהתגלו' : 'Insights'} />
            <DiscoveryCounter icon={<Sparkles size={16} />} count={0} label={isHe ? 'דפוסים שזיהיתי' : 'Patterns'} />
            <DiscoveryCounter icon={<Heart size={16} />} count={0} label={isHe ? 'החלטות שקיבלתי' : 'Decisions'} />
          </div>
        </div>
      </aside>

      {/* Mobile bottom bar */}
      <div className="fixed bottom-0 inset-x-0 lg:hidden bg-slate-800/95 backdrop-blur-sm border-t border-slate-700 z-10">
        <div className="flex items-center justify-center gap-3 py-2.5 px-4">
          {MACRO_STAGES.map((stage, idx) => {
            const isActive = idx === currentIdx;
            const isCompleted = idx < currentIdx;

            return (
              <div key={stage.id} className="flex flex-col items-center gap-1">
                <div
                  className={`
                    w-3 h-3 rounded-full transition-all duration-300
                    ${isCompleted ? 'bg-teal-400' : ''}
                    ${isActive ? 'bg-teal-400 ring-2 ring-teal-400/40 scale-125' : ''}
                    ${!isActive && !isCompleted ? 'bg-slate-500' : ''}
                  `}
                />
                {isActive && (
                  <span className="text-[10px] text-teal-300 font-medium">
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

function DiscoveryCounter({ icon, count, label }: { icon: React.ReactNode; count: number; label: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-gray-400">{label}</span>
      <div className="flex items-center gap-2">
        <span className="text-lg font-bold text-teal-300">{count}</span>
        <div className="w-7 h-7 rounded-lg bg-teal-600/30 flex items-center justify-center text-teal-300">
          {icon}
        </div>
      </div>
    </div>
  );
}
