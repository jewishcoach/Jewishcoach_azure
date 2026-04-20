import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { Brain } from 'lucide-react';
import { useAuth } from '@clerk/clerk-react';
import { apiClient } from '../../services/api';
import { ReflectionCard } from './ReflectionCard';
import { GapWidget } from './widgets/GapWidget';
import { PatternWidget } from './widgets/PatternWidget';
import { ListWidget } from './widgets/ListWidget';

interface CognitiveData {
  topic?: string;
  /** V2 may mirror these at root as well as under event_actual */
  emotions?: string[];
  thought?: string;
  action_actual?: string;
  event_actual?: {
    emotions_list?: string[];
    thought_content?: string;
    action_content?: string;
    action_desired?: string;
    emotion_desired?: string;
    thought_desired?: string;
  };
  gap_analysis?: {
    name?: string;
    score?: number;
  };
  pattern_id?: {
    name?: string;
    paradigm?: string;
  };
  being_desire?: {
    identity?: string;
  };
  kmz_forces?: {
    source_forces?: string[];
    nature_forces?: string[];
  };
  commitment?: {
    difficulty?: string;
    result?: string;
  };
  shehiya_mission?: {
    title?: string;
    body?: string;
    step?: string;
    station_id?: string;
    assigned_at?: string;
  };
  stance?: {
    reality_belief?: string;
    activation_trigger?: string;
    gains?: string[];
    losses?: string[];
  };
  paradigm?: string;
}

interface InsightItem {
  stage: string;
  title: string;
  status: 'draft' | 'final';
  data: any;
}

interface SmartInsightsPanelProps {
  conversationId: number;
  currentPhase: string;
}

