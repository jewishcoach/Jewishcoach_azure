import { useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'

/* ── Hero ── */

type HeroProps = {
  eyebrow?: string
  title: string
  subtitle?: string
  body?: string
  children?: ReactNode
  image?: string
}

export function Hero({ eyebrow, title, subtitle, body, children, image }: HeroProps) {
  return (
    <section className="relative overflow-hidden bg-cream px-4 pt-8 pb-0">
      <div className="relative mx-auto max-w-3xl text-center">
        {eyebrow ? (
          <p className="mb-3 text-sm font-medium tracking-wide text-teal">{eyebrow}</p>
        ) : null}
        <h1 className="font-display text-4xl sm:text-5xl md:text-6xl text-navy leading-tight mb-4">
          {title}
        </h1>
        {subtitle ? (
          <p className="text-lg sm:text-xl text-navy/80 leading-relaxed max-w-2xl mx-auto">
            {subtitle}
          </p>
        ) : null}
        {body ? (
          <p className="mt-3 text-base sm:text-lg text-brown-muted leading-relaxed max-w-2xl mx-auto">
            {body}
          </p>
        ) : null}
        {children ? <div className="mt-6 flex flex-wrap justify-center gap-3">{children}</div> : null}
      </div>
      {image ? (
        <div className="mx-auto max-w-xl mt-6">
          <img src={image} alt="" className="w-full h-auto" />
        </div>
      ) : null}
    </section>
  )
}

/* ── Section ── */

export function Section({
  id,
  title,
  children,
  className = '',
  dark = false,
}: {
  id?: string
  title?: string
  children: ReactNode
  className?: string
  dark?: boolean
}) {
  const bg = dark ? 'bg-navy text-white' : ''
  return (
    <section id={id} className={`px-4 py-12 sm:py-16 ${bg} ${className}`}>
      <div className="mx-auto max-w-4xl">
        {title ? (
          <h2 className={`font-display text-4xl sm:text-5xl font-normal text-center mb-8 ${dark ? 'text-white' : 'text-navy'}`}>
            {title}
          </h2>
        ) : null}
        <div className={dark ? '' : 'prose-site text-navy/80'}>{children}</div>
      </div>
    </section>
  )
}

/* ── Buttons ── */

export function PrimaryButton({
  to,
  href,
  children,
  variant = 'cyan',
}: {
  to?: string
  href?: string
  children: ReactNode
  variant?: 'cyan' | 'outline' | 'dark'
}) {
  const base = 'inline-flex items-center justify-center rounded-full px-8 py-3 text-lg font-medium transition'
  const styles = {
    cyan: `${base} bg-cyan text-navy hover:brightness-90`,
    outline: `${base} border-2 border-navy/20 text-navy hover:bg-navy/5`,
    dark: `${base} bg-navy text-white hover:bg-navy/90`,
  }

  if (to) return <Link to={to} className={styles[variant]}>{children}</Link>
  if (href)
    return (
      <a href={href} className={styles[variant]} target={href.startsWith('http') ? '_blank' : undefined} rel="noreferrer">
        {children}
      </a>
    )
  return <button type="button" className={styles[variant]}>{children}</button>
}

/* ── Benefit Card ── */

export function BenefitCard({ title, text }: { title: string; text: string }) {
  return (
    <article className="bg-white rounded-2xl p-6 shadow-[0_0_7px_rgba(0,0,0,0.11)] text-center flex flex-col items-center gap-2">
      <h3 className="text-xl font-bold text-teal">{title}</h3>
      <p className="text-navy/80 leading-relaxed max-w-[220px]">{text}</p>
    </article>
  )
}

/* ── AI Feature Bullet ── */

export function AiBullet({ icon, text }: { icon?: string; text: string }) {
  return (
    <div className="flex flex-col items-center gap-3 text-center">
      {icon ? (
        <div className="size-9">
          <img src={icon} alt="" className="size-full" />
        </div>
      ) : null}
      <p className="text-white text-xl sm:text-2xl leading-relaxed">{text}</p>
    </div>
  )
}

/* ── Dark Pill (for "מה התהליך יאפשר לי") ── */

export function DarkPill({ text }: { text: string }) {
  return (
    <div className="bg-navy rounded-lg px-6 py-4 text-white text-center font-medium leading-snug">
      {text}
    </div>
  )
}

/* ── Testimonial Card ── */

export function TestimonialCard({
  quote,
  name,
  role,
  image,
}: {
  quote: string
  name: string
  role: string
  image?: string
}) {
  return (
    <blockquote className="bg-white/95 border border-brown/10 p-8 sm:p-10 max-w-lg mx-auto">
      <p className="text-brown text-lg leading-relaxed mb-6 text-right">
        {quote}
      </p>
      <footer className="flex items-center justify-end gap-4 border-t border-brown/10 pt-5">
        <div className="text-right">
          <p className="font-medium text-brown">{name}</p>
          <p className="text-brown-muted text-sm">{role}</p>
        </div>
        {image ? (
          <img src={image} alt={name} className="size-12 rounded-full object-cover shadow" />
        ) : null}
      </footer>
    </blockquote>
  )
}

/* ── FAQ Accordion ── */

export function FaqItem({ question, answer }: { question: string; answer?: string }) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <div
      className="bg-cream-warm shadow-[0_0_4px_rgba(0,0,0,0.25)] overflow-hidden cursor-pointer"
      onClick={() => setIsOpen((v) => !v)}
    >
      <div className="flex items-center justify-between px-6 py-5">
        <p className="font-semibold text-navy text-lg sm:text-xl text-right flex-1">{question}</p>
        <img
          src="/images/faq-chevron.svg"
          alt=""
          className={`size-6 shrink-0 transition-transform ${isOpen ? 'rotate-180' : ''}`}
        />
      </div>
      {isOpen && answer ? (
        <div className="px-6 pb-5 text-navy/70 leading-relaxed border-t border-navy/10 pt-4">
          {answer}
        </div>
      ) : null}
    </div>
  )
}

