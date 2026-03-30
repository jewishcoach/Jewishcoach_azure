import { useState, useRef, useCallback } from 'react';
import * as sdk from 'microsoft-cognitiveservices-speech-sdk';
import { apiClient } from '../services/api';

const RECOGNITION_LANGUAGE_MAP: Record<string, string> = {
  he: 'he-IL',
  en: 'en-US',
};

/**
 * @param getClerkToken - Pass `getToken` from `useAuth()` so /speech/token gets a fresh JWT (avoids 401 when apiClient token is stale or unset).
 */
export const useVoiceRecord = (
  language: string,
  getClerkToken?: () => Promise<string | null>,
) => {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recognizerRef = useRef<sdk.SpeechRecognizer | null>(null);
  const transcriptRef = useRef<string[]>([]);

  const getSpeechToken = useCallback(async () => {
    return apiClient.getSpeechToken();
  }, []);

  const startRecording = useCallback(async (): Promise<boolean> => {
    try {
      setError(null);
      transcriptRef.current = [];

      if (getClerkToken) {
        const clerkJwt = await getClerkToken();
        if (clerkJwt) {
          apiClient.setToken(clerkJwt);
        }
      }

      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error('הדפדפן שלך לא תומך בהקלטת קול');
      }
      await navigator.mediaDevices.getUserMedia({ audio: true });

      const { token, region } = await getSpeechToken();
      const speechConfig = sdk.SpeechConfig.fromAuthorizationToken(token, region);
      speechConfig.speechRecognitionLanguage = RECOGNITION_LANGUAGE_MAP[language] || 'en-US';

      const audioConfig = sdk.AudioConfig.fromDefaultMicrophoneInput();
      const recognizer = new sdk.SpeechRecognizer(speechConfig, audioConfig);

      recognizer.recognized = (_s, e) => {
        if (e.result.reason === sdk.ResultReason.RecognizedSpeech && e.result.text?.trim()) {
          transcriptRef.current.push(e.result.text.trim());
        }
      };

      recognizer.canceled = (_s, e) => {
        if (e.reason === sdk.CancellationReason.Error) {
          setError(e.errorDetails || 'שגיאה בזיהוי קול');
        }
      };

      await new Promise<void>((resolve, reject) => {
        recognizer.startContinuousRecognitionAsync(resolve, reject);
      });

      recognizerRef.current = recognizer;
      setIsRecording(true);
      return true;
    } catch (err) {
      console.error('Voice record error:', err);
      setError(err instanceof Error ? err.message : 'שגיאה בהקלטה');
      setIsRecording(false);
      return false;
    }
  }, [language, getSpeechToken, getClerkToken]);

  const stopRecording = useCallback(async (): Promise<string> => {
    if (!recognizerRef.current) {
      setIsRecording(false);
      return transcriptRef.current.join(' ');
    }

    return new Promise((resolve) => {
      recognizerRef.current!.stopContinuousRecognitionAsync(
        () => {
          recognizerRef.current?.close();
          recognizerRef.current = null;
          setIsRecording(false);
          resolve(transcriptRef.current.join(' '));
        },
        () => {
          recognizerRef.current?.close();
          recognizerRef.current = null;
          setIsRecording(false);
          resolve(transcriptRef.current.join(' '));
        }
      );
    });
  }, []);

  return { isRecording, error, startRecording, stopRecording };
};
