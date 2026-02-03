import { motion } from 'framer-motion';
import { Square, User, UserCircle2 } from 'lucide-react';
import { useState, useEffect } from 'react';
import { useContinuousChat } from '../hooks/useContinuousChat';
import { COACH_VOICES, type VoiceGender } from '../constants/voices';

interface Props {
  language: 'he' | 'en';
  voiceGender: VoiceGender;
  onVoiceGenderChange: (gender: VoiceGender) => void;
  onMessageSync: (role: 'user' | 'assistant', content: string) => Promise<void>;
  onAIResponseReady: (speakFn: (text: string) => Promise<void>) => void;
  onStopSessionReady: (stopFn: () => void) => void;
  onStop: () => void;
}

export const VoiceControlBar = ({
  language,
  voiceGender,
  onVoiceGenderChange,
  onMessageSync,
  onAIResponseReady,
  onStopSessionReady,
  onStop
}: Props) => {
  const [partialTranscript, setPartialTranscript] = useState('');
  const [error, setError] = useState<string | null>(null);
  
  const { isListening, isSpeaking, startSession, stopSession, speakAndContinue } = useContinuousChat({
    language,
    voiceGender,
    onMessageSync,
    onPartialTranscript: setPartialTranscript,
    onError: setError
  });

  // Expose speak function to parent
  useEffect(() => {
    onAIResponseReady(speakAndContinue);
  }, [speakAndContinue, onAIResponseReady]);

  // Expose stopSession function to parent
  useEffect(() => {
    onStopSessionReady(stopSession);
  }, [stopSession, onStopSessionReady]);

  // Auto-start session on mount and cleanup on unmount
  useEffect(() => {
    console.log('🎤 VoiceControlBar mounted - starting session');
    startSession();
    
    return () => {
      console.log('🎤 VoiceControlBar unmounting - cleaning up');
      stopSession();
    };
  }, [startSession, stopSession]);

  const currentVoice = COACH_VOICES[language][voiceGender];

  const handleStop = () => {
    stopSession();
    onStop();
  };

  return (
    <motion.div
      initial={{ y: 100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      exit={{ y: 100, opacity: 0 }}
      transition={{ type: 'spring', damping: 25, stiffness: 300 }}
      className="w-full bg-gradient-to-r from-primary via-primary-light to-primary-dark shadow-2xl border-t-4 border-accent"
    >
      <div className="px-6 py-4">
        {/* Top Row: Status & Voice Toggle */}
        <div className="flex items-center justify-between mb-3">
          {/* Left: Pulsing Indicator */}
          <div className="flex items-center gap-3">
            <motion.div
              animate={{
                scale: isListening ? [1, 1.3, 1] : isSpeaking ? [1, 1.2, 1] : 1,
                opacity: isListening ? [0.6, 1, 0.6] : isSpeaking ? [0.7, 1, 0.7] : 0.5
              }}
              transition={{
                duration: isListening ? 1.2 : isSpeaking ? 1.5 : 0,
                repeat: (isListening || isSpeaking) ? Infinity : 0,
                ease: 'easeInOut'
              }}
              className={`w-4 h-4 rounded-full ${
                isListening 
                  ? 'bg-accent shadow-glow' 
                  : isSpeaking 
                  ? 'bg-blue-400 shadow-[0_0_20px_rgba(59,130,246,0.6)]'
                  : 'bg-gray-500'
              }`}
            />
            <span className="text-cream text-sm font-medium">
              {isListening 
                ? (language === 'he' ? 'מקשיב...' : 'Listening...') 
                : isSpeaking 
                ? (language === 'he' ? 'מדבר...' : 'Speaking...') 
                : currentVoice.label}
            </span>
          </div>

          {/* Right: Voice Gender Toggle & Stop Button */}
          <div className="flex items-center gap-2">
            {/* Voice Gender Buttons */}
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onVoiceGenderChange('male');
              }}
              className={`p-2 rounded-lg transition-all ${
                voiceGender === 'male'
                  ? 'bg-accent text-white shadow-glow'
                  : 'bg-white/10 text-cream/70 hover:bg-white/20'
              }`}
              title={COACH_VOICES[language].male.name}
            >
              <User size={16} />
            </button>
            
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onVoiceGenderChange('female');
              }}
              className={`p-2 rounded-lg transition-all ${
                voiceGender === 'female'
                  ? 'bg-accent text-white shadow-glow'
                  : 'bg-white/10 text-cream/70 hover:bg-white/20'
              }`}
              title={COACH_VOICES[language].female.name}
            >
              <UserCircle2 size={16} />
            </button>

            {/* Stop Button */}
            <motion.button
              type="button"
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              onClick={handleStop}
              className="p-2 rounded-lg bg-red-500/20 text-red-300 hover:bg-red-500/40 transition-colors"
              title={language === 'he' ? 'עצור שיחה קולית' : 'Stop Voice Chat'}
            >
              <Square size={20} />
            </motion.button>
          </div>
        </div>

        {/* Bottom Row: Live Transcript or Status */}
        {partialTranscript ? (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="bg-white/10 backdrop-blur-sm rounded-lg px-4 py-2"
          >
            <p 
              className="text-cream text-sm" 
              dir={language === 'he' ? 'rtl' : 'ltr'}
            >
              {partialTranscript}
            </p>
          </motion.div>
        ) : (
          <div className="text-center">
            <p className="text-cream/60 text-xs">
              {language === 'he' 
                ? 'התחל לדבר או לחץ על הריבוע כדי לעצור'
                : 'Start speaking or click square to stop'}
            </p>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-2 p-2 bg-red-500/20 border border-red-500/50 rounded-lg text-red-300 text-xs text-center"
          >
            {error}
          </motion.div>
        )}
      </div>
    </motion.div>
  );
};

