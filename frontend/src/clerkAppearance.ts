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
    colorPrimary: '#e2e4e8',
    colorPrimaryForeground: '#2e3a56',
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
    /* Primary CTA — cream surface + depth (.clerk-form-primary enforces over Clerk defaults) */
    formButtonPrimary: 'premium-cta-btn !rounded-xl !min-h-[44px] !px-4 !text-[#2E3A56] !font-semibold',
    formFieldInput: [
      'border-white/12 bg-[#020617]/90 text-base',
      'focus:ring-2 focus:ring-slate-400/30 focus:border-slate-400/35',
    ].join(' '),
    formFieldLabel: 'text-[#f8fafc]/92 text-sm font-medium',
    footer: 'text-[#f8fafc]/55 text-sm',
    footerAction: 'text-[#f8fafc]/80',
    footerActionLink: 'text-slate-300 hover:text-white font-medium',
    identityPreviewText: 'text-[#f8fafc]/92',
    identityPreviewEditButton: 'text-slate-300 hover:text-white',
    formFieldInputShowPasswordButton: 'text-slate-300 hover:text-white',
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
  /** UserButton dropdown — light text/icons on dark card (default dark theme washes out actions) */
  userButton: {
    elements: {
      userButtonPopoverCard: 'border border-white/10 bg-[#0f172a] shadow-2xl',
      userButtonPopoverMain: 'text-[#f8fafc]',
      userButtonPopoverActionButton:
        '!text-[#f1f5f9] hover:!bg-white/[0.12] [&_span]:!text-[#f1f5f9]',
      userButtonPopoverActionButton__manageAccount: '!text-[#f1f5f9]',
      userButtonPopoverActionButton__signOut: '!text-[#f1f5f9]',
      userButtonPopoverActionButtonIcon: '!text-[#f1f5f9] opacity-100',
      userButtonPopoverActionButtonIconBox: 'text-[#f1f5f9]',
      userButtonPopoverFooter: 'text-slate-400',
    },
  },
  captcha: { theme: 'dark' },
} satisfies Appearance;
