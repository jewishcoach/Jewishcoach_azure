import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ChevronDown, ChevronUp, X } from 'lucide-react';
import type { StationCheckpointPayload } from '../../types';
import { WORKSPACE_CHAT_FONT } from '../../constants/workspaceFonts';
import { apiClient } from '../../services/api';

interface StationCheckpointBarProps {
  checkpoint: StationCheckpointPayload;
  conversationId: number;
  getToken: () => Promise<string | null>;
  onDismiss: () => void;
  onIntentSent: () => void;
}

export function StationCheckpointBar({
  checkpoint,
  conversationId,
  getToken,
  onDismiss,
  onIntentSent,
}: StationCheckpointBarProps) {
  const { t, i18n } = useTranslation();
  const [expanded, setExpanded] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendIntent = async (intent: 'pause_here' | 'continue_coaching') => {
    setError(null);
    setBusy(true);
    try {
      const token = await getToken();
      if (!token) {
        setError(t('chat.errorSessionNotFound'));
        return;
      }
      apiClient.setToken(token);
      await apiClient.sendStationIntent(conversationId, intent);
      onIntentSent();
      onDismiss();
    } catch {
      setError(t('chat.errorGeneric'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className="mb-4 rounded-xl border border-[#B38728]/35 bg-gradient-to-br from-[#FFFBF0] to-white shadow-sm overflow-hidden"
      dir={i18n.dir()}
    >
      <div className="flex items-start justify-between gap-2 px-4 pt-3 pb-2 md:px-5">
        <div className="min-w-0 flex-1">
          <p
            className="text-[11px] font-semibold uppercase tracking-wide text-[#8B6914]/90"
            style={{ fontFamily: WORKSPACE_CHAT_FONT }}
          >
            {t('chat.stationCheckpointBadge')}
          </p>
          <h3
            className="text-[15px] md:text-[16px] font-semibold text-[#2E3A56] mt-0.5"
            style={{ fontFamily: WORKSPACE_CHAT_FONT }}
          >
            {checkpoint.floor_title}
          </h3>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          <button
            type="button"
            onClick={() => setExpanded((e) => !e)}
            className="p-2 rounded-lg text-[#2E3A56]/70 hover:bg-[#F0F1F3] transition-colors"
            aria-expanded={expanded}
            title={expanded ? t('chat.stationCollapse') : t('chat.stationExpand')}
          >
            {expanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
          </button>
          <button
            type="button"
            onClick={onDismiss}
            className="p-2 rounded-lg text-[#2E3A56]/50 hover:bg-[#F0F1F3] transition-colors"
            title={t('chat.stationHide')}
          >
            <X size={18} />
          </button>
        </div>
      </div>

      {expanded && (
        <div className="px-4 pb-3 md:px-5 md:pb-4 space-y-3">
          <div>
            <p
              className="text-[13px] font-semibold text-[#2E3A56]/90"
              style={{ fontFamily: WORKSPACE_CHAT_FONT }}
            >
              {checkpoint.homework_title}
            </p>
            <p
              className="text-[13px] md:text-[14px] text-[#2E3A56]/85 mt-1 leading-relaxed whitespace-pre-wrap"
              style={{ fontFamily: WORKSPACE_CHAT_FONT, fontWeight: 400 }}
            >
              {checkpoint.homework_body}
            </p>
          </div>
          {error ? (
            <p className="text-[12px] text-red-700/90" style={{ fontFamily: WORKSPACE_CHAT_FONT }}>
              {error}
            </p>
          ) : null}
          <div className="flex flex-wrap gap-2 pt-1">
            <button
              type="button"
              disabled={busy}
              onClick={() => void sendIntent('pause_here')}
              className="px-4 py-2.5 rounded-xl text-[13px] font-medium bg-white border border-[#E2E4E8] text-[#2E3A56] hover:bg-[#F8F9FA] disabled:opacity-50 transition-colors"
              style={{ fontFamily: WORKSPACE_CHAT_FONT }}
            >
              {t('chat.stationPauseHere')}
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => void sendIntent('continue_coaching')}
              className="px-4 py-2.5 rounded-xl text-[13px] font-semibold bg-[#B38728] text-white hover:bg-[#9a7222] disabled:opacity-50 transition-colors shadow-sm"
              style={{ fontFamily: WORKSPACE_CHAT_FONT }}
            >
              {t('chat.stationContinue')}
            </button>
          </div>
          <p
            className="text-[11px] text-[#5A6B8A]/90 leading-snug"
            style={{ fontFamily: WORKSPACE_CHAT_FONT }}
          >
            {t('chat.stationHint')}
          </p>
        </div>
      )}
    </div>
  );
}
