import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Brain, Heart, MessageSquare, Zap, Target, Repeat, User, Sparkles, Award } from 'lucide-react';
import { apiClient } from '../../services/api';

interface CognitiveData {
  topic?: string;
  // V2 fields
  emotions?: string[];
  thought?: string;
  action_actual?: string;
  action_desired?: string;
  emotion_desired?: string;  // ✨ NEW
  thought_desired?: string;  // ✨ NEW
  gap_name?: string;
  gap_score?: number;
  pattern?: string;
  // V1 fields (backwards compatibility)
  event_actual?: {
    emotions_list?: string[];
    thought_content?: string;
    action_content?: string;
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

interface InsightsPanelProps {
  conversationId: number;
  currentPhase: string;
}

export const InsightsPanel = ({ conversationId, currentPhase }: InsightsPanelProps) => {
  const [insights, setInsights] = useState<CognitiveData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;
    
    const fetchInsights = async () => {
      try {
        const data = await apiClient.getConversationInsights(conversationId);
        
        // Check if conversation exists
        if (data.exists === false) {
          console.warn(`[InsightsPanel] Conversation ${conversationId} doesn't exist, stopping polling`);
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
        // Don't stop polling on transient errors, but show empty state
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
        <p className="text-sm text-primary-dark mt-2">טוען תובנות...</p>
      </div>
    );
  }

  if (!insights || Object.keys(insights).length === 0) {
    return (
      <div className="p-4 text-center opacity-50">
        <Brain size={32} className="text-accent mx-auto mb-2" />
        <p className="text-sm text-primary-dark">התובנות יופיעו כאן במהלך השיחה</p>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-3 overflow-y-auto custom-scrollbar">
      {/* Topic (S1) */}
      {insights.topic && (
        <InsightCard
          icon={<Target size={16} />}
          title="נושא האימון"
          content={insights.topic}
          stage="S1"
          currentStage={currentPhase}
        />
      )}

      {/* Emotions (S3) */}
      {insights.event_actual?.emotions_list && insights.event_actual.emotions_list.length > 0 && (
        <InsightCard
          icon={<Heart size={16} />}
          title="רגשות"
          content={
            <div className="flex flex-wrap gap-1">
              {insights.event_actual.emotions_list.map((emotion, idx) => (
                <span
                  key={idx}
                  className="px-2 py-1 bg-accent/10 text-accent text-xs rounded-full"
                >
                  {emotion}
                </span>
              ))}
            </div>
          }
          stage="S3"
          currentStage={currentPhase}
        />
      )}

      {/* Thought (S4) */}
      {insights.event_actual?.thought_content && (
        <InsightCard
          icon={<MessageSquare size={16} />}
          title="מחשבה"
          content={`"${insights.event_actual.thought_content}"`}
          stage="S4"
          currentStage={currentPhase}
        />
      )}

      {/* Action (S5) */}
      {insights.event_actual?.action_content && (
        <InsightCard
          icon={<Zap size={16} />}
          title="פעולה"
          content={insights.event_actual.action_content}
          stage="S5"
          currentStage={currentPhase}
        />
      )}
      
      {/* Action Actual (S5) - V2 */}
      {insights.action_actual && (
        <InsightCard
          icon={<Zap size={16} />}
          title="פעולה (מצוי)"
          content={insights.action_actual}
          stage="S5"
          currentStage={currentPhase}
        />
      )}
      
      {/* === רצוי (Desired) === */}
      
      {/* Action Desired (S5) */}
      {insights.action_desired && (
        <InsightCard
          icon={<Zap size={16} className="text-green-600" />}
          title="פעולה רצויה"
          content={insights.action_desired}
          stage="S5"
          currentStage={currentPhase}
        />
      )}
      
      {/* Emotion Desired (S5) */}
      {insights.emotion_desired && (
        <InsightCard
          icon={<Heart size={16} className="text-green-600" />}
          title="רגש רצוי"
          content={insights.emotion_desired}
          stage="S5"
          currentStage={currentPhase}
        />
      )}
      
      {/* Thought Desired (S5) */}
      {insights.thought_desired && (
        <InsightCard
          icon={<MessageSquare size={16} className="text-green-600" />}
          title="מחשבה רצויה"
          content={`"${insights.thought_desired}"`}
          stage="S5"
          currentStage={currentPhase}
        />
      )}

      {/* Gap (S6) */}
      {insights.gap_analysis?.name && (
        <InsightCard
          icon={<Target size={16} />}
          title="הפער"
          content={
            <div>
              <p className="font-medium">{insights.gap_analysis.name}</p>
              {insights.gap_analysis.score && (
                <div className="mt-1 flex items-center gap-2">
                  <div className="flex-1 h-2 bg-primary-light/30 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-accent transition-all duration-300"
                      style={{ width: `${insights.gap_analysis.score * 10}%` }}
                    />
                  </div>
                  <span className="text-xs text-primary-dark">{insights.gap_analysis.score}/10</span>
                </div>
              )}
            </div>
          }
          stage="S6"
          currentStage={currentPhase}
        />
      )}

      {/* Pattern (S7) */}
      {insights.pattern_id?.name && (
        <InsightCard
          icon={<Repeat size={16} />}
          title="דפוס"
          content={
            <div>
              <p className="font-medium">{insights.pattern_id.name}</p>
              {insights.pattern_id.paradigm && (
                <p className="text-xs text-primary-dark mt-1">
                  אמונה: {insights.pattern_id.paradigm}
                </p>
              )}
            </div>
          }
          stage="S7"
          currentStage={currentPhase}
        />
      )}

      {/* Being (S8) */}
      {insights.being_desire?.identity && (
        <InsightCard
          icon={<User size={16} />}
          title="זהות רצויה"
          content={insights.being_desire.identity}
          stage="S8"
          currentStage={currentPhase}
        />
      )}

      {/* KaMaZ Forces (S9) */}
      {(insights.kmz_forces?.source_forces?.length || insights.kmz_forces?.nature_forces?.length) && (
        <InsightCard
          icon={<Sparkles size={16} />}
          title="כוחות"
          content={
            <div className="space-y-2">
              {insights.kmz_forces.source_forces && insights.kmz_forces.source_forces.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-primary-dark mb-1">כוחות מקור:</p>
                  <div className="flex flex-wrap gap-1">
                    {insights.kmz_forces.source_forces.map((force, idx) => (
                      <span key={idx} className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded">
                        {force}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {insights.kmz_forces.nature_forces && insights.kmz_forces.nature_forces.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-primary-dark mb-1">כוחות טבע:</p>
                  <div className="flex flex-wrap gap-1">
                    {insights.kmz_forces.nature_forces.map((force, idx) => (
                      <span key={idx} className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded">
                        {force}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          }
          stage="S9"
          currentStage={currentPhase}
        />
      )}

      {/* Commitment (S10) */}
      {insights.commitment?.difficulty && (
        <InsightCard
          icon={<Award size={16} />}
          title="מחויבות"
          content={
            <div className="space-y-1">
              <p className="text-xs"><span className="font-medium">קושי:</span> {insights.commitment.difficulty}</p>
              {insights.commitment.result && (
                <p className="text-xs"><span className="font-medium">תוצאה:</span> {insights.commitment.result}</p>
              )}
            </div>
          }
          stage="S10"
          currentStage={currentPhase}
        />
      )}
    </div>
  );
};

interface InsightCardProps {
  icon: React.ReactNode;
  title: string;
  content: React.ReactNode;
  stage: string;
  currentStage: string;
}

const InsightCard = ({ icon, title, content, stage, currentStage }: InsightCardProps) => {
  const isActive = currentStage === stage;
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`p-3 rounded-lg border transition-all ${
        isActive
          ? 'bg-accent/10 border-accent shadow-md'
          : 'bg-white/50 border-primary-light/30'
      }`}
    >
      <div className="flex items-start gap-2">
        <div className={`mt-0.5 ${isActive ? 'text-accent' : 'text-primary-dark'}`}>
          {icon}
        </div>
        <div className="flex-1 min-w-0">
          <h3 className={`text-xs font-semibold mb-1 ${isActive ? 'text-accent' : 'text-primary-dark'}`}>
            {title}
          </h3>
          <div className="text-sm text-primary">
            {typeof content === 'string' ? <p>{content}</p> : content}
          </div>
        </div>
      </div>
    </motion.div>
  );
};



