import { CircleHelp, Sparkles } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { WORKSPACE_CHAT_FONT } from '../../constants/workspaceFonts';

type Props = {
  disabled?: boolean;
  onPick: (message: string) => void;
};

function S0ChoiceCard({
  label,
  icon: Icon,
  onClick,
  disabled,
}: {
  label: string;
  icon: typeof Sparkles;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className="group flex w-full min-w-0 flex-col items-center justify-center gap-2.5 rounded-[18px] border border-[#E8E0CC] bg-white px-4 py-5 text-center shadow-[0px_1px_8px_rgba(10,10,10,0.05)] transition-[border-color,box-shadow,transform] duration-200 hover:border-[#d4c4a8] hover:shadow-[0px_2px_14px_rgba(201,169,110,0.12)] active:scale-[0.99] disabled:pointer-events-none disabled:opacity-55 sm:px-5 sm:py-6"
      style={{ fontFamily: WORKSPACE_CHAT_FONT }}
    >
      <span className="flex h-11 w-11 items-center justify-center rounded-full bg-[#f7f3ea] text-[#AA771C] transition-colors group-hover:bg-[#f0e8d6]">
        <Icon className="h-5 w-5" strokeWidth={1.5} aria-hidden />
      </span>
      <span className="text-[14px] font-medium leading-snug text-[#393939] sm:text-[15px]">
        {label}
      </span>
    </button>
  );
}

/** After workspace welcome — S0 permission quick replies. */
export function WorkspaceS0QuickPick({ disabled, onPick }: Props) {
  const { t, i18n } = useTranslation();
  const dir = i18n.dir() as 'rtl' | 'ltr';

  const readyMsg = t('workspace.s0PickReady');
  const explainMsg = t('workspace.s0PickExplain');

  return (
    <div className="w-full max-w-[min(520px,100%)] px-1" dir={dir}>
      <p
        className="mb-3 text-center text-[13px] text-[#4c5a70]/85 sm:text-start"
        style={{ fontFamily: WORKSPACE_CHAT_FONT }}
      >
        {t('workspace.s0QuickPickHint')}
      </p>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <S0ChoiceCard
          label={readyMsg}
          icon={Sparkles}
          disabled={disabled}
          onClick={() => onPick(readyMsg)}
        />
        <S0ChoiceCard
          label={explainMsg}
          icon={CircleHelp}
          disabled={disabled}
          onClick={() => onPick(explainMsg)}
        />
      </div>
    </div>
  );
}
