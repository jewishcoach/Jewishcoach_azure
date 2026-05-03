import React, { useCallback, useEffect, useState } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { apiClient } from '../services/api';

interface StepRow {
  id: number;
  sequence_id: number;
  sort_order: number;
  delay_after_previous_minutes: number;
  subject: string;
  body_html: string;
  body_plain: string | null;
  image_urls: string[];
}

interface SequenceRow {
  id: number;
  name: string;
  description: string | null;
  is_active: boolean;
  is_default: boolean;
  steps: StepRow[];
}

export const AdminOnboardingEmailPanel: React.FC = () => {
  const { getToken } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [meta, setMeta] = useState<{ placeholders: string[]; default_app_url: string } | null>(null);
  const [sequences, setSequences] = useState<SequenceRow[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [draftSeq, setDraftSeq] = useState({
    name: '',
    description: '',
    is_active: true,
    is_default: false,
  });
  const [aiOpen, setAiOpen] = useState(false);
  const [aiTargetStepId, setAiTargetStepId] = useState<number | 'new' | null>(null);
  const [aiPrompt, setAiPrompt] = useState('');
  const [aiLang, setAiLang] = useState('he');
  const [aiBusy, setAiBusy] = useState(false);
  const [previewHtml, setPreviewHtml] = useState<string | null>(null);
  const [previewSubject, setPreviewSubject] = useState<string | null>(null);
  const [testEmail, setTestEmail] = useState('');
  const [processBusy, setProcessBusy] = useState(false);

  const authFetch = useCallback(async () => {
    const token = await getToken();
    if (token) apiClient.setToken(token);
  }, [getToken]);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await authFetch();
      const [m, list] = await Promise.all([
        apiClient.getOnboardingEmailMeta(),
        apiClient.listOnboardingEmailSequences(),
      ]);
      setMeta(m as { placeholders: string[]; default_app_url: string });
      const rows = (list as { sequences: SequenceRow[] }).sequences || [];
      setSequences(rows);
      setSelectedId((prev) => {
        if (prev && rows.some((r) => r.id === prev)) return prev;
        return rows[0]?.id ?? null;
      });
    } catch (e: unknown) {
      console.error(e);
      let msg = e instanceof Error ? e.message : 'Failed to load onboarding emails';
      if (/404/.test(msg)) {
        msg =
          '404 — השרת לא מצא את נתיב האונבורדינג. בדרך כלל זה אומר ש־jewishcoach-api בפרודקשן עדיין לא נפרס עם הקומיט האחרון (GitHub Action «Deploy Backend» אחרי push ל־backend/). אחרי פריסה תראה כאן את הרשימה.';
      }
      setError(msg);
      setSequences([]);
    } finally {
      setLoading(false);
    }
  }, [authFetch]);

  useEffect(() => {
    reload();
  }, [reload]);

  const selected = sequences.find((s) => s.id === selectedId) ?? null;

  useEffect(() => {
    if (!selected) {
      setDraftSeq({ name: '', description: '', is_active: true, is_default: false });
      return;
    }
    setDraftSeq({
      name: selected.name,
      description: selected.description || '',
      is_active: selected.is_active,
      is_default: selected.is_default,
    });
  }, [selected]);

  const saveSequence = async () => {
    await authFetch();
    try {
      if (!selected) {
        const row = await apiClient.createOnboardingEmailSequence({
          name: draftSeq.name.trim() || 'סדרה חדשה',
          description: draftSeq.description.trim() || null,
          is_active: draftSeq.is_active,
          is_default: draftSeq.is_default,
        });
        setSelectedId(row.id);
      } else {
        await apiClient.patchOnboardingEmailSequence(selected.id, {
          name: draftSeq.name.trim(),
          description: draftSeq.description.trim() || null,
          is_active: draftSeq.is_active,
          is_default: draftSeq.is_default,
        });
      }
      await reload();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : 'Save failed');
    }
  };

  const addStep = async () => {
    if (!selected) return;
    await authFetch();
    await apiClient.createOnboardingEmailStep(selected.id, {
      delay_after_previous_minutes: selected.steps.length === 0 ? 5 : 1440,
      subject: 'שלב חדש — נושא',
      body_html: '<p>שלום {{display_name}},</p><p>היכנסו לאפליקציה: <a href="{{app_url}}">{{app_url}}</a></p>',
      body_plain: null,
      image_urls: [],
    });
    await reload();
  };

  const patchStepLocal = async (stepId: number, patch: Partial<StepRow>) => {
    if (!selected) return;
    await authFetch();
    await apiClient.patchOnboardingEmailStep(stepId, patch);
    await reload();
  };

  const deleteStep = async (stepId: number) => {
    if (!confirm('למחוק את המסר מהשרשרת?')) return;
    await authFetch();
    await apiClient.deleteOnboardingEmailStep(stepId);
    await reload();
  };

  const moveStep = async (index: number, dir: -1 | 1) => {
    if (!selected) return;
    const steps = [...selected.steps].sort((a, b) => a.sort_order - b.sort_order);
    const j = index + dir;
    if (j < 0 || j >= steps.length) return;
    const swapped = [...steps];
    [swapped[index], swapped[j]] = [swapped[j], swapped[index]];
    await authFetch();
    await apiClient.reorderOnboardingEmailSteps(
      selected.id,
      swapped.map((s) => s.id),
    );
    await reload();
  };

  const openAi = (sid: number | 'new') => {
    setAiTargetStepId(sid);
    setAiOpen(true);
  };

  const runAi = async () => {
    if (!selected) return;
    setAiBusy(true);
    await authFetch();
    try {
      const data = await apiClient.onboardingEmailAiDraft({
        admin_prompt: aiPrompt.trim(),
        language: aiLang,
        sequence_id: selected.id,
        step_id: aiTargetStepId !== 'new' ? aiTargetStepId : null,
      });
      if (aiTargetStepId === 'new') {
        await apiClient.createOnboardingEmailStep(selected.id, {
          delay_after_previous_minutes:
            selected.steps.length === 0 ? 10 : Math.min(10080, 1440 * (selected.steps.length + 1)),
          subject: (data as { subject: string }).subject,
          body_html: (data as { body_html: string }).body_html,
          body_plain: (data as { body_plain?: string }).body_plain ?? null,
          image_urls: [],
        });
      } else if (typeof aiTargetStepId === 'number') {
        await apiClient.patchOnboardingEmailStep(aiTargetStepId, {
          subject: (data as { subject: string }).subject,
          body_html: (data as { body_html: string }).body_html,
          body_plain: (data as { body_plain?: string }).body_plain ?? null,
        });
      }
      setAiOpen(false);
      setAiPrompt('');
      await reload();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : 'AI draft failed');
    } finally {
      setAiBusy(false);
    }
  };

  const previewStep = async (stepId: number) => {
    if (!selected) return;
    await authFetch();
    try {
      const data = await apiClient.onboardingEmailPreviewStep(selected.id, stepId, {
        sample_display_name: 'אבי לדוגמה',
        sample_email: 'preview@example.com',
      });
      setPreviewSubject((data as { subject: string }).subject);
      setPreviewHtml((data as { body_html: string }).body_html);
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : 'Preview failed');
    }
  };

  const sendTest = async (stepId: number) => {
    if (!selected || !testEmail.trim()) {
      alert('נא למלא כתובת אימייל לבדיקה למטה');
      return;
    }
    await authFetch();
    try {
      const res = await apiClient.onboardingEmailTestSend(selected.id, {
        step_id: stepId,
        to_email: testEmail.trim(),
      });
      alert((res as { sent: boolean }).sent ? 'נשלח (בדוק בתיבה).' : 'השליחה נכשלה — בדוק הגדרות Email.');
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : 'Send failed');
    }
  };

  const processDue = async () => {
    setProcessBusy(true);
    await authFetch();
    try {
      const res = await apiClient.onboardingEmailProcessDue(50);
      const r = res as { sent?: number; skipped?: number; notes?: string[] };
      alert(
        `נשלחו: ${r.sent ?? 0}, דולגו: ${r.skipped ?? 0}${r.notes?.length ? `\n${r.notes.slice(0, 5).join('\n')}` : ''}`,
      );
      await reload();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : 'process-due failed');
    } finally {
      setProcessBusy(false);
    }
  };

  if (loading && !sequences.length) {
    return <div className="text-center py-12 text-gray-600">טוען מערכת אימיילים…</div>;
  }

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-red-50 text-red-800 rounded-lg p-4 text-sm border border-red-200">{error}</div>
      )}

      <div className="flex flex-wrap gap-3 items-center justify-between bg-white rounded-lg shadow p-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">שרשרת אימיילים למשתמשים חדשים</h2>
          <p className="text-sm text-gray-600 mt-1">
            סימון &quot;ברירת מחדל&quot; ירשום משתמשים חדשים אוטומטית (בהתחברות ראשונה). שליחה מתוזמנת: הגדר ב‑Azure{' '}
            <code className="bg-slate-100 px-1 rounded text-xs">EMAIL_CONNECTION_STRING</code> או{' '}
            <code className="bg-slate-100 px-1 rounded text-xs">SENDGRID_API_KEY</code>, וכן{' '}
            <code className="bg-slate-100 px-1 rounded text-xs">PUBLIC_APP_URL</code> ו‑
            <code className="bg-slate-100 px-1 rounded text-xs">CLERK_SECRET_KEY</code>. להפעלה אוטומטית של התור: סוד{' '}
            <code className="bg-slate-100 px-1 rounded text-xs">ONBOARDING_EMAIL_CRON_SECRET</code> + קריאה מתוזמנת ל‑
            <code className="bg-slate-100 px-1 rounded text-xs">
              POST /api/internal/onboarding-email/process-due
            </code>{' '}
            (כותרת <code className="bg-slate-100 px-1 rounded text-xs">X-Onboarding-Email-Cron-Secret</code>) — ראה GitHub
            workflow <code className="bg-slate-100 px-1 rounded text-xs">onboarding-email-dispatch.yml</code>. ידנית
            (JWT אדמין):{' '}
            <code className="bg-slate-100 px-1 rounded text-xs">POST /api/admin/onboarding-email/process-due</code>.
          </p>
          {meta && (
            <p className="text-xs text-slate-500 mt-2 font-mono">
              Placeholders: {meta.placeholders.join(' · ')} · app: {meta.default_app_url}
            </p>
          )}
        </div>
        <button
          type="button"
          disabled={processBusy}
          onClick={processDue}
          className="px-4 py-2 rounded-lg bg-emerald-700 text-white text-sm font-medium hover:bg-emerald-800 disabled:opacity-40"
        >
          {processBusy ? 'מעבד…' : 'שלח תורים שהגיע זמנם'}
        </button>
      </div>

      <div className="bg-white rounded-lg shadow p-4 flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-xs text-gray-500 mb-1">סדרה פעילה</label>
          <select
            className="border rounded px-3 py-2 text-sm min-w-[220px]"
            value={selectedId ?? ''}
            onChange={(e) => setSelectedId(e.target.value ? Number(e.target.value) : null)}
          >
            {sequences.length === 0 && <option value="">— אין סדרות —</option>}
            {sequences.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} {s.is_default ? '(ברירת מחדל)' : ''}
              </option>
            ))}
          </select>
        </div>
        <button
          type="button"
          onClick={() => {
            setSelectedId(null);
            setDraftSeq({
              name: 'ברוכים הבאים — סדרה חדשה',
              description: '',
              is_active: true,
              is_default: false,
            });
          }}
          className="px-3 py-2 rounded border border-gray-300 text-sm hover:bg-gray-50"
        >
          סדרה חדשה
        </button>
      </div>

      <div className="bg-white rounded-lg shadow p-4 space-y-3">
        <h3 className="font-semibold text-gray-900">הגדרות סדרה</h3>
        <div className="grid gap-3 md:grid-cols-2">
          <div>
            <label className="block text-xs text-gray-500 mb-1">שם</label>
            <input
              className="w-full border rounded px-3 py-2 text-sm"
              value={draftSeq.name}
              onChange={(e) => setDraftSeq((d) => ({ ...d, name: e.target.value }))}
            />
          </div>
          <div className="flex flex-wrap gap-4 items-center pt-6">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={draftSeq.is_active}
                onChange={(e) => setDraftSeq((d) => ({ ...d, is_active: e.target.checked }))}
              />
              פעיל
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={draftSeq.is_default}
                onChange={(e) => setDraftSeq((d) => ({ ...d, is_default: e.target.checked }))}
              />
              ברירת מחדל לחדשים
            </label>
          </div>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">תיאור פנימי</label>
          <textarea
            className="w-full border rounded px-3 py-2 text-sm min-h-[60px]"
            value={draftSeq.description}
            onChange={(e) => setDraftSeq((d) => ({ ...d, description: e.target.value }))}
          />
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={saveSequence}
            className="px-4 py-2 rounded-lg bg-slate-800 text-white text-sm font-medium hover:bg-slate-700"
          >
            שמור סדרה
          </button>
          {selected && (
            <>
              <button
                type="button"
                onClick={() => openAi('new')}
                className="px-4 py-2 rounded-lg border border-violet-400 text-violet-900 text-sm font-medium hover:bg-violet-50"
              >
                צור מסר חדש עם AI
              </button>
              <button
                type="button"
                onClick={async () => {
                  if (!selected || !confirm('למחוק סדרה כולה?')) return;
                  await authFetch();
                  await apiClient.deleteOnboardingEmailSequence(selected.id);
                  setSelectedId(null);
                  await reload();
                }}
                className="px-4 py-2 rounded-lg border border-red-300 text-red-800 text-sm hover:bg-red-50"
              >
                מחק סדרה
              </button>
            </>
          )}
        </div>
      </div>

      {selected && (
        <>
          <div className="bg-white rounded-lg shadow p-4 flex flex-wrap gap-4 items-end">
            <div className="flex-1 min-w-[200px]">
              <label className="block text-xs text-gray-500 mb-1">אימייל לבדיקות שליחה</label>
              <input
                type="email"
                className="w-full border rounded px-3 py-2 text-sm"
                placeholder="you@company.com"
                value={testEmail}
                onChange={(e) => setTestEmail(e.target.value)}
              />
            </div>
            <button
              type="button"
              onClick={addStep}
              className="px-4 py-2 rounded-lg bg-slate-100 border border-slate-300 text-sm font-medium"
            >
              + מסר ידני
            </button>
          </div>

          <div className="space-y-4">
            {selected.steps
              .slice()
              .sort((a, b) => a.sort_order - b.sort_order)
              .map((st, idx, arr) => (
                <StepEditorCard
                  key={st.id}
                  step={st}
                  index={idx}
                  length={arr.length}
                  onPatch={(patch) => patchStepLocal(st.id, patch)}
                  onDelete={() => deleteStep(st.id)}
                  onMove={(dir) => moveStep(idx, dir)}
                  onAi={() => openAi(st.id)}
                  onPreview={() => previewStep(st.id)}
                  onTest={() => sendTest(st.id)}
                />
              ))}
          </div>
        </>
      )}

      {aiOpen && (
        <div className="fixed inset-0 z-[110] flex items-center justify-center p-4 bg-black/50" role="dialog">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-4 space-y-3">
            <h3 className="font-semibold text-lg">טיוטת AI למסר</h3>
            <label className="block text-xs text-gray-500">שפה</label>
            <select
              className="border rounded px-2 py-1 text-sm"
              value={aiLang}
              onChange={(e) => setAiLang(e.target.value)}
            >
              <option value="he">עברית</option>
              <option value="en">English</option>
            </select>
            <label className="block text-xs text-gray-500">מה המודל צריך לכתוב? (מטרה, טון, דגשים)</label>
            <textarea
              className="w-full border rounded px-3 py-2 text-sm min-h-[120px]"
              value={aiPrompt}
              onChange={(e) => setAiPrompt(e.target.value)}
              placeholder="למשל: מסר חם יום אחרי הרשמה — להזכיר את תהליך BSD ולקרוא להזין את הנושא הראשון בצ'אט..."
            />
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" className="px-3 py-2 text-sm rounded border" onClick={() => setAiOpen(false)}>
                ביטול
              </button>
              <button
                type="button"
                disabled={aiBusy || !aiPrompt.trim()}
                onClick={runAi}
                className="px-4 py-2 rounded-lg bg-violet-700 text-white text-sm disabled:opacity-40"
              >
                {aiBusy ? 'יוצר…' : 'צור והחל'}
              </button>
            </div>
          </div>
        </div>
      )}

      {(previewHtml || previewSubject) && (
        <div className="fixed inset-0 z-[110] flex items-center justify-center p-4 bg-black/50" role="dialog">
          <div className="bg-white rounded-xl shadow-xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            <div className="flex justify-between items-center px-4 py-3 border-b">
              <div className="font-semibold truncate">{previewSubject}</div>
              <button
                type="button"
                className="text-gray-500 hover:text-gray-800 px-2 text-xl"
                onClick={() => {
                  setPreviewHtml(null);
                  setPreviewSubject(null);
                }}
              >
                ×
              </button>
            </div>
            <iframe title="preview" className="flex-1 min-h-[360px] w-full border-0" sandbox="" srcDoc={previewHtml || ''} />
          </div>
        </div>
      )}
    </div>
  );
};

