import { Hero, PrimaryButton, Section } from '../components/ui'
import { bookContent } from '../data/pdfContent'

export function BookPage() {
  const c = bookContent

  return (
    <>
      <Hero title={c.heroTitle} body={c.heroBody}>
        <PrimaryButton href="https://bsdcoach.com/post/the-books">הספר / לקריאת פרק ראשון</PrimaryButton>
      </Hero>

      <Section title={c.structureTitle}>
        <p>{c.structureP1}</p>
        <p>{c.structureP2}</p>
      </Section>

      <Section title={c.insideTitle} className="bg-white">
        <p>{c.insideIntro}</p>
        <ul>
          {c.insideItems.map((item) => (
            <li key={item.title}>
              <strong>{item.title}</strong> {item.text}
            </li>
          ))}
        </ul>
      </Section>

      <Section title="למי הספר מיועד?">
        <ul>
          {c.audienceBullets.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        <p className="mt-6 text-center text-navy/60">{c.closingText}</p>
        <p className="mt-6 text-center">
          <PrimaryButton href="https://bsdcoach.com/post/the-books">לסל / רכישה מאובטחת</PrimaryButton>
        </p>
      </Section>
    </>
  )
}
