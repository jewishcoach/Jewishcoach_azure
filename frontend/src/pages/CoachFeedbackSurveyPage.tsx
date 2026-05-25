import { useMemo, useState } from 'react';
import axios from 'axios';
import { CheckCircle2, Loader2 } from 'lucide-react';
import {
  COACH_FEEDBACK_SURVEY_INTRO,
  COACH_FEEDBACK_SURVEY_SECTIONS,
  COACH_FEEDBACK_SURVEY_TITLE,
  RECOMMEND_TRAINEES_OPTIONS,
  REQUIRED_CHOICE_KEYS,
  type SurveyQuestion,
} from '../data/coachFeedbackSurveyQuestions';
import { apiClient } from '../services/api';

type FormState = {
  respondentName: string;
  choices: Record<string, string>;
  otherTexts: Record<string, string>;
  questionQuality: string;
  upgradeSuggestion: string;
  recommendReason: string;
};

const INITIAL_FORM: FormState = {
  respondentName: '',
  choices: {},
  otherTexts: {},
  questionQuality: '',
  upgradeSuggestion: '',
  recommendReason: '',
};

function ChoiceGroup({
  question,
  value,
  otherValue,
  onChange,
  onOtherChange,
  disabled,
}: {
  question: SurveyQuestion;
  value: string;
  otherValue: string;
  onChange: (next: string) => void;
  onOtherChange: (next: string) => void;
  disabled?: boolean;
}) {
  const options = question.allowOther
    ? [...question.options, { value: 'other', label: 'אחר' }]
    : question.options;

  return (
    <fieldset className="space-y-3" disabled={disabled}>
      <legend className="text-base font-semibold text-[#2E3A56] mb-1">{question.title}</legend>
      <div className="space-y-2">
        {options.map((option) => {
          const checked = value === option.value;
          return (
            <label
              key={option.value}
              className={`flex items-start gap-3 rounded-xl border px-4 py-3 cursor-pointer transition-colors ${
                checked
                  ? 'border-[#C9A96E] bg-[#fffaf0]'
                  : 'border-[#E2E4E8] bg-white hover:border-[#CCD6E0]'
              }`}
            >
              <input
                type="radio"
                name={question.key}
                value={option.value}
                checked={checked}
                onChange={() => onChange(option.value)}
                className="mt-1 accent-[#C9A96E]"
              />
              <span className="text-sm leading-relaxed text-[#2E3A56]">{option.label}</span>
            </label>
          );
        })}
      </div>
      {value === 'other' && (
        <textarea
          value={otherValue}
          onChange={(e) => onOtherChange(e.target.value)}
          rows={3}
          placeholder="פרט/י כאן..."
          className="w-full rounded-xl border border-[#E2E4E8] bg-white px-4 py-3 text-sm text-[#2E3A56] focus:border-[#C9A96E] focus:outline-none focus:ring-2 focus:ring-[#C9A96E]/20"
        />
      )}
    </fieldset>
  );
}