export const SmartInsightsPanel = ({ conversationId, currentPhase }: SmartInsightsPanelProps) => {
  const { t, i18n } = useTranslation();
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [insights, setInsights] = useState<CognitiveData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) {
      setLoading(false);
      return;
    }

    let interval: NodeJS.Timeout | null = null;
    
    const fetchInsights = async () => {
      try {
        const token = await getToken();
        if (token) apiClient.setToken(token);
        const data = await apiClient.getConversationInsights(conversationId);
        
        // Check if conversation exists
        if (data.exists === false) {
          console.warn(`[SmartInsightsPanel] Conversation ${conversationId} doesn't exist, stopping polling`);
          if (interval) {
            clearInterval(interval);
            interval = null;
          }
          setInsights(null);
          setLoading(false);
          return;
        }
        
        setInsights(data.cognitive_data || {});
      } catch (error) {
        console.error('Error fetching insights:', error);
        // Don't stop polling on transient errors
      } finally {
        setLoading(false);
      }
    };

    fetchInsights();
    // Refresh every 3 seconds while conversation is active
    interval = setInterval(fetchInsights, 3000);
    
    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [conversationId, isLoaded, isSignedIn, getToken]);

  if (loading) {
    return (
      <div className="p-4 text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent mx-auto"></div>
        <p className="text-sm text-primary-dark mt-2">{t('chat.insightsLoading')}</p>
      </div>
    );
  }

  if (!insights || Object.keys(insights).length === 0) {
    return (
      <div className="p-4 text-center opacity-50">
        <Brain size={32} className="text-accent mx-auto mb-2" />
        <p className="text-sm text-primary-dark">{t('chat.insightsPlaceholder')}</p>
      </div>
    );
  }

  // Build list of insights to display
  const insightItems: InsightItem[] = [];

  // Stage titles mapping (bilingual)
  const stageTitles = {
    'S1': { he: 'נושא האימון', en: 'Coaching Topic' },
    /** Single card: emotion + thought + action (aligned with S6 "Desired" layout) */
    'MEZUY': { he: 'המצוי', en: 'Actual' },
    'S6': { he: 'הרצוי', en: 'Desired' },
    'S7': { he: 'ניתוח הפער', en: 'Gap Analysis' },
    'S8': { he: 'דפוס', en: 'Pattern' },
    'S9': { he: 'פרדיגמה', en: 'Paradigm' },
    'S10': { he: 'עמדה+טריגר', en: 'Stance & Trigger' },
    'S11': { he: 'טבלת רווח והפסד', en: 'Profit & loss table' },
    'S12': { he: 'כמ"ז - כוחות', en: 'KaMaZ - Forces' },
    'S13': { he: 'בחירה', en: 'Choice' },
    'S14': { he: 'חזון', en: 'Vision' },
    'S15': { he: 'מחויבות', en: 'Commitment' }
  };

  const lang = i18n.language as 'he' | 'en';

  // S1: Topic
  if (insights.topic) {
    insightItems.push({
      stage: 'S1',
      title: stageTitles['S1'][lang],
      status: currentPhase === 'S1' ? 'draft' : 'final',
      data: { topic: insights.topic }
    });
  }

  // S3–S5: המצוי — כרטיס אחד (עיצוב מקביל ל־S6 הרצוי)
  const ea = insights.event_actual;
  const emotionsList =
    ea?.emotions_list?.length ? ea.emotions_list : (insights.emotions?.length ? insights.emotions : []);
  const thoughtActual = (ea?.thought_content ?? insights.thought ?? '').trim();
  const actionActual = (ea?.action_content ?? insights.action_actual ?? '').trim();
  const hasMezuy =
    emotionsList.length > 0 || Boolean(thoughtActual) || Boolean(actionActual);
  if (hasMezuy) {
    const inMezuyStages = currentPhase === 'S3' || currentPhase === 'S4' || currentPhase === 'S5';
    insightItems.push({
      stage: 'MEZUY',
      title: stageTitles['MEZUY'][lang],
      status: inMezuyStages ? 'draft' : 'final',
      data: {
        emotions_list: emotionsList,
        thought: thoughtActual,
        action: actionActual,
      },
    });
  }

  // S6: Desired
  if (insights.event_actual?.action_desired || insights.event_actual?.emotion_desired || insights.event_actual?.thought_desired) {
    insightItems.push({
      stage: 'S6',
      title: stageTitles['S6'][lang],
      status: currentPhase === 'S6' ? 'draft' : 'final',
      data: {
        action_desired: insights.event_actual?.action_desired,
        emotion_desired: insights.event_actual?.emotion_desired,
        thought_desired: insights.event_actual?.thought_desired
      }
    });
  }

  // S7: Gap
  if (insights.gap_analysis?.name) {
    insightItems.push({
      stage: 'S7',
      title: stageTitles['S7'][lang],
      status: currentPhase === 'S7' ? 'draft' : 'final',
      data: {
        current_reality: lang === 'he' ? `פער: ${insights.gap_analysis.name}` : `Gap: ${insights.gap_analysis.name}`,
        desired_reality: lang === 'he' ? `ציון: ${insights.gap_analysis.score || 0}/10` : `Score: ${insights.gap_analysis.score || 0}/10`,
        gap_name: insights.gap_analysis.name,
        gap_score: insights.gap_analysis.score
      }
    });
  }

  // S8: Pattern
  if (insights.pattern_id?.name) {
    insightItems.push({
      stage: 'S8',
      title: stageTitles['S8'][lang],
      status: currentPhase === 'S8' ? 'draft' : 'final',
      data: {
        trigger: insights.pattern_id.name || '',
        reaction: lang === 'he' ? 'תגובה חוזרת' : 'Recurring reaction',
        consequence: insights.pattern_id.paradigm || ''
      }
    });
  }

  // S9: Paradigm (פרדיגמה) — prefer explicit paradigm from cognitive_data
  if (insights.paradigm?.trim()) {
    insightItems.push({
      stage: 'S9',
      title: stageTitles['S9'][lang],
      status: currentPhase === 'S9' ? 'draft' : 'final',
      data: { identity: insights.paradigm.trim() },
    });
  } else if (insights.being_desire?.identity) {
    insightItems.push({
      stage: 'S9',
      title: stageTitles['S9'][lang],
      status: currentPhase === 'S9' ? 'draft' : 'final',
      data: { identity: insights.being_desire.identity },
    });
  }

  // S10: עמדה (תפיסת מציאות + טריגר)
  const rb = insights.stance?.reality_belief?.trim();
  const trig = insights.stance?.activation_trigger?.trim();
  if (rb || trig) {
    insightItems.push({
      stage: 'S10',
      title: stageTitles['S10'][lang],
      status: currentPhase === 'S10' ? 'draft' : 'final',
      data: { reality_belief: rb || '', activation_trigger: trig || '' },
    });
  }

  // S11: טבלת רווח והפסד
  const sg = insights.stance?.gains ?? [];
  const sl = insights.stance?.losses ?? [];
  if (sg.length > 0 || sl.length > 0) {
    insightItems.push({
      stage: 'S11',
      title: stageTitles['S11'][lang],
      status: currentPhase === 'S11' ? 'draft' : 'final',
      data: { gains: sg, losses: sl },
    });
  }

  // S12: KaMaZ
  if (insights.kmz_forces?.source_forces?.length || insights.kmz_forces?.nature_forces?.length) {
    insightItems.push({
      stage: 'S12',
      title: stageTitles['S12'][lang],
      status: currentPhase === 'S12' ? 'draft' : 'final',
      data: {
        source_forces: insights.kmz_forces.source_forces || [],
        nature_forces: insights.kmz_forces.nature_forces || []
      }
    });
  }

  // S15: Commitment
  if (insights.commitment?.difficulty) {
    insightItems.push({
      stage: 'S15',
      title: stageTitles['S15'][lang],
      status: currentPhase === 'S15' ? 'draft' : 'final',
      data: {
        difficulty: insights.commitment.difficulty,
        result: insights.commitment.result || ''
      }
    });
  }

  const shehiyaItems: InsightItem[] = [];
  if (insights.shehiya_mission?.title || insights.shehiya_mission?.body) {
    shehiyaItems.push({
      stage: 'SHEHIYA',
      title: lang === 'he' ? 'משימת השהיה' : 'Between-session mission',
      status: 'draft',
      data: { ...insights.shehiya_mission },
    });
  }

  const orderedItems = [...shehiyaItems, ...insightItems];

  return (
    <div className="p-4 space-y-4 overflow-y-auto custom-scrollbar">
      {orderedItems.map((item, index) => (
        <ReflectionCard
          key={`${item.stage}-${index}`}
          status={item.status}
          title={item.title}
          language={lang}
        >
          {renderWidgetContent(item.stage, item.data, lang)}
        </ReflectionCard>
      ))}
    </div>
  );
};

