import { Keyboard, Mic } from 'lucide-react';
import { useTranslation } from 'react-i18next';

export type WorkspaceInputMode = 'type' | 'voice';

type Props = {
  mode: WorkspaceInputMode;
  onChange: (mode: WorkspaceInputMode) => void;
  disabled?: boolean;
};

export function WorkspaceInputModeToggle({ mode, onChange, disabled }: Props) {
  const { t } = useTranslation();

  return (
    <div
      className="mb-2 flex rounded-[9px] border border-[#e8e0cc] bg-[#f5f1e8] p-0.5"
      role="tablist"
      aria-label={t('workspace.inputModeLabel')}
    >
      <button
        type="button"
        role="tab"
        aria-selected={mode === 'type'}
        disabled={disabled}
        onClick={() => onChange('type')}
        className={`flex flex-1 items-center justify-center gap-1.5 rounded-[7px] px-2 py-1.5 text-[12px] font-medium transition-colors md:text-[13px] ${
          mode === 'type'
            ? 'bg-white text-[#1a1510] shadow-sm'
            : 'text-[#4c5a70]/85 hover:text-[#1a1510]'
        } disabled:opacity-50`}
      >
        <Keyboard size={14} strokeWidth={1.5} aria-hidden />
        {t('workspace.inputModeType')}
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={mode === 'voice'}
        disabled={disabled}
        onClick={() => onChange('voice')}
        className={`flex flex-1 items-center justify-center gap-1.5 rounded-[7px] px-2 py-1.5 text-[12px] font-medium transition-colors md:text-[13px] ${
          mode === 'voice'
            ? 'bg-white text-[#1a1510] shadow-sm'
            : 'text-[#4c5a70]/85 hover:text-[#1a1510]'
        } disabled:opacity-50`}
      >
        <Mic size={14} strokeWidth={1.5} aria-hidden />
        {t('workspace.inputModeVoice')}
      </button>
    </div>
  );
}
