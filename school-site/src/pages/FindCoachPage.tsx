import { Hero, Section } from '../components/ui'
import { ContactForm } from '../components/ContactForm'
import { findCoachContent } from '../data/pdfContent'
import { Seo } from '../components/Seo'

export function FindCoachPage() {
  const c = findCoachContent

  return (
    <>
      <Seo title="התאמת מאמן אישי מבוגרי BSD אימון יהודי" description="מחפשים לעבור אימון אישי? נתאים לכם מאמן מוסמך מבוגרי בית הספר לאימון יהודי BSD." path="/programs/find-coach" />
      <Hero title={c.heroTitle} body={c.heroBody} />

      <Section>
        <ul>
          {c.benefits.map((item) => (
            <li key={item.title}>
              <strong>{item.title}</strong> {item.text}
            </li>
          ))}
        </ul>
      </Section>

      <section className="px-4 py-14 bg-white">
        <div className="mx-auto max-w-lg">
          <ContactForm defaultSubject="personal-coach" submitLabel="שתתאימו לי מאמן אישי" />
          <p className="text-xs text-navy/50 mt-4">{c.fieldHint}</p>
        </div>
      </section>
    </>
  )
}