// Helper function to render the appropriate widget for each stage
function renderWidgetContent(stage: string, data: any, language: 'he' | 'en') {
  switch (stage) {
    case 'SHEHIYA':
      return (
        <div className="space-y-2 text-sm text-primary">
          {data.title ? (
            <div className="font-semibold text-primary-dark leading-snug">{data.title}</div>
          ) : null}
          {data.body ? (
            <p className="leading-relaxed whitespace-pre-wrap">{data.body}</p>
          ) : null}
        </div>
      );

    case 'S1':
      return (
        <div className="text-sm text-primary font-medium">
          {data.topic}
        </div>
      );

    case 'MEZUY':
      return (
        <div className="space-y-2 text-sm">
          {data.emotions_list?.length > 0 && (
            <div>
              <span className="font-semibold">
                {language === 'he' ? 'רגש (מצוי):' : 'Emotion (actual):'}
              </span>{' '}
              <span className="inline-flex flex-wrap gap-1.5 align-middle">
                {data.emotions_list.map((emotion: string, idx: number) => (
                  <motion.span
                    key={idx}
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: idx * 0.06 }}
                    className="px-2.5 py-1 bg-orange-100 text-orange-700 text-xs rounded-full border border-orange-300 font-medium"
                  >
                    {emotion}
                  </motion.span>
                ))}
              </span>
            </div>
          )}
          {data.thought ? (
            <div>
              <span className="font-semibold">
                {language === 'he' ? 'מחשבה (מצוי):' : 'Thought (actual):'}
              </span>{' '}
              <span className="text-primary italic">"{data.thought}"</span>
            </div>
          ) : null}
          {data.action ? (
            <div>
              <span className="font-semibold">
                {language === 'he' ? 'מעשה (מצוי):' : 'Action (actual):'}
              </span>{' '}
              <span className="text-primary">{data.action}</span>
            </div>
          ) : null}
        </div>
      );

    case 'S6':
      return (
        <div className="space-y-2 text-sm">
          {data.action_desired && (
            <div><span className="font-semibold">{language === 'he' ? 'מעשה רצוי:' : 'Desired action:'}</span> {data.action_desired}</div>
          )}
          {data.emotion_desired && (
            <div><span className="font-semibold">{language === 'he' ? 'רגש רצוי:' : 'Desired emotion:'}</span> {data.emotion_desired}</div>
          )}
          {data.thought_desired && (
            <div><span className="font-semibold">{language === 'he' ? 'מחשבה רצויה:' : 'Desired thought:'}</span> {data.thought_desired}</div>
          )}
        </div>
      );

    case 'S7':
      return <GapWidget data={data} language={language} />;

    case 'S8':
      return <PatternWidget data={data} language={language} />;

    case 'S9':
      return (
        <div className="text-sm text-primary font-medium">
          {data.identity}
        </div>
      );

    case 'S10':
      return (
        <div className="space-y-2 text-sm text-primary">
          {data.reality_belief ? (
            <div>
              <span className="font-semibold text-primary-dark">
                {language === 'he' ? 'תפיסת מציאות:' : 'Reality belief:'}
              </span>{' '}
              <span className="italic">"{data.reality_belief}"</span>
            </div>
          ) : null}
          {data.activation_trigger ? (
            <div>
              <span className="font-semibold text-primary-dark">
                {language === 'he' ? 'טריגר:' : 'Trigger:'}
              </span>{' '}
              <span>{data.activation_trigger}</span>
            </div>
          ) : null}
        </div>
      );

    case 'S11':
      return (
        <ListWidget
          data={{ gains: data.gains || [], losses: data.losses || [] }}
          stage="Stance"
          language={language}
        />
      );

    case 'S12':
      return (
        <div className="space-y-3">
          {data.source_forces && data.source_forces.length > 0 && (
            <div>
              <div className="text-xs font-semibold text-blue-700 mb-1.5">
                {language === 'he' ? 'כוחות מקור:' : 'Source Forces:'}
              </div>
              <div className="flex flex-wrap gap-1.5">
                {data.source_forces.map((force: string, idx: number) => (
                  <span key={idx} className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded">
                    {force}
                  </span>
                ))}
              </div>
            </div>
          )}
          {data.nature_forces && data.nature_forces.length > 0 && (
            <div>
              <div className="text-xs font-semibold text-green-700 mb-1.5">
                {language === 'he' ? 'כוחות טבע:' : 'Nature Forces:'}
              </div>
              <div className="flex flex-wrap gap-1.5">
                {data.nature_forces.map((force: string, idx: number) => (
                  <span key={idx} className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded">
                    {force}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      );

    case 'S15':
      return (
        <div className="space-y-2 text-sm">
          <div>
            <span className="font-semibold text-primary-dark">
              {language === 'he' ? 'קושי:' : 'Difficulty:'}
            </span>{' '}
            <span className="text-primary">{data.difficulty}</span>
          </div>
          {data.result && (
            <div>
              <span className="font-semibold text-primary-dark">
                {language === 'he' ? 'תוצאה:' : 'Result:'}
              </span>{' '}
              <span className="text-primary">{data.result}</span>
            </div>
          )}
        </div>
      );

    default:
      return (
        <div className="text-sm text-gray-500 italic">
          {language === 'he' ? 'אין תצוגה מוגדרת' : 'No display defined'}
        </div>
      );
  }
}

