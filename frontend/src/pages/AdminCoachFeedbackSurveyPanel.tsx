import React, { useEffect, useState } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { apiClient } from '../services/api';
import {
  COACH_FEEDBACK_SURVEY_SECTIONS,
  RECOMMEND_TRAINEES_OPTIONS,
} from '../data/coachFeedbackSurveyQuestions';

type SurveyItem = {
  id: number;
  respondent_name: string;
  responses: Record<string, string>;
  created_at: string | null;
};

const QUESTION_LABELS: Record<string, string> = {
  ...Object.fromEntries(
    COACH_FEEDBACK_SURVEY_SECTIONS.flatMap((section) =>
      section.questions.map((question) => [question.key, question.title]),
    ),
  ),
  recommend_trainees: 'המלצה למתאמנים',
  question_quality: 'איכות השאלות וההכוונה',
  upgrade_suggestion: 'שאלת שדרוג',
  recommend_reason: 'מדוע?',
};

const OPTION_LABELS: Record<string, string> = {
  ...Object.fromEntries(
    COACH_FEEDBACK_SURVEY_SECTIONS.flatMap((section) =>
      section.questions.flatMap((question) =>
        question.options.map((option) => [option.value, option.label]),
      ),
    ),
  ),
  ...Object.fromEntries(RECOMMEND_TRAINEES_OPTIONS.map((option) => [option.value, option.label])),
  other: 'אחר',
};

function formatAnswer(key: string, value: string, responses: Record<string, string>): string {
  if (value === 'other') {
    const other = responses[`${key}_other`]?.trim();
    return other ? `אחר: ${other}` : 'אחר';
  }
  return OPTION_LABELS[value] ?? value;
}

export const AdminCoachFeedbackSurveyPanel: React.FC = () => {
  const { getToken } = useAuth();
  const [items, setItems] = useState<SurveyItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadItems();
  }, []);

  const loadItems = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = await getToken();
      if (token) apiClient.setToken(token);
      const data = await apiClient.listCoachFeedbackSurveys({ limit: 100 });
      setItems(data.items);
      setTotal(data.total);
    } catch (err) {
      console.error('Failed to load coach feedback surveys:', err);
      setError('טעינת המשובים נכשלה.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-6 text-gray-600">טוען משובי מאמנים...</div>;
  }

  return (
    <div dir="rtl" className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">שאלון משוב מאמנים</h2>
          <p className="text-sm text-gray-600 mt-1">
            קישור לשיתוף:{' '}
            <code className="rounded bg-gray-100 px-2 py-1 text-xs">
              {typeof window !== 'undefined'
                ? `${window.location.protocol}//${
                    window.location.hostname === 'jewishcoacher.com'
                      ? 'www.jewishcoacher.com'
                      : window.location.hostname
                  }/coach-feedback-survey`
                : 'https://www.jewishcoacher.com/coach-feedback-survey'}
            </code>
          </p>
        </div>
        <button
          type="button"
          onClick={() => void loadItems()}
          className="rounded-lg border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50"
        >
          רענון
        </button>
      </div>

      {error && <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

      <div className="rounded-lg border border-gray-200 bg-white overflow-hidden">
        <div className="border-b border-gray-200 px-4 py-3 text-sm text-gray-600">
          סה״כ הגשות: {total}
        </div>
        {items.length === 0 ? (
          <div className="px-6 py-12 text-center text-gray-500">עדיין אין הגשות.</div>
        ) : (
          <div className="divide-y divide-gray-200">
            {items.map((item) => {
              const expanded = expandedId === item.id;
              return (
                <div key={item.id} className="px-4 py-4">
                  <button
                    type="button"
                    onClick={() => setExpandedId(expanded ? null : item.id)}
                    className="flex w-full items-center justify-between gap-4 text-right"
                  >
                    <div>
                      <div className="font-medium text-gray-900">{item.respondent_name}</div>
                      <div className="text-sm text-gray-500">
                        #{item.id}
                        {item.created_at ? ` · ${new Date(item.created_at).toLocaleString('he-IL')}` : ''}
                      </div>
                    </div>
                    <span className="text-sm text-blue-600">{expanded ? 'סגור' : 'פתח'}</span>
                  </button>
                  {expanded && (
                    <dl className="mt-4 space-y-3 rounded-lg bg-gray-50 p-4">
                      {Object.entries(item.responses)
                        .filter(([key]) => !key.endsWith('_other'))
                        .map(([key, value]) => (
                          <div key={key}>
                            <dt className="text-sm font-medium text-gray-700">
                              {QUESTION_LABELS[key] ?? key}
                            </dt>
                            <dd className="text-sm text-gray-900 mt-1 whitespace-pre-wrap">
                              {formatAnswer(key, value, item.responses)}
                            </dd>
                          </div>
                        ))}
                    </dl>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