function StepEditorCard({
  step,
  index,
  length,
  onPatch,
  onDelete,
  onMove,
  onAi,
  onPreview,
  onTest,
}: {
  step: StepRow;
  index: number;
  length: number;
  onPatch: (patch: Partial<StepRow>) => void;
  onDelete: () => void;
  onMove: (dir: -1 | 1) => void;
  onAi: () => void;
  onPreview: () => void;
  onTest: () => void;
}) {
  const [delay, setDelay] = useState(String(step.delay_after_previous_minutes));
  const [subject, setSubject] = useState(step.subject);
  const [html, setHtml] = useState(step.body_html);
  const [plain, setPlain] = useState(step.body_plain || '');
  const [imgs, setImgs] = useState(step.image_urls.join('\n'));

  useEffect(() => {
    setDelay(String(step.delay_after_previous_minutes));
    setSubject(step.subject);
    setHtml(step.body_html);
    setPlain(step.body_plain || '');
    setImgs(step.image_urls.join('\n'));
  }, [step]);

  const save = () => {
    const urls = imgs
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean);
    onPatch({
      delay_after_previous_minutes: Math.max(0, parseInt(delay, 10) || 0),
      subject,
      body_html: html,
      body_plain: plain.trim() || null,
      image_urls: urls,
    });
  };

  return (
    <div className="bg-white rounded-lg shadow border border-slate-200 p-4 space-y-3">
      <div className="flex flex-wrap justify-between gap-2 items-center">
        <div className="font-semibold text-slate-900">
          מסר #{index + 1}{' '}
          <span className="text-xs font-normal text-slate-500">(id {step.id})</span>
        </div>
        <div className="flex flex-wrap gap-1">
          <button
            type="button"
            disabled={index <= 0}
            className="px-2 py-1 text-xs rounded border disabled:opacity-30"
            onClick={() => onMove(-1)}
          >
            למעלה
          </button>
          <button
            type="button"
            disabled={index >= length - 1}
            className="px-2 py-1 text-xs rounded border disabled:opacity-30"
            onClick={() => onMove(1)}
          >
            למטה
          </button>
          <button type="button" className="px-2 py-1 text-xs rounded border border-violet-300 text-violet-900" onClick={onAi}>
            AI
          </button>
          <button type="button" className="px-2 py-1 text-xs rounded border" onClick={onPreview}>
            תצוגה מקדימה
          </button>
          <button type="button" className="px-2 py-1 text-xs rounded border border-emerald-300" onClick={onTest}>
            שלח בדיקה
          </button>
          <button type="button" className="px-2 py-1 text-xs rounded border border-red-300 text-red-800" onClick={onDelete}>
            מחק
          </button>
        </div>
      </div>
      <div className="grid md:grid-cols-3 gap-3">
        <div>
          <label className="block text-xs text-gray-500 mb-1">השהיה מהמסר הקודם (דקות)</label>
          <input
            className="w-full border rounded px-2 py-1 text-sm"
            value={delay}
            onChange={(e) => setDelay(e.target.value)}
          />
          <p className="text-[11px] text-slate-500 mt-1">מסר ראשון: השהיה מרגע ההרשמה</p>
        </div>
        <div className="md:col-span-2">
          <label className="block text-xs text-gray-500 mb-1">נושא</label>
          <input className="w-full border rounded px-2 py-1 text-sm" value={subject} onChange={(e) => setSubject(e.target.value)} />
        </div>
      </div>
      <div>
        <label className="block text-xs text-gray-500 mb-1">גוף HTML</label>
        <textarea className="w-full border rounded px-2 py-2 text-sm font-mono min-h-[140px]" value={html} onChange={(e) => setHtml(e.target.value)} />
      </div>
      <div>
        <label className="block text-xs text-gray-500 mb-1">טקסט פשוט (אופציונלי)</label>
        <textarea className="w-full border rounded px-2 py-2 text-sm min-h-[60px]" value={plain} onChange={(e) => setPlain(e.target.value)} />
      </div>
      <div>
        <label className="block text-xs text-gray-500 mb-1">כתובות תמונה (שורה לכל URL — יתווספו לסוף המייל)</label>
        <textarea className="w-full border rounded px-2 py-2 text-sm font-mono min-h-[56px]" value={imgs} onChange={(e) => setImgs(e.target.value)} />
      </div>
      <button type="button" onClick={save} className="px-4 py-2 rounded-lg bg-slate-800 text-white text-sm">
        שמור מסר
      </button>
    </div>
  );
}
