import { Link } from 'react-router-dom'
import { Hero, PrimaryButton, Section, ProgramCardGrid, QuoteBlock } from '../components/ui'
import { ContactForm } from '../components/ContactForm'
import { homeContent, programsFromPdf } from '../data/pdfContent'
import { APP_URL } from '../config'
import { Seo } from '../components/Seo'

export function HomePage() {
  const c = homeContent

  return (
    <>
      <Seo title="בית הספר לאימון יהודי BSD | הכשרת מאמנים ואימון אישי" description="בית הספר לאימון יהודי בשיטת BSD: הכשרת מאמנים, אימון אישי, ומורשת בני גל ז״ל." path="/" />
      {/* ── Hero ── */}
      <Hero title={c.heroTitle} subtitle={c.heroSubtitle} body={c.heroBody}>
        <PrimaryButton to="/programs/personal">המסלולים שלנו</PrimaryButton>
        <PrimaryButton to="/bsd-ai" variant="outline">נסה את ה-AI</PrimaryButton>
      </Hero>

      {/* ── שאיפה ── */}
      <Section title={c.aspirationTitle}>
        <p>{c.aspirationP1}</p>
        <p>{c.aspirationP2}</p>
      </Section>

      {/* ── סמכות — השיטה ── */}
      <Section title={c.authorityTitle} className="bg-white">
        <p>{c.authorityP1}</p>
        <p>{c.processIntro}</p>
        <ul>
          {c.processBullets.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        <p className="text-center mt-6">
          <Link to="/about" className="text-teal font-semibold hover:underline">
            {c.aboutLink}
          </Link>
        </p>
      </Section>

      {/* ── מסלולים ── */}
      <section className="px-4 py-12 sm:py-16 bg-cream-warm">
        <h2 className="font-display text-4xl sm:text-5xl text-navy text-center mb-8">
          {c.programsTitle}
        </h2>
        <ProgramCardGrid items={[...programsFromPdf]} />
      </section>

      {/* ── AI טיזר ── */}
      <section className="bg-navy px-4 py-14 sm:py-20">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="font-display text-4xl sm:text-5xl text-white mb-4">
            אימון יהודי AI
          </h2>
          <p className="text-white/80 text-lg sm:text-xl leading-relaxed mb-4">
            מהיום אפשר לעבור את תהליך האימון היהודי גם אונליין.
            <br />
            אותה שיטה. אותם העקרונות. אותו מסע של התבוננות, בחירה וצמיחה.
          </p>
          <p className="text-white/60 text-base leading-relaxed mb-8">
            AI שמנגיש את שיטת האימון של בני גל, צעד אחר צעד — זמינות 24/7, מסע רציף שזוכר את הדרך, ותהליך מובנה ומוכח.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <PrimaryButton to="/bsd-ai" variant="cyan">גלה עוד</PrimaryButton>
            <PrimaryButton href={APP_URL} variant="outline">התחל עכשיו</PrimaryButton>
          </div>
        </div>
      </section>

      {/* ── ציטוט ── */}
      <QuoteBlock text={c.quote.text} source={c.quote.source} />

      {/* ── סגירה + טופס ── */}
      <section className="px-4 py-14 bg-white border-t border-navy/5">
        <div className="mx-auto max-w-xl text-center mb-8">
          <h2 className="font-display text-4xl text-navy mb-3">{c.closingTitle}</h2>
          <p className="text-navy/60 text-sm leading-relaxed">{c.closingText}</p>
        </div>
        <div className="mx-auto max-w-lg px-4">
          <ContactForm compact submitLabel="שלחו לי פרטים" />
        </div>
      </section>
    </>
  )
}
