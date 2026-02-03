import { useState, useRef } from 'react';
import * as sdk from 'microsoft-cognitiveservices-speech-sdk';
import axios from 'axios';
import type { SpeechToken } from '../types';

const VOICE_MAP = {
  he: 'he-IL-HilaNeural',
  en: 'en-US-JennyNeural',
};

const RECOGNITION_LANGUAGE_MAP = {
  he: 'he-IL',
  en: 'en-US',
};

export const useAzureSpeech = (language: string) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recognizerRef = useRef<sdk.SpeechRecognizer | null>(null);

  const getToken = async (): Promise<SpeechToken> => {
    try {
      const response = await axios.get<SpeechToken>('http://localhost:8000/api/speech/token');
      return response.data;
    } catch (err) {
      console.error('Failed to get speech token:', err);
      throw new Error('לא הצלחנו לקבל טוקן לזיהוי דיבור');
    }
  };

  const startRecognition = async (onResult: (text: string) => void) => {
    try {
      setError(null);
      console.log('Starting speech recognition...');
      
      // Check if browser supports getUserMedia
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('הדפדפן שלך לא תומך בזיהוי קול');
      }

      // Request microphone permission explicitly
      try {
        await navigator.mediaDevices.getUserMedia({ audio: true });
        console.log('Microphone permission granted');
      } catch (permErr) {
        console.error('Microphone permission denied:', permErr);
        throw new Error('יש לאשר גישה למיקרופון בדפדפן');
      }

      const { token, region } = await getToken();
      console.log('Got speech token, region:', region);
      
      const speechConfig = sdk.SpeechConfig.fromAuthorizationToken(token, region);
      speechConfig.speechRecognitionLanguage = RECOGNITION_LANGUAGE_MAP[language as keyof typeof RECOGNITION_LANGUAGE_MAP] || 'en-US';
      console.log('Recognition language:', speechConfig.speechRecognitionLanguage);

      const audioConfig = sdk.AudioConfig.fromDefaultMicrophoneInput();
      const recognizer = new sdk.SpeechRecognizer(speechConfig, audioConfig);

      recognizer.recognized = (_s, e) => {
        if (e.result.reason === sdk.ResultReason.RecognizedSpeech && e.result.text) {
          console.log('Recognized text:', e.result.text);
          onResult(e.result.text);
        }
      };

      recognizer.recognizing = (_s, e) => {
        if (e.result.text) {
          console.log('Recognizing:', e.result.text);
        }
      };

      recognizer.canceled = (_s, e) => {
        console.error('Recognition canceled:', e.reason, e.errorDetails);
        if (e.reason === sdk.CancellationReason.Error) {
          setError(`שגיאה בזיהוי קול: ${e.errorDetails}`);
          setIsRecording(false);
        }
      };

      recognizer.sessionStopped = () => {
        console.log('Recognition session stopped');
        setIsRecording(false);
      };

      recognizer.startContinuousRecognitionAsync(
        () => {
          console.log('Recognition started successfully');
          setIsRecording(true);
        },
        (err) => {
          console.error('Recognition start error:', err);
          setError('לא הצלחנו להתחיל זיהוי קול');
          setIsRecording(false);
        }
      );
      
      recognizerRef.current = recognizer;
    } catch (err) {
      console.error('Error starting recognition:', err);
      setError(err instanceof Error ? err.message : 'שגיאה לא ידועה');
      setIsRecording(false);
    }
  };

  const stopRecognition = () => {
    console.log('Stopping recognition...');
    if (recognizerRef.current) {
      recognizerRef.current.stopContinuousRecognitionAsync(
        () => {
          console.log('Recognition stopped successfully');
          recognizerRef.current?.close();
          recognizerRef.current = null;
          setIsRecording(false);
        },
        (err) => {
          console.error('Error stopping recognition:', err);
          setIsRecording(false);
        }
      );
    } else {
      setIsRecording(false);
    }
  };

  const speak = async (text: string) => {
    try {
      setError(null);
      console.log('Starting text-to-speech...');
      
      // Clean text for TTS: remove emojis and markdown
      const cleanTextForTTS = (input: string): string => {
        return input
          // Remove emojis (all emoji ranges)
          .replace(/[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F700}-\u{1F77F}\u{1F780}-\u{1F7FF}\u{1F800}-\u{1F8FF}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FA6F}\u{1FA70}-\u{1FAFF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu, '')
          // Remove markdown bold **text**
          .replace(/\*\*(.*?)\*\*/g, '$1')
          // Remove markdown italic *text*
          .replace(/\*(.*?)\*/g, '$1')
          // Clean up multiple spaces
          .replace(/\s+/g, ' ')
          .trim();
      };
      
      const cleanedText = cleanTextForTTS(text);
      console.log('TTS cleaned text:', cleanedText.substring(0, 100));
      
      const { token, region } = await getToken();
      const speechConfig = sdk.SpeechConfig.fromAuthorizationToken(token, region);
      speechConfig.speechSynthesisVoiceName = VOICE_MAP[language as keyof typeof VOICE_MAP] || VOICE_MAP.en;
      console.log('TTS voice:', speechConfig.speechSynthesisVoiceName);

      const synthesizer = new sdk.SpeechSynthesizer(speechConfig);
      setIsSpeaking(true);

      synthesizer.speakTextAsync(
        cleanedText,
        () => {
          console.log('TTS completed');
          setIsSpeaking(false);
          synthesizer.close();
        },
        (err) => {
          console.error('TTS Error:', err);
          setError('שגיאה בהקראת הטקסט');
          setIsSpeaking(false);
          synthesizer.close();
        }
      );
    } catch (err) {
      console.error('Error with text-to-speech:', err);
      setError(err instanceof Error ? err.message : 'שגיאה בהקראת הטקסט');
      setIsSpeaking(false);
    }
  };

  return { 
    isRecording, 
    isSpeaking, 
    error,
    startRecognition, 
    stopRecognition, 
    speak 
  };
};
