import { dark } from '@clerk/themes';
import type { Appearance } from '@clerk/shared/types';
import { HEBREW_UI_SANS } from './constants/workspaceFonts';

/**
 * Clerk modals: Hebrew-friendly sans, readable sizes, OAuth buttons on light tiles
 * so provider names (e.g. “Google”) stay visible on dark cards.
 */
export const bsdClerkAppearance = {
  theme: dark,
  variables: {
    colorPrimary: '#d4a20c',
    colorPrimaryForeground: '#0c0a06',
    colorBackground: '#0f172a',
    colorForeground: '#f8fafc',
    colorMutedForeground: 'rgba(248, 250, 252, 0.72)',
    colorNeutral: 'rgba(255, 255, 255, 0.14)',
    colorInput: '#020617',
    colorInputForeground: '#f8fafc',
    colorBorder: 'rgba(255, 255, 255, 0.12)',
    borderRadius: '0.875rem',
    fontFamily: HEBREW_UI_SANS,
    fontFamilyButtons: HEBREW_UI_SANS,
    fontSize: '1rem',
    colorModalBackdrop: '#020617',
  },
  layout: {
    logoImageUrl: '/bsd-logo.png',
    logoPlacement: 'inside',
    socialButtonsVariant: 'blockButton',
    socialButtonsPlacement: 'top',
  },
  elements: {
    rootBox: 'font-sans',
    card: 'border border-white/[0.08] shadow-[0_25px_50px_-12px_rgba(0,0,0,0.55)]',
    headerTitle: 'text-[#f8fafc] text-xl font-semibold tracking-tight',
    headerSubtitle: 'text-[#f8fafc]/75 text-sm font-normal',
    modalBackdrop: 'backdrop-blur-sm',
    modalContent: 'border border-white/[0.06]',
    main: 'gap-4',
    /* Primary CTA — solid amber, less “90s gold chrome” */
    formButtonPrimary: [
      '!bg-amber-500 hover:!bg-amber-400 !text-stone-950 font-semibold',
      'shadow-md shadow-amber-950/25 border-0',
      'transition-colors duration-150',
    ].join(' '),
    formFieldInput: [
      'border-white/12 bg-[#020617]/90 text-base',
      'focus:ring-2 focus:ring-amber-400/35 focus:border-amber-400/40',
    ].join(' '),
    formFieldLabel: 'text-[#f8fafc]/92 text-sm font-medium',
    footer: 'text-[#f8fafc]/55 text-sm',
    footerAction: 'text-[#f8fafc]/80',
    footerActionLink: 'text-amber-300 hover:text-amber-200 font-medium',
    identityPreviewText: 'text-[#f8fafc]/92',
    identityPreviewEditButton: 'text-amber-300',
    formFieldInputShowPasswordButton: 'text-amber-300/95',
    dividerLine: 'bg-white/[0.12]',
    dividerText: 'text-[#f8fafc]/50 text-sm',
    /**
     * Light “OAuth row” — fixes invisible “Google” / provider text on dark theme.
     */
    socialButtonsBlockButton: [
      '!bg-white !border-[#dadce0] !text-[#1f1f1f]',
      'shadow-sm hover:!bg-[#f8f9fa] hover:shadow',
      '[&_*]:!text-[#1f1f1f] [&_span]:!opacity-100',
      'font-medium',
    ].join(' '),
    socialButtonsBlockButtonText: '!text-[#1f1f1f] font-medium',
    socialButtonsProviderIcon: 'shrink-0',
    alternativeMethodsBlockButton: 'border-white/15 bg-white/[0.06] text-[#f8fafc]',
    otpCodeFieldInputs: 'gap-2',
    formFieldRow: 'gap-3',
  },
  captcha: { theme: 'dark' },
} satisfies Appearance;
