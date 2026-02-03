import { motion, AnimatePresence } from 'framer-motion';
import { X, User, UserCircle2 } from 'lucide-react';
import { useState, useEffect } from 'react';
import { useContinuousChat } from '../hooks/useContinuousChat';
import { COACH_VOICES, type VoiceGender } from '../constants/voices';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  language: 'he' | 'en';
  voiceGender: VoiceGender;
  onVoiceGenderChange: (gender: VoiceGender) => void;
  onMessageSync: (role: 'user' | 'assistant', content: string) => Promise<void>;
  onAIResponseReady: (speakFn: (text: string) => Promise<void>) => void;
}

export const VoiceConversationModal = ({
  isOpen,
  onClose,
  language,
  voiceGender,
  onVoiceGenderChange,
  onMessageSync,
  onAIResponseReady
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

  // Auto-start session when modal opens
  useEffect(() => {
    if (isOpen) {
      startSession();
    } else {
      stopSession();
    }
    
    return () => stopSession();
  }, [isOpen, startSession, stopSession]);

  if (!isOpen) return null;

  const currentVoice = COACH_VOICES[language][voiceGender];
  
  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-md"
        onClick={(e) => {
          // Only close if clicking directly on the backdrop
          if (e.target === e.currentTarget) {
            onClose();
          }
        }}
      >
        <motion.div
          initial={{ scale: 0.9, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.9, y: 20 }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          className="relative bg-gradient-to-br from-primary via-primary-light to-primary-dark rounded-3xl shadow-2xl p-12 max-w-2xl w-full mx-4"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Close Button */}
          <motion.button
            type="button"
            whileHover={{ scale: 1.1, rotate: 90 }}
            whileTap={{ scale: 0.9 }}
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onClose();
            }}
            className="absolute top-4 right-4 p-2 rounded-full bg-red-500/20 text-red-300 hover:bg-red-500/40 transition-colors"
          >
            <X size={24} />
          </motion.button>

          {/* Voice Visualizer Orb */}
          <div className="flex justify-center mb-8">
            <motion.div
              animate={{
                scale: isListening ? [1, 1.2, 1] : isSpeaking ? [1, 1.1, 1] : 1,
                opacity: isListening ? [0.8, 1, 0.8] : isSpeaking ? [0.9, 1, 0.9] : 0.7
              }}
              transition={{
                duration: isListening ? 1.5 : isSpeaking ? 2 : 0,
                repeat: (isListening || isSpeaking) ? Infinity : 0,
                ease: 'easeInOut'
              }}
              className={`w-48 h-48 rounded-full flex items-center justify-center ${
                isListening 
                  ? 'bg-gradient-to-br from-accent to-accent-dark shadow-glow' 
                  : isSpeaking 
                  ? 'bg-gradient-to-br from-blue-400 to-blue-600 shadow-[0_0_40px_rgba(59,130,246,0.6)]'
                  : 'bg-gradient-to-br from-gray-600 to-gray-800'
              }`}
            >
              <motion.div
                animate={{ rotate: isSpeaking ? 360 : 0 }}
                transition={{ duration: 2, repeat: isSpeaking ? Infinity : 0, ease: 'linear' }}
              >
                <User size={80} className="text-white" />
              </motion.div>
            </motion.div>
          </div>

          {/* Status Text */}
          <div className="text-center mb-6">
            <h3 className="text-2xl font-serif font-bold text-cream mb-2">
              {isListening ? (language === 'he' ? 'מקשיב...' : 'Listening...') 
                : isSpeaking ? (language === 'he' ? 'מדבר...' : 'Speaking...') 
                : (language === 'he' ? 'מוכן' : 'Ready')}
            </h3>
            <p className="text-cream/70">
              {currentVoice.label}
            </p>
          </div>

          {/* Live Captions */}
          <AnimatePresence>
            {partialTranscript && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="bg-white/10 backdrop-blur-sm rounded-xl px-6 py-4 mb-6 text-center"
              >
                <p className="text-cream text-lg" dir={language === 'he' ? 'rtl' : 'ltr'}>
                  {partialTranscript}
                </p>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Voice Gender Toggle */}
          <div className="flex justify-center gap-4">
            <motion.button
              type="button"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onVoiceGenderChange('male');
              }}
              className={`px-6 py-3 rounded-xl flex items-center gap-2 transition-all ${
                voiceGender === 'male'
                  ? 'bg-accent text-white shadow-glow'
                  : 'bg-white/10 text-cream/70 hover:bg-white/20'
              }`}
            >
              <User size={20} />
              <span>{COACH_VOICES[language].male.name}</span>
            </motion.button>
            
            <motion.button
              type="button"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onVoiceGenderChange('female');
              }}
              className={`px-6 py-3 rounded-xl flex items-center gap-2 transition-all ${
                voiceGender === 'female'
                  ? 'bg-accent text-white shadow-glow'
                  : 'bg-white/10 text-cream/70 hover:bg-white/20'
              }`}
            >
              <UserCircle2 size={20} />
              <span>{COACH_VOICES[language].female.name}</span>
            </motion.button>
          </div>

          {/* Error Display */}
          {error && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mt-4 p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-300 text-center text-sm"
            >
              {error}
            </motion.div>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

