import { useState, type FormEvent } from 'react'
import { CONTACT_EMAIL } from '../config'

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
  const [subject, setSubject] = useState<ContactSubject>(defaultSubject)

  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    const name = String(fd.get('name') ?? '')
    const phone = String(fd.get('phone') ?? '')
    const email = String(fd.get('email') ?? '')
    const message = String(fd.get('message') ?? '')
    const certification = String(fd.get('certification') ?? '')
    const topic = subjectLabels[subject]

    const body = [
      `שם: ${name}`,
      `טלפון: ${phone}`,
      `אימייל: ${email}`,
      `נושא: ${topic}`,
      ...(certification ? [`מוסד הכשרה קודם / תעודה: ${certification}`] : []),
      '',
      message,
    ].join('\n')

    const mailto = `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(`פנייה מהאתר — ${topic}`)}&body=${encodeURIComponent(body)}`
    window.location.href = mailto
    setSent(true)
  }

  if (sent) {
    return (
      <p className="rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 text-sm">
        תודה! נפתחה הודעת דוא״ל — שלחו אותה כדי שנקבל את הפנייה.
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
      <button
        type="submit"
        className="w-full sm:w-auto rounded-full bg-cyan text-navy font-semibold px-8 py-3 text-sm hover:brightness-90 transition"
      >
        {submitLabel}
      </button>
    </form>
  )
}