export function CoachFeedbackSurveyPage() {
  const [form, setForm] = useState<FormState>(INITIAL_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [submittedId, setSubmittedId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const shareUrl = useMemo(() => {
    if (typeof window === 'undefined') return '';
    return `${window.location.origin}/coach-feedback-survey`;
  }, []);

  const setChoice = (key: string, value: string) => {
    setForm((prev) => ({
      ...prev,
      choices: { ...prev.choices, [key]: value },
    }));
  };

  const setOtherText = (key: string, value: string) => {
    setForm((prev) => ({
      ...prev,
      otherTexts: { ...prev.otherTexts, [key]: value },
    }));
  };

  const validate = (): string | null => {
    const name = form.respondentName.trim();
    if (!name) return 'נא למלא את שם הממלא.';

    for (const key of REQUIRED_CHOICE_KEYS) {
      const choice = form.choices[key];
      if (!choice) return 'נא לענות על כל שאלות הבחירה.';
      if (choice === 'other' && !form.otherTexts[key]?.trim()) {
        return 'נא לפרט את תשובת "אחר".';
      }
    }

    return null;
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);

    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    const responses: Record<string, string> = {};
    for (const key of REQUIRED_CHOICE_KEYS) {
      responses[key] = form.choices[key];
      if (form.choices[key] === 'other') {
        responses[`${key}_other`] = form.otherTexts[key].trim();
      }
    }

    const questionQuality = form.questionQuality.trim();
    if (questionQuality) responses.question_quality = questionQuality;

    const upgradeSuggestion = form.upgradeSuggestion.trim();
    if (upgradeSuggestion) responses.upgrade_suggestion = upgradeSuggestion;

    const recommendReason = form.recommendReason.trim();
    if (recommendReason) responses.recommend_reason = recommendReason;

    setSubmitting(true);
    try {
      const result = await apiClient.submitCoachFeedbackSurvey({
        respondent_name: form.respondentName.trim(),
        responses,
      });
      setSubmittedId(result.id);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const detail = err.response?.data?.detail;
        if (typeof detail === 'string') {
          setError(detail);
        } else if (Array.isArray(detail) && detail[0]?.msg) {
          setError(String(detail[0].msg));
        } else {
          setError('שליחת הטופס נכשלה. נסו שוב בעוד רגע.');
        }
      } else {
        setError('שליחת הטופס נכשלה. נסו שוב בעוד רגע.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (submittedId != null) {
    return (
      <div dir="rtl" className="min-h-screen bg-[#faf8f3] px-4 py-10">
        <div className="mx-auto max-w-2xl rounded-2xl border border-[#E2E4E8] bg-white p-8 shadow-sm text-center">
          <CheckCircle2 className="mx-auto mb-4 h-14 w-14 text-[#C9A96E]" />
          <h1 className="text-2xl font-semibold text-[#2E3A56] mb-3">תודה רבה!</h1>
          <p className="text-[#4c5a70] leading-relaxed">
            המשוב שלכם נשמר בהצלחה. מספר הגשה: {submittedId}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div dir="rtl" className="min-h-screen bg-[#faf8f3]">
      <header className="border-b border-white/[0.07] bg-[#1e293b] px-4 py-5 md:px-8">
        <div className="mx-auto flex max-w-3xl items-center gap-4">
          <img src="/bsd-logo.png" alt="BSD אימון יהודי" className="h-12 object-contain" />
          <div>
            <p className="text-xs text-[#8b97ae]">טופס ציבורי לשיתוף</p>
            <p className="text-sm text-[#e8e4dc] break-all">{shareUrl}</p>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-8 md:py-10">
        <form onSubmit={handleSubmit} className="space-y-8">
          <section className="rounded-2xl border border-[#E2E4E8] bg-white p-6 md:p-8 shadow-sm">
            <h1
              className="text-2xl md:text-3xl font-semibold text-[#2E3A56] mb-4"
              style={{ fontFamily: '"Frank Ruhl Libre", "Heebo", serif' }}
            >
              {COACH_FEEDBACK_SURVEY_TITLE}
            </h1>
            <p className="text-[#4c5a70] leading-relaxed whitespace-pre-line">{COACH_FEEDBACK_SURVEY_INTRO}</p>
          </section>

          <section className="rounded-2xl border border-[#E2E4E8] bg-white p-6 md:p-8 shadow-sm space-y-4">
            <label htmlFor="respondent-name" className="block text-base font-semibold text-[#2E3A56]">
              שם הממלא
            </label>
            <input
              id="respondent-name"
              type="text"
              value={form.respondentName}
              onChange={(e) => setForm((prev) => ({ ...prev, respondentName: e.target.value }))}
              maxLength={200}
              required
              className="w-full rounded-xl border border-[#E2E4E8] bg-white px-4 py-3 text-[#2E3A56] focus:border-[#C9A96E] focus:outline-none focus:ring-2 focus:ring-[#C9A96E]/20"
              placeholder="שם מלא"
            />
          </section>

          {COACH_FEEDBACK_SURVEY_SECTIONS.map((section) => (
            <section
              key={section.id}
              className="rounded-2xl border border-[#E2E4E8] bg-white p-6 md:p-8 shadow-sm space-y-8"
            >
              <h2 className="text-xl font-semibold text-[#2E3A56]">{section.title}</h2>
              {section.questions.map((question) => (
                <ChoiceGroup
                  key={question.key}
                  question={question}
                  value={form.choices[question.key] ?? ''}
                  otherValue={form.otherTexts[question.key] ?? ''}
                  onChange={(value) => setChoice(question.key, value)}
                  onOtherChange={(value) => setOtherText(question.key, value)}
                  disabled={submitting}
                />
              ))}

              {section.id === 'experience' && (
                <div className="space-y-3">
                  <label htmlFor="question-quality" className="block text-base font-semibold text-[#2E3A56]">
                    איכות השאלות וההכוונה
                  </label>
                  <p className="text-sm text-[#4c5a70]">שאלה מצוינת או כזו שפספסה את המטרה?</p>
                  <textarea
                    id="question-quality"
                    value={form.questionQuality}
                    onChange={(e) => setForm((prev) => ({ ...prev, questionQuality: e.target.value }))}
                    rows={4}
                    disabled={submitting}
                    className="w-full rounded-xl border border-[#E2E4E8] bg-white px-4 py-3 text-sm text-[#2E3A56] focus:border-[#C9A96E] focus:outline-none focus:ring-2 focus:ring-[#C9A96E]/20"
                  />
                </div>
              )}
            </section>
          ))}

          <section className="rounded-2xl border border-[#E2E4E8] bg-white p-6 md:p-8 shadow-sm space-y-8">
            <h2 className="text-xl font-semibold text-[#2E3A56]">חלק ד&apos;: השורה התחתונה</h2>

            <div className="space-y-3">
              <label htmlFor="upgrade-suggestion" className="block text-base font-semibold text-[#2E3A56]">
                שאלת שדרוג
              </label>
              <p className="text-sm text-[#4c5a70]">דבר אחד שהיה מקפיץ דרמטית את ערך האפליקציה.</p>
              <textarea
                id="upgrade-suggestion"
                value={form.upgradeSuggestion}
                onChange={(e) => setForm((prev) => ({ ...prev, upgradeSuggestion: e.target.value }))}
                rows={4}
                disabled={submitting}
                className="w-full rounded-xl border border-[#E2E4E8] bg-white px-4 py-3 text-sm text-[#2E3A56] focus:border-[#C9A96E] focus:outline-none focus:ring-2 focus:ring-[#C9A96E]/20"
              />
            </div>

            <ChoiceGroup
              question={{
                key: 'recommend_trainees',
                title: 'המלצה למתאמנים',
                options: RECOMMEND_TRAINEES_OPTIONS,
                allowOther: false,
              }}
              value={form.choices.recommend_trainees ?? ''}
              otherValue=""
              onChange={(value) => setChoice('recommend_trainees', value)}
              onOtherChange={() => {}}
              disabled={submitting}
            />

            <div className="space-y-3">
              <label htmlFor="recommend-reason" className="block text-base font-semibold text-[#2E3A56]">
                מדוע?
              </label>
              <p className="text-sm text-[#4c5a70]">הסבר לתשובת ההמלצה.</p>
              <textarea
                id="recommend-reason"
                value={form.recommendReason}
                onChange={(e) => setForm((prev) => ({ ...prev, recommendReason: e.target.value }))}
                rows={4}
                disabled={submitting}
                className="w-full rounded-xl border border-[#E2E4E8] bg-white px-4 py-3 text-sm text-[#2E3A56] focus:border-[#C9A96E] focus:outline-none focus:ring-2 focus:ring-[#C9A96E]/20"
              />
            </div>
          </section>

          {error && (
            <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="premium-cta-btn inline-flex w-full items-center justify-center gap-2 rounded-xl px-6 py-3 text-base disabled:opacity-60"
          >
            {submitting ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                שולח...
              </>
            ) : (
              'שליחת המשוב'
            )}
          </button>
        </form>
      </main>
    </div>
  );
}

export default CoachFeedbackSurveyPage;
