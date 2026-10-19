import { Hero, PrimaryButton, Section } from '../components/ui'
import { ContactForm } from '../components/ContactForm'
import { personalTrackContent } from '../data/pdfContent'

export function PersonalTrackPage() {
  const c = personalTrackContent

  return (
    <>
      <Hero title={c.heroTitle} body={c.heroBody}>
        <PrimaryButton to="/programs/find-coach">שיחת הכרות קצרה</PrimaryButton>
      </Hero>

      <Section title={c.whereTitle}>
        <p>{c.whereP1}</p>
        <p>{c.whereP2}</p>
      </Section>

      <Section title={c.howTitle} className="bg-white">
        <p>{c.howIntro}</p>
        <ul>
          {c.howSteps.map((step) => (
            <li key={step.title}>
              <strong>{step.title}</strong> {step.text}
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
        <div className="mx-auto max-w-xl">
          <p className="text-center text-navy/60 text-sm mb-4">{c.closingP1}</p>
          <p className="text-center text-navy/60 text-sm mb-8">{c.closingP2}</p>
          <ContactForm defaultSubject="personal-coach" submitLabel="חזרו אלי לתיאום שיחה" />
        </div>
      </section>
    </>
  )
}
