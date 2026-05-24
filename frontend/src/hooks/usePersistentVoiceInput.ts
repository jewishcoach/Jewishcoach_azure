import { useState, useRef, useCallback, useEffect } from 'react';
import * as sdk from 'microsoft-cognitiveservices-speech-sdk';
import { apiClient } from '../services/api';

const RECOGNITION_LANGUAGE_MAP: Record<string, string> = {
  he: 'he-IL',
  en: 'en-US',
};

type Options = {
  language: string;
  getClerkToken?: () => Promise<string | null>;
  /** Voice session stays on while true (user chose "speak" mode). */
  enabled: boolean;
  /** Pause mic while coach thinks, forms, stations, welcome, etc. */
  paused: boolean;
  onUtterance: (text: string) => void | Promise<void>;
};

export function usePersistentVoiceInput({
  language,
  getClerkToken,
  enabled,
  paused,
  onUtterance,
}: Options) {
  const [isListening, setIsListening] = useState(false);
  const [livePreview, setLivePreview] = useState('');
  const [error, setError] = useState<string | null>(null);

  const recognizerRef = useRef<sdk.SpeechRecognizer | null>(null);
  const enabledRef = useRef(enabled);
  const pausedRef = useRef(paused);
  const processingRef = useRef(false);
  const lastTextRef = useRef('');
  const onUtteranceRef = useRef(onUtterance);
  const startingRef = useRef(false);

  useEffect(() => {
    onUtteranceRef.current = onUtterance;
  }, [onUtterance]);

  useEffect(() => {
    enabledRef.current = enabled;
  }, [enabled]);

  useEffect(() => {
    pausedRef.current = paused;
  }, [paused]);

  const teardown = useCallback(async () => {
    const rec = recognizerRef.current;
    recognizerRef.current = null;
    setIsListening(false);
    if (!rec) {
      setLivePreview('');
      return;
    }
    await new Promise<void>((resolve) => {
      rec.stopContinuousRecognitionAsync(
        () => {
          rec.close();
          resolve();
        },
        () => {
          rec.close();
          resolve();
        },
      );
    });
    if (!processingRef.current) {
      setLivePreview('');
    }
  }, []);

  const startListening = useCallback(async () => {
    if (
      !enabledRef.current ||
      pausedRef.current ||
      recognizerRef.current ||
      processingRef.current ||
      startingRef.current
    ) {
      return;
    }

    startingRef.current = true;
    try {
      setError(null);

      if (getClerkToken) {
        const clerkJwt = await getClerkToken();
        if (clerkJwt) {
          apiClient.setToken(clerkJwt);
        }
      }

      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error('Microphone not supported in this browser');
      }
      await navigator.mediaDevices.getUserMedia({ audio: true });

      const { token, region } = await apiClient.getSpeechToken();
      const speechConfig = sdk.SpeechConfig.fromAuthorizationToken(token, region);
      speechConfig.speechRecognitionLanguage = RECOGNITION_LANGUAGE_MAP[language] || 'en-US';

      const recognizer = new sdk.SpeechRecognizer(
        speechConfig,
        sdk.AudioConfig.fromDefaultMicrophoneInput(),
      );

      recognizer.recognizing = (_s, e) => {
        if (!enabledRef.current || pausedRef.current) return;
        setLivePreview(e.result.text ?? '');
      };

      recognizer.recognized = (_s, e) => {
        if (!enabledRef.current || pausedRef.current) return;
        if (e.result.reason !== sdk.ResultReason.RecognizedSpeech || !e.result.text?.trim()) {
          return;
        }

        const text = e.result.text.trim();
        if (processingRef.current || lastTextRef.current === text) return;

        processingRef.current = true;
        lastTextRef.current = text;
        setLivePreview('');

        void (async () => {
          await teardown();
          try {
            await onUtteranceRef.current(text);
          } finally {
            processingRef.current = false;
            window.setTimeout(() => {
              lastTextRef.current = '';
            }, 900);
          }
        })();
      };

      recognizer.canceled = (_s, e) => {
        if (e.reason === sdk.CancellationReason.Error) {
          setError(e.errorDetails || 'Speech recognition error');
        }
      };

      await new Promise<void>((resolve, reject) => {
        recognizer.startContinuousRecognitionAsync(resolve, reject);
      });

      recognizerRef.current = recognizer;
      setIsListening(true);
    } catch (err) {
      console.error('Persistent voice input error:', err);
      setError(err instanceof Error ? err.message : 'Recording error');
      setIsListening(false);
    } finally {
      startingRef.current = false;
    }
  }, [language, getClerkToken, teardown]);

  useEffect(() => {
    if (!enabled) {
      void teardown();
      return;
    }
    if (paused) {
      void teardown();
      return;
    }
    void startListening();
  }, [enabled, paused, teardown, startListening]);

  useEffect(() => () => {
    void teardown();
  }, [teardown]);

  return { isListening, livePreview, error };
}