/* ── Feature Card (ספר המסע) ── */

export function FeatureCard({
  icon,
  title,
  text,
}: {
  icon: string
  title: string
  text: string
}) {
  return (
    <article className="bg-white border border-brown/10 rounded-xl p-8 text-center flex flex-col items-center gap-4">
      <div className="size-6">
        <img src={icon} alt="" className="size-full" />
      </div>
      <h3 className="font-semibold text-2xl text-teal-light">{title}</h3>
      <p className="text-navy/80 leading-relaxed">{text}</p>
    </article>
  )
}

/* ── Program Card Grid (legacy, updated styling) ── */

export function ProgramCardGrid({
  items,
}: {
  items: { title: string; description: string; href: string; cta: string }[]
}) {
  return (
    <div className="grid gap-6 sm:grid-cols-2 max-w-4xl mx-auto">
      {items.map((item) => (
        <article
          key={item.href}
          className="rounded-2xl border border-brown/10 bg-white p-6 shadow-[0_0_7px_rgba(0,0,0,0.11)] flex flex-col"
        >
          <h3 className="font-display text-2xl text-navy mb-3">{item.title}</h3>
          <p className="text-navy/70 text-sm leading-relaxed flex-1 mb-5">{item.description}</p>
          <Link
            to={item.href}
            className="text-teal font-semibold text-sm hover:text-teal-light"
          >
            {item.cta} ←
          </Link>
        </article>
      ))}
    </div>
  )
}

/* ── Quote Block ── */

export function QuoteBlock({ text, source }: { text: string; source: string }) {
  return (
    <blockquote className="mx-auto max-w-2xl text-center px-4 py-10">
      <p className="font-display text-2xl sm:text-3xl text-navy leading-relaxed mb-4">"{text}"</p>
      <footer className="text-sm text-brown-muted">— {source}</footer>
    </blockquote>
  )
}
