import { dark } from '@clerk/themes';
import type { Appearance } from '@clerk/shared/types';

/**
 * Clerk modals (SignIn / SignUp / UserButton) aligned with BSD workspace:
 * slate base, cream text, gold primary — matches LandingPage and App header.
 */
export const bsdClerkAppearance = {
  theme: dark,
  variables: {
    colorPrimary: '#c9a227',
    colorPrimaryForeground: '#020617',
    colorBackground: '#0f172a',
    colorForeground: '#f5f5f0',
    colorMutedForeground: 'rgba(245, 245, 240, 0.65)',
    colorNeutral: 'rgba(255, 255, 255, 0.12)',
    colorInput: '#020617',
    colorInputForeground: '#f5f5f0',
    colorBorder: 'rgba(255, 255, 255, 0.1)',
    borderRadius: '0.75rem',
    fontFamily: '"Inter", system-ui, sans-serif',
    fontFamilyButtons: '"Inter", system-ui, sans-serif',
    colorModalBackdrop: '#020617',
  },
  layout: {
    logoImageUrl: '/bsd-logo.png',
    logoPlacement: 'inside',
    socialButtonsVariant: 'blockButton',
    socialButtonsPlacement: 'top',
  },
  elements: {
    card: 'border border-white/[0.08] shadow-[0_25px_50px_-12px_rgba(0,0,0,0.55)]',
    headerTitle: 'text-[#f5f5f0]',
    headerSubtitle: 'text-[#f5f5f0]/70',
    modalBackdrop: 'backdrop-blur-sm',
    modalContent: 'border border-white/[0.06]',
    formButtonPrimary:
      'bg-gradient-to-r from-[#BF953F] via-[#FCF6BA] to-[#B38728] text-[#020617] font-semibold shadow-md hover:opacity-95 hover:brightness-105',
    formFieldInput:
      'border-white/10 bg-[#020617]/80 focus:ring-2 focus:ring-[#c9a227]/30 focus:border-[#c9a227]/40',
    formFieldLabel: 'text-[#f5f5f0]/90',
    footer: 'text-[#f5f5f0]/55',
    footerAction: 'text-[#f5f5f0]/80',
    footerActionLink: 'text-[#FCF6BA] hover:text-[#FCF6BA]/90 font-medium',
    identityPreviewText: 'text-[#f5f5f0]/90',
    identityPreviewEditButton: 'text-[#FCF6BA]',
    formFieldInputShowPasswordButton: 'text-[#FCF6BA]/90',
    dividerLine: 'bg-white/[0.12]',
    dividerText: 'text-[#f5f5f0]/45',
    socialButtonsBlockButton:
      'border-white/12 bg-white/[0.04] text-[#f5f5f0] hover:bg-white/[0.08]',
    alternativeMethodsBlockButton: 'border-white/12',
    otpCodeFieldInputs: 'gap-2',
  },
  captcha: { theme: 'dark' },
} satisfies Appearance;
