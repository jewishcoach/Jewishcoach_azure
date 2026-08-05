import { Heart, Lightbulb, Sparkles } from 'lucide-react';
import { MACRO_STAGES } from '../types';
import { useState } from 'react';

interface JourneySidebarProps {
  currentMacroStage: string;
  language: string;
}

export function JourneySidebar({ currentMacroStage, language }: JourneySidebarProps) {
  const isHe = language.startsWith('he');
  const currentIdx = MACRO_STAGES.findIndex((s) => s.id === currentMacroStage);
  const [activeTab, setActiveTab] = useState<'journey' | 'insights'>('journey');

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="w-[330px] bg-[#3c5465] hidden lg:flex lg:flex-col flex-shrink-0 order-first">
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
            <span>{isHe ? 'התובנות שלי (7)' : 'My Insights (7)'}</span>
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
              <div className="space-y-6">
                {MACRO_STAGES.map((stage, idx) => {
                  const isActive = idx === currentIdx;
                  const isCompleted = idx < currentIdx;
                  const isFuture = idx > currentIdx;

                  return (
                    <div
                      key={stage.id}
                      className={`flex items-center gap-6 justify-end pe-7 ${isFuture ? 'opacity-50' : ''}`}
                    >
                      {/* Stage text */}
                      <div className="flex-1 min-w-0 text-end">
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

                      {/* Circle */}
                      <div
                        className={`
                          w-6 h-6 rounded-full flex-shrink-0
                          ${isCompleted ? 'bg-[#03ffe6]' : ''}
                          ${isActive ? 'bg-[#03ffe6] ring-4 ring-[#01897b]' : ''}
                          ${isFuture ? 'bg-[#03ffe6]' : ''}
                        `}
                      />
                    </div>
                  );
                })}
              </div>
            </>
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

function DiscoveryCounter({ icon, count, label }: { icon: React.ReactNode; count: number; label: string }) {
  return (
    <div className="flex items-center justify-end gap-6 pe-2">
      <div className="flex flex-col items-end">
        <span className="text-2xl font-semibold text-[#03ffe6]" style={{ fontFamily: "'Heebo', sans-serif" }}>{count}</span>
        <span className="text-xs text-[rgba(255,255,255,0.33)]" style={{ fontFamily: "'Heebo', sans-serif" }}>{label}</span>
      </div>
      <div className="w-8 h-8 rounded-lg bg-[rgba(3,255,230,0.2)] flex items-center justify-center text-[#03ffe6]">
        {icon}
      </div>
    </div>
  );
}
