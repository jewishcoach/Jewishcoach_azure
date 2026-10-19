import { Hero, PrimaryButton, Section } from '../components/ui'
import { ContactForm } from '../components/ContactForm'
import { certifiedCoachesContent } from '../data/pdfContent'

export function CertifiedCoachesPage() {
  const c = certifiedCoachesContent

  return (
    <>
      <Hero title={c.heroTitle} body={c.heroBody}>
        <PrimaryButton to="/contact">תנאי קבלה וסילבוס</PrimaryButton>
      </Hero>

      <Section title={c.whyTitle}>
        <p>{c.whyP1}</p>
        <p>{c.whyP2}</p>
      </Section>

      <Section title={c.programTitle} className="bg-white">
        <p>{c.programIntro}</p>
        <ul>
          {c.programItems.map((item) => (
            <li key={item.title}>
              <strong>{item.title}</strong> {item.text}
            </li>
          ))}
        </ul>
      </Section>

      <Section title={c.audienceTitle}>
        <p>{c.audienceIntro}</p>
        <ul>
          {c.audienceBullets.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </Section>

      <section className="px-4 py-14 bg-cream-warm">
        <div className="mx-auto max-w-lg">
          <h2 className="font-display text-3xl text-navy text-center mb-4">{c.closingTitle}</h2>
          <p className="text-center text-navy/60 text-sm mb-6">{c.closingText}</p>
          <ContactForm
            defaultSubject="certified-program"
            submitLabel="מועמדות לבדיקת התאמה"
            showCertificationField
          />
        </div>
      </section>
    </>
  )
}
