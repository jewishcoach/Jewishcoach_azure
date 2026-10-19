import { Hero } from '../components/ui'
import { ContactForm } from '../components/ContactForm'
import { CONTACT_EMAIL, CONTACT_PHONE } from '../config'
import { contactContent } from '../data/pdfContent'
import { Seo } from '../components/Seo'

export function ContactPage() {
  const c = contactContent

  return (
    <>
      <Seo title="צור קשר | בית הספר לאימון יהודי BSD" description="שאלות על אימון אישי, הכשרת מאמנים או הספר? השאירו פרטים ונחזור אליכם." path="/contact" />
      <Hero title={c.title} subtitle={c.intro} />

      <section className="px-4 py-12">
        <div className="mx-auto max-w-5xl grid gap-10 lg:grid-cols-2">
          <div>
            <h2 className="font-display text-2xl text-navy mb-2">טופס יצירת קשר</h2>
            <p className="text-sm text-navy/50 mb-4">{c.formNote}</p>
            <ContactForm submitLabel="פנייה" />
          </div>
          <div className="text-sm text-navy/70 space-y-4">
            <h2 className="font-display text-2xl text-navy mb-2">
              {c.directTitle}
            </h2>
            <p className="text-navy/50">{c.directNote}</p>
            {CONTACT_PHONE ? (
              <p>
                <strong>{c.phoneLabel}</strong> {CONTACT_PHONE}
              </p>
            ) : null}
            <p>
              <strong>{c.hoursLabel}</strong> {c.hours}
            </p>
            <p>
              <strong>{c.emailLabel}</strong>{' '}
              <a href={`mailto:${CONTACT_EMAIL}`} className="text-teal">
                {CONTACT_EMAIL}
              </a>
            </p>
          </div>
        </div>
      </section>
    </>
  )
}
