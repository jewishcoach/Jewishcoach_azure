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
  const [livePreview, setLivePreview] = useState('');
  const recognizerRef = useRef<sdk.SpeechRecognizer | null>(null);
  const transcriptRef = useRef<string[]>([]);
  const partialRef = useRef('');

  const flushLivePreview = useCallback(() => {
    const joined = transcriptRef.current.join(' ');
    const p = partialRef.current.trim();
    setLivePreview(p ? (joined ? `${joined} ${p}` : p) : joined);
  }, []);

  const getSpeechToken = useCallback(async () => {
    return apiClient.getSpeechToken();
  }, []);

  const startRecording = useCallback(async (): Promise<boolean> => {
    try {
      setError(null);
      transcriptRef.current = [];
      partialRef.current = '';
      setLivePreview('');

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

      recognizer.recognizing = (_s, e) => {
        partialRef.current = e.result.text ?? '';
        flushLivePreview();
      };

      recognizer.recognized = (_s, e) => {
        if (e.result.reason === sdk.ResultReason.RecognizedSpeech && e.result.text?.trim()) {
          transcriptRef.current.push(e.result.text.trim());
          partialRef.current = '';
          flushLivePreview();
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
  }, [language, getSpeechToken, getClerkToken, flushLivePreview]);

  const stopRecording = useCallback(async (): Promise<string> => {
    const mergeTranscript = () => {
      const joined = transcriptRef.current.join(' ');
      const p = partialRef.current.trim();
      if (p) {
        return joined ? `${joined} ${p}` : p;
      }
      return joined;
    };

    if (!recognizerRef.current) {
      setIsRecording(false);
      setLivePreview('');
      return mergeTranscript();
    }

    return new Promise((resolve) => {
      recognizerRef.current!.stopContinuousRecognitionAsync(
        () => {
          recognizerRef.current?.close();
          recognizerRef.current = null;
          setIsRecording(false);
          const text = mergeTranscript();
          partialRef.current = '';
          setLivePreview('');
          resolve(text);
        },
        () => {
          recognizerRef.current?.close();
          recognizerRef.current = null;
          setIsRecording(false);
          const text = mergeTranscript();
          partialRef.current = '';
          setLivePreview('');
          resolve(text);
        }
      );
    });
  }, []);

  return { isRecording, error, livePreview, startRecording, stopRecording };
};
