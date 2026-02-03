import { useState, useRef, useCallback } from 'react';
import * as sdk from 'microsoft-cognitiveservices-speech-sdk';
import { COACH_VOICES, type VoiceGender, type VoiceLanguage } from '../constants/voices';
import axios from 'axios';

interface UseContinuousChatProps {
  language: VoiceLanguage;
  voiceGender: VoiceGender;
  onMessageSync: (role: 'user' | 'assistant', content: string) => Promise<void>;
  onPartialTranscript?: (text: string) => void;
  onError?: (error: string) => void;
}

export const useContinuousChat = ({
  language,
  voiceGender,
  onMessageSync,
  onPartialTranscript,
  onError
}: UseContinuousChatProps) => {
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isActive, setIsActive] = useState(false);
  
  const recognizerRef = useRef<sdk.SpeechRecognizer | null>(null);
  const synthesizerRef = useRef<sdk.SpeechSynthesizer | null>(null);
  const shouldContinueRef = useRef(true);
  const lastProcessedTextRef = useRef<string>(''); // Track last processed text to prevent duplicates
  const isProcessingRef = useRef(false); // Prevent concurrent processing

  // Get Azure Speech token
  const getToken = async () => {
    const response = await axios.get('http://localhost:8000/api/speech/token');
    return response.data;
  };

  // Initialize recognizer
  const initRecognizer = useCallback(async () => {
    // Close any existing recognizer before creating a new one to prevent duplicates
    if (recognizerRef.current) {
      console.log('🔄 Closing existing recognizer before creating new one');
      try {
        recognizerRef.current.stopContinuousRecognitionAsync();
        recognizerRef.current.close();
      } catch (err) {
        console.warn('⚠️ Error closing old recognizer:', err);
      }
      recognizerRef.current = null;
    }
    
    const { token, region } = await getToken();
    const speechConfig = sdk.SpeechConfig.fromAuthorizationToken(token, region);
    speechConfig.speechRecognitionLanguage = language === 'he' ? 'he-IL' : 'en-US';
    
    const audioConfig = sdk.AudioConfig.fromDefaultMicrophoneInput();
    const recognizer = new sdk.SpeechRecognizer(speechConfig, audioConfig);

    // Live transcription (partial)
    recognizer.recognizing = (_s, e) => {
      // Only show partial transcript if session is still active
      if (e.result.text && onPartialTranscript && shouldContinueRef.current) {
        onPartialTranscript(e.result.text);
      }
    };

    // Final transcription
    recognizer.recognized = async (_s, e) => {
      if (e.result.reason === sdk.ResultReason.RecognizedSpeech && e.result.text) {
        const recognizedText = e.result.text.trim();
        
        // Check if session is still active before processing
        if (!shouldContinueRef.current) {
          console.log('⚠️ Recognition received but session stopped, ignoring');
          return;
        }
        
        // CRITICAL: Prevent duplicate processing of the same text
        if (isProcessingRef.current) {
          console.log('⚠️ Already processing a message, skipping duplicate');
          return;
        }
        
        if (lastProcessedTextRef.current === recognizedText) {
          console.log('⚠️ Duplicate recognition detected, ignoring:', recognizedText.substring(0, 30));
          return;
        }
        
        // Mark as processing and store the text
        isProcessingRef.current = true;
        lastProcessedTextRef.current = recognizedText;
        console.log('🎤 Processing new user message:', recognizedText.substring(0, 50));
        
        setIsListening(false);
        
        // Clear partial transcript
        if (onPartialTranscript) {
          onPartialTranscript('');
        }
        
        // Stop recognizer BEFORE sending message (to prevent overlap)
        recognizer.stopContinuousRecognitionAsync();
        
        try {
          // Send user message to UI and DB
          await onMessageSync('user', recognizedText);
        } finally {
          // Reset processing flag after a short delay
          setTimeout(() => {
            isProcessingRef.current = false;
          }, 500);
        }
      }
    };

    recognizer.canceled = (_s, e) => {
      if (e.reason === sdk.CancellationReason.Error) {
        onError?.(e.errorDetails);
      }
    };

    recognizerRef.current = recognizer;
    return recognizer;
  }, [language, onMessageSync, onPartialTranscript, onError]);

  // Speak AI response and auto-restart listening
  const speakAndContinue = useCallback(async (text: string) => {
    if (!shouldContinueRef.current) return;
    
    // Stop any existing speech synthesis to prevent duplicate audio
    if (synthesizerRef.current) {
      console.log('🔄 Stopping existing synthesizer before creating new one');
      try {
        synthesizerRef.current.close();
      } catch (err) {
        console.warn('⚠️ Error closing old synthesizer:', err);
      }
      synthesizerRef.current = null;
    }
    
    setIsSpeaking(true);
    
    try {
      const { token, region } = await getToken();
      const speechConfig = sdk.SpeechConfig.fromAuthorizationToken(token, region);
      
      const voiceId = COACH_VOICES[language][voiceGender].id;
      speechConfig.speechSynthesisVoiceName = voiceId;
      
      const synthesizer = new sdk.SpeechSynthesizer(speechConfig);
      synthesizerRef.current = synthesizer;

      synthesizer.speakTextAsync(
        text,
        async () => {
          setIsSpeaking(false);
          synthesizer.close();
          
          // Auto-restart listening if session is still active
          if (shouldContinueRef.current) {
            // Reset last processed text to allow new recognition
            lastProcessedTextRef.current = '';
            console.log('🔄 Starting new listening cycle');
            
            const recognizer = await initRecognizer();
            recognizer.startContinuousRecognitionAsync(() => {
              setIsListening(true);
            });
          }
        },
        (err) => {
          onError?.(err);
          setIsSpeaking(false);
          synthesizer.close();
        }
      );
    } catch (err) {
      onError?.(err instanceof Error ? err.message : 'Speech synthesis error');
      setIsSpeaking(false);
    }
  }, [language, voiceGender, initRecognizer, onError]);

  // Start the session
  const startSession = useCallback(async () => {
    try {
      shouldContinueRef.current = true;
      setIsActive(true);
      
      // Reset processing state for new session
      isProcessingRef.current = false;
      lastProcessedTextRef.current = '';
      
      const recognizer = await initRecognizer();
      recognizer.startContinuousRecognitionAsync(() => {
        setIsListening(true);
      });
    } catch (err) {
      onError?.(err instanceof Error ? err.message : 'Failed to start session');
      setIsActive(false);
    }
  }, [initRecognizer, onError]);

  // Stop the session immediately
  const stopSession = useCallback(() => {
    console.log('🛑 Stopping voice session...');
    shouldContinueRef.current = false;
    setIsActive(false);
    setIsListening(false);
    setIsSpeaking(false);
    
    // Reset processing state
    isProcessingRef.current = false;
    lastProcessedTextRef.current = '';
    
    // Clear any partial transcript
    if (onPartialTranscript) {
      onPartialTranscript('');
    }
    
    // Stop recognizer with callback to ensure it stops
    if (recognizerRef.current) {
      try {
        recognizerRef.current.stopContinuousRecognitionAsync(
          () => {
            console.log('✅ Recognizer stopped successfully');
            if (recognizerRef.current) {
              recognizerRef.current.close();
              recognizerRef.current = null;
            }
          },
          (err) => {
            console.error('❌ Error stopping recognizer:', err);
            if (recognizerRef.current) {
              recognizerRef.current.close();
              recognizerRef.current = null;
            }
          }
        );
      } catch (err) {
        console.error('❌ Exception stopping recognizer:', err);
        if (recognizerRef.current) {
          recognizerRef.current.close();
          recognizerRef.current = null;
        }
      }
    }
    
    // Stop synthesizer immediately
    if (synthesizerRef.current) {
      try {
        synthesizerRef.current.close();
        synthesizerRef.current = null;
        console.log('✅ Synthesizer stopped');
      } catch (err) {
        console.error('❌ Error stopping synthesizer:', err);
      }
    }
  }, [onPartialTranscript]);

  return {
    isListening,
    isSpeaking,
    isActive,
    startSession,
    stopSession,
    speakAndContinue  // Called by parent when AI response ready
  };
};



