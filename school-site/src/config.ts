export const APP_URL = import.meta.env.VITE_APP_URL ?? 'https://www.jewishcoacher.com/'
export const LEGACY_URL = import.meta.env.VITE_LEGACY_URL ?? 'https://bsdcoach.com'
export const CONTACT_EMAIL = import.meta.env.VITE_CONTACT_EMAIL ?? 'office@bsdcoach.com'
export const CONTACT_PHONE = import.meta.env.VITE_CONTACT_PHONE ?? ''

export type ProgramCard = {
  title: string
  description: string
  href: string
  cta: string
}

export { programsFromPdf as programs } from './data/pdfContent'
