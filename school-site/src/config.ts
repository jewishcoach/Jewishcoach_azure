export const APP_URL = import.meta.env.VITE_APP_URL ?? 'https://www.jewishcoacher.com/'
export const LEGACY_URL = import.meta.env.VITE_LEGACY_URL ?? 'https://bsdcoach.com'
export const CONTACT_EMAIL = import.meta.env.VITE_CONTACT_EMAIL ?? 'office@bsdcoach.com'
export const CONTACT_PHONE = import.meta.env.VITE_CONTACT_PHONE ?? ''
// the coach app's server sends the contact form to the office (Nov 10; it was a mailto: link that sent nothing)
export const CONTACT_API_URL =
  import.meta.env.VITE_CONTACT_API_URL ?? 'https://jewishcoach-api.azurewebsites.net/api/public/site-contact'

export type ProgramCard = {
  title: string
  description: string
  href: string
  cta: string
}

export { programsFromPdf as programs } from './data/pdfContent'
