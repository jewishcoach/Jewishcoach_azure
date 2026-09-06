import { Hero, Section } from '../components/ui'
import testimonialsData from '../data/testimonials.json'
import pressData from '../data/press.json'
import type { PressData, Testimonial } from '../data/types'

const testimonials = testimonialsData as Testimonial[]
const press = pressData as PressData

function testimonialLabel(item: Testimonial): string {
  if (item.kind === 'press') {
    return `מקור: ${item.author}`
  }
  if (item.company) {
    return `${item.author} · ${item.company}`
  }
  return item.author
}

export function TestimonialsPage() {
  return (
    <>
      <Hero
        title="המלצות ועיתונות"
        subtitle="עדויות מקוראים, בוגרים וכלי תקשורת על השיטה ועל בית הספר."
      />

      <Section title="מהאנשים">
        <ul className="space-y-6 list-none p-0">
          {testimonials.map((item) => (
            <li
              key={`${item.author}-${item.quote.slice(0, 32)}`}
              className="rounded-xl border border-brown/10 bg-white p-5 shadow-[0_0_4px_rgba(0,0,0,0.1)]"
            >
              <p className="text-navy/80 text-sm leading-relaxed">«{item.quote}»</p>
              <p className="mt-3 text-xs font-medium text-teal">{testimonialLabel(item)}</p>
            </li>
          ))}
        </ul>
      </Section>

      {press.pdfs.length > 0 ? (
        <Section title="כתבות PDF" className="bg-white">
          <ul className="space-y-4 list-none p-0">
            {press.pdfs.map((pdf) => (
              <li key={pdf.url}>
                <a
                  href={pdf.url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 text-teal font-medium hover:underline"
                >
                  {pdf.title} — פתיחת PDF
                </a>
              </li>
            ))}
          </ul>
        </Section>
      ) : null}

      {press.items.length > 0 ? (
        <Section title="מן העיתונות">
          <p className="text-sm text-navy/60 mb-8 max-w-2xl">
            הצצה לעולם האימון היהודי מנקודת מבטה של העיתונות — כולל קישורים לכתבות המקוריות.
          </p>
          <ul className="grid gap-8 sm:grid-cols-2 list-none p-0">
            {press.items.map((item) => (
              <li
                key={`${item.title}-${item.url}`}
                className="overflow-hidden rounded-xl border border-brown/10 bg-white shadow-[0_0_4px_rgba(0,0,0,0.1)]"
              >
                {item.image ? (
                  <div className="h-28 overflow-hidden bg-cream-warm flex items-center justify-center p-3">
                    <img src={item.image} alt="" className="max-h-full max-w-full object-contain" loading="lazy" />
                  </div>
                ) : null}
                <div className="p-5">
                  <h3 className="font-display text-2xl text-navy mb-1">{item.title}</h3>
                  {item.source || item.published ? (
                    <p className="text-xs text-teal font-medium mb-3">
                      {[item.source, item.published].filter(Boolean).join(' · ')}
                    </p>
                  ) : null}
                  {item.summary ? (
                    <p className="text-sm text-navy/70 leading-relaxed mb-4">{item.summary}</p>
                  ) : null}
                  {item.url && item.url !== '#' ? (
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-sm font-medium text-teal hover:underline"
                    >
                      קרא עוד ←
                    </a>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        </Section>
      ) : null}
    </>
  )
}
