import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { Brain } from 'lucide-react';
import { apiClient } from '../../services/api';
import { ReflectionCard } from './ReflectionCard';
import { GapWidget } from './widgets/GapWidget';
import { PatternWidget } from './widgets/PatternWidget';

interface CognitiveData {
  topic?: string;
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
  const { i18n } = useTranslation();
  const [insights, setInsights] = useState<CognitiveData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;
    
    const fetchInsights = async () => {
      try {
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
  }, [conversationId]);

  if (loading) {
    return (
      <div className="p-4 text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent mx-auto"></div>
        <p className="text-sm text-primary-dark mt-2">
          {i18n.language === 'he' ? 'טוען תובנות...' : 'Loading insights...'}
        </p>
      </div>
    );
  }

  if (!insights || Object.keys(insights).length === 0) {
    return (
      <div className="p-4 text-center opacity-50">
        <Brain size={32} className="text-accent mx-auto mb-2" />
        <p className="text-sm text-primary-dark">
          {i18n.language === 'he' ? 'התובנות יופיעו כאן במהלך השיחה' : 'Insights will appear here during the conversation'}
        </p>
      </div>
    );
  }

  // Build list of insights to display
  const insightItems: InsightItem[] = [];

  // Stage titles mapping (bilingual)
  const stageTitles = {
    'S1': { he: 'נושא האימון', en: 'Coaching Topic' },
    'S3': { he: 'מסך הרגש', en: 'Emotion Screen' },
    'S4': { he: 'מסך המחשבה', en: 'Thought Screen' },
    'S5': { he: 'מסך המעשה (מצוי)', en: 'Action Screen (actual)' },
    'S6': { he: 'הרצוי', en: 'Desired' },
    'S7': { he: 'ניתוח הפער', en: 'Gap Analysis' },
    'S8': { he: 'דפוס ופרדיגמה', en: 'Pattern & Paradigm' },
    'S9': { he: 'בירור הרצון', en: 'Clarify Desire' },
    'S10': { he: 'כמ"ז - כוחות', en: 'KaMaZ - Forces' },
    'S13': { he: 'נוסחת המחויבות', en: 'Commitment Formula' }
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

  // S3: Emotions
  if (insights.event_actual?.emotions_list && insights.event_actual.emotions_list.length > 0) {
    insightItems.push({
      stage: 'S3',
      title: stageTitles['S3'][lang],
      status: currentPhase === 'S3' ? 'draft' : 'final',
      data: { emotions_list: insights.event_actual.emotions_list }
    });
  }

  // S4: Thought
  if (insights.event_actual?.thought_content) {
    insightItems.push({
      stage: 'S4',
      title: stageTitles['S4'][lang],
      status: currentPhase === 'S4' ? 'draft' : 'final',
      data: { thought: insights.event_actual.thought_content }
    });
  }

  // S5: Action
  if (insights.event_actual?.action_content) {
    insightItems.push({
      stage: 'S5',
      title: stageTitles['S5'][lang],
      status: currentPhase === 'S5' ? 'draft' : 'final',
      data: { action: insights.event_actual.action_content }
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

  // S9: Being
  if (insights.being_desire?.identity) {
    insightItems.push({
      stage: 'S9',
      title: stageTitles['S9'][lang],
      status: currentPhase === 'S9' ? 'draft' : 'final',
      data: { identity: insights.being_desire.identity }
    });
  }

  // S10: KaMaZ
  if (insights.kmz_forces?.source_forces?.length || insights.kmz_forces?.nature_forces?.length) {
    insightItems.push({
      stage: 'S10',
      title: stageTitles['S10'][lang],
      status: currentPhase === 'S10' ? 'draft' : 'final',
      data: {
        source_forces: insights.kmz_forces.source_forces || [],
        nature_forces: insights.kmz_forces.nature_forces || []
      }
    });
  }

  // S13: Commitment
  if (insights.commitment?.difficulty) {
    insightItems.push({
      stage: 'S13',
      title: stageTitles['S13'][lang],
      status: currentPhase === 'S13' ? 'draft' : 'final',
      data: {
        difficulty: insights.commitment.difficulty,
        result: insights.commitment.result || ''
      }
    });
  }

  return (
    <div className="p-4 space-y-4 overflow-y-auto custom-scrollbar">
      {insightItems.map((item, index) => (
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
    case 'S1':
      return (
        <div className="text-sm text-primary font-medium">
          {data.topic}
        </div>
      );

    case 'S3':
      return (
        <div className="flex flex-wrap gap-1.5">
          {data.emotions_list.map((emotion: string, idx: number) => (
            <motion.span
              key={idx}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: idx * 0.1 }}
              className="px-2.5 py-1 bg-orange-100 text-orange-700 text-sm rounded-full border border-orange-300 font-medium"
            >
              {emotion}
            </motion.span>
          ))}
        </div>
      );

    case 'S4':
      return (
        <div className="text-sm text-primary italic">
          "{data.thought}"
        </div>
      );

    case 'S5':
      return (
        <div className="text-sm text-primary">
          {data.action}
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

    case 'S13':
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

