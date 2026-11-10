import { useState, type FormEvent } from 'react'
import { CONTACT_API_URL, CONTACT_EMAIL } from '../config'

export type ContactSubject =
  | 'personal-coach'
  | 'certified-program'
  | 'books'
  | 'other'

const subjectLabels: Record<ContactSubject, string> = {
  'personal-coach': 'התאמת מאמן אישי (אחד על אחד)',
  'certified-program': 'תוכנית השלמה והתמחות למאמנים מוסמכים',
  books: 'רכישת חומרי לימוד וספרות מקצועית',
  other: 'אחר',
}

type ContactFormProps = {
  defaultSubject?: ContactSubject
  submitLabel?: string
  compact?: boolean
  showCertificationField?: boolean
}

export function ContactForm({
  defaultSubject = 'other',
  submitLabel = 'שליחה',
  compact = false,
  showCertificationField = false,
}: ContactFormProps) {
  const [sent, setSent] = useState(false)
  const [sending, setSending] = useState(false)
  const [failed, setFailed] = useState(false)
  const [subject, setSubject] = useState<ContactSubject>(defaultSubject)

  // Sent by the server to the office (Nov 10). It used to open the visitor's mail app (mailto:), so nothing arrived
  // unless they pressed "send" there — and without a mail app nothing happened at all, while the site said "תודה!".
  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (sending) return
    const fd = new FormData(e.currentTarget)
    const name = String(fd.get('name') ?? '')
    const phone = String(fd.get('phone') ?? '')
    const email = String(fd.get('email') ?? '')
    const message = String(fd.get('message') ?? '')
    const certification = String(fd.get('certification') ?? '')
    const topic = subjectLabels[subject]

    setSending(true)
    setFailed(false)
    try {
      const res = await fetch(CONTACT_API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name, phone, email, message, certification, topic,
          page: window.location.pathname,
          website: String(fd.get('website') ?? ''),
        }),
      })
      if (!res.ok) throw new Error(String(res.status))
      setSent(true)
    } catch {
      setFailed(true)
    } finally {
      setSending(false)
    }
  }

  if (sent) {
    return (
      <p className="rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 text-sm">
        תודה! הפנייה התקבלה, ונחזור אליכם בהקדם.
      </p>
    )
  }

  return (
    <form onSubmit={onSubmit} className={`space-y-4 ${compact ? '' : 'max-w-lg'}`}>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block text-sm">
          <span className="font-medium text-navy">שם מלא</span>
          <input
            name="name"
            required
            className="mt-1 w-full rounded-lg border border-navy/20 px-3 py-2 text-sm"
          />
        </label>
        <label className="block text-sm">
          <span className="font-medium text-navy">טלפון</span>
          <input
            name="phone"
            required
            type="tel"
            className="mt-1 w-full rounded-lg border border-navy/20 px-3 py-2 text-sm"
          />
        </label>
      </div>
      <label className="block text-sm">
        <span className="font-medium text-navy">דואר אלקטרוני</span>
        <input
          name="email"
          required
          type="email"
          className="mt-1 w-full rounded-lg border border-navy/20 px-3 py-2 text-sm"
        />
      </label>
      {!compact ? (
        <label className="block text-sm">
          <span className="font-medium text-navy">נושא הפנייה</span>
          <select
            value={subject}
            onChange={(e) => setSubject(e.target.value as ContactSubject)}
            className="mt-1 w-full rounded-lg border border-navy/20 px-3 py-2 text-sm bg-white"
          >
            {(Object.keys(subjectLabels) as ContactSubject[]).map((key) => (
              <option key={key} value={key}>
                {subjectLabels[key]}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      {showCertificationField ? (
        <label className="block text-sm">
          <span className="font-medium text-navy">מוסד הכשרה קודם / תעודה</span>
          <input
            name="certification"
            className="mt-1 w-full rounded-lg border border-navy/20 px-3 py-2 text-sm"
          />
        </label>
      ) : null}
      <label className="block text-sm">
        <span className="font-medium text-navy">
          {compact ? 'מה מעניין אותך?' : 'תוכן הפנייה / הערות'}
        </span>
        <textarea
          name="message"
          rows={compact ? 2 : 4}
          className="mt-1 w-full rounded-lg border border-navy/20 px-3 py-2 text-sm"
          placeholder={
            compact
              ? 'אימון אישי / קורס הכשרת מאמנים / אחר'
              : undefined
          }
        />
      </label>
      {/* hidden from people; simple bots fill it and the server drops the message */}
      <input name="website" tabIndex={-1} autoComplete="off" aria-hidden="true"
        className="sr-only" />
      {failed ? (
        <p className="rounded-xl bg-amber-50 border border-amber-200 text-amber-900 px-4 py-3 text-sm">
          השליחה לא הצליחה. אפשר לנסות שוב, או לכתוב ישירות אל{' '}
          <a href={`mailto:${CONTACT_EMAIL}`} className="underline font-semibold">{CONTACT_EMAIL}</a>
          {' '}או בוואטסאפ <a href="https://wa.me/972523288607" className="underline font-semibold" dir="ltr">052-3288607</a>.
        </p>
      ) : null}
      <button
        type="submit"
        disabled={sending}
        className="w-full sm:w-auto rounded-full bg-cyan text-navy font-semibold px-8 py-3 text-sm hover:brightness-90 transition disabled:opacity-60"
      >
        {sending ? 'שולח…' : submitLabel}
      </button>
    </form>
  )
}
