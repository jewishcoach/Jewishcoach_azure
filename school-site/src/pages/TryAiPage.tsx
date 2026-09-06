import { useState } from 'react'
import { APP_URL } from '../config'

const FAQ_ITEMS = [
  { q: 'האם זה מחליף אימון אישי?', a: 'התהליך מבוסס על אותה שיטה בדיוק, אך הוא מונגש דרך AI. הוא יכול לשמש כתהליך עצמאי או כהכנה לאימון אישי עם מאמן.' },
  { q: 'כמה זמן נמשך כל שלב?', a: 'כל שלב נמשך בדרך כלל בין 20 ל-40 דקות, אבל אפשר לעצור ולהמשיך בכל רגע.' },
  { q: 'אפשר לעצור באמצע?', a: 'כמובן. כל ההתקדמות נשמרת, ואפשר להמשיך בדיוק מהמקום שבו עצרת.' },
  { q: 'איך נשמר המידע שלי?', a: 'כל המידע מוצפן ונשמר באופן פרטי. רק אתה יכול לגשת לתוכן שלך.' },
  { q: 'צריך ניסיון קודם?', a: 'בכלל לא. התהליך מתאים לכל אחד, ללא ניסיון קודם באימון או בעבודה פנימית.' },
]

const BENEFITS = [
  { title: 'בדיוק בקצב שלך', text: 'אפשר לעצור מתי שצריך, לקחת נשימה, ולהמשיך בדיוק מאותה הנקודה.' },
  { title: 'שומר את המסע שלך', text: 'כל תובנה, החלטה והתקדמות נשמרות עבורך כדי לבנות קומה על גבי קומה.' },
  { title: 'זמינות בכל זמן', text: 'המלווה שלך מחכה לך בדיוק מתי שנוח לך ובכל רגע שעולה דילמה.' },
  { title: 'מרחב בטוח ונקי משיפוטיות', text: 'פרטיות מקסימלית שמאפשרת לך להיות בכנות מוחלטת, ללא מסכות.' },
]

const AI_FEATURES = [
  'זמינות 24/7 ללא תלות בלוח זמנים',
  'מסע רציף שזוכר את הדרך שעברת',
  'שאלות עומק מהשיטה, לא אלגוריתם גנרי',
  'תהליך מובנה ומוכח, לא צ\'אט פתוח',
  'תרגום העבודה הפנימית לתוצאות בשטח',
]

const PROCESS_ITEMS = [
  'לזהות את הדפוסים והחסמים שמעכבים אותך',
  'להבין לעומק מה באמת מנהל אותך מבפנים',
  'לגלות מחדש את הכוחות והאוצרות שכבר קיימים בתוכך',
  'לבנות את כרטיס המהות (כמ״ז) – המצפן האישי שלך לדרך',
  'לפתח אמון פנימי עמוק וביטחון בעצמך',
  'ליצור חזון ברור, מחובר ומדויק לחיים ולעסקים',
]

const TESTIMONIALS = [
  { quote: 'המצפן האישי שבניתי בתהליך הוא הדבר המשמעותי ביותר שעשיתי לעצמי בשנים האחרונות.', name: 'דנה ד׳', role: 'מתאמנ/ת', photo: '/images/testimonial-dana.png' },
  { quote: 'לאחר שנים של חיים על טייס אוטומטי, לראשונה עצרתי ושאלתי את עצמי את השאלות הנכונות.', name: 'אורי פנחסי', role: 'מתאמן', photo: '/images/testimonial-ori.png' },
  { quote: 'הייתי סקפטית לגבי AI, אבל התהליך הרגיש אמיתי מהרגע הראשון. כל שאלה הייתה בדיוק במקום הנכון.', name: 'מיכל ד׳', role: 'מתאמנ/ת', photo: '/images/testimonial-michal.png' },
]

export function TryAiPage() {
  return (
    <>
      {/* ── Hero — side-by-side: tree left, text right ── */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0">
          <img src="/images/hero-bg.png" alt="" className="w-full h-full object-cover" />
          <div className="absolute inset-0 bg-black/10" />
        </div>
        <div className="relative mx-auto max-w-7xl flex flex-col lg:flex-row items-center px-4 py-10 sm:py-14 gap-4 lg:gap-8">
          <div className="flex-shrink-0 w-full lg:w-1/2 flex justify-center">
            <img src="/images/hero-tree.png" alt="" className="w-full max-w-[500px] h-auto" />
          </div>
          <div className="flex-1 text-center lg:text-right">
            <h1 className="font-display text-[38px] sm:text-[52px] md:text-[64px] lg:text-[76px] text-navy leading-[1.05] mb-5">
              מהיום אפשר לעבור את תהליך
              <br />
              האימון היהודי - מבית בני גל גם אונליין
            </h1>
            <div className="text-lg sm:text-xl md:text-2xl lg:text-[32px] text-navy/80 leading-relaxed">
              <p>אותה שיטה.</p>
              <p>אותם העקרונות.</p>
              <p>אותו מסע של התבוננות, בחירה וצמיחה.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ── CTA bar ── */}
      <section className="bg-navy text-center py-7 px-4">
        <a
          href={APP_URL}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center justify-center rounded-full bg-cyan text-navy text-xl font-medium px-16 py-3.5 hover:brightness-90 transition"
        >
          התחלת האימון
        </a>
        <p className="text-white text-lg mt-3">עכשיו בקצב שלך, בזמן שלך, ובכל מקום.</p>
      </section>

      {/* ── מהו אימון יהודי? ── */}
      <section id="what" className="bg-cream px-4 py-14 sm:py-20">
        <div className="mx-auto max-w-4xl text-center">
          <h2 className="font-display text-4xl sm:text-5xl lg:text-[100px] text-navy mb-8 leading-tight">מהו אימון יהודי?</h2>

          <div className="relative mx-auto max-w-[1000px] rounded-xl overflow-hidden shadow-lg mb-8">
            <img src="/images/video-thumb.png" alt="בני גל מסביר על השיטה" className="w-full" />
            <div className="absolute inset-0 bg-black/20 flex items-center justify-center">
              <div className="size-16 sm:size-20 rounded-full bg-cream/90 shadow-lg flex items-center justify-center">
                <img src="/images/play-icon.svg" alt="נגן" className="size-5 sm:size-6 mr-[-2px]" />
              </div>
            </div>
            <div className="absolute bottom-0 right-0 bg-white px-4 py-2.5 rounded-tl-lg">
              <span className="text-sm font-medium text-navy/80">בני גל מסביר על השיטה · 4:32</span>
            </div>
          </div>

          <p className="text-navy/80 text-base sm:text-lg lg:text-[22px] leading-[1.8] max-w-4xl mx-auto">
            שיטת האימון היהודי (BSD) פותחה על ידי בני גל מתוך 25 שנות עבודה עם אלפי מתאמנים. השיטה משלבת את תורת הנפש היהודית עם פרקטיקה יישומית, ותוביל אותך למסע של התבוננות, זיהוי דפוסים, בניית חזון אישי והפיכתו לדרך חיים.
          </p>
        </div>
      </section>

      {/* ── למה אונליין? ── */}
      <section className="px-4 py-14 sm:py-20">
        <div className="mx-auto max-w-6xl">
          <h2 className="font-display text-4xl sm:text-5xl lg:text-[100px] text-navy text-center mb-10 leading-tight">
            למה לעבור את התהליך אונליין?
          </h2>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {BENEFITS.map((b) => (
              <article key={b.title} className="bg-white rounded-2xl p-7 shadow-[0_0_7px_rgba(0,0,0,0.11)] text-center flex flex-col items-center gap-3 border-t-[3px] border-teal">
                <h3 className="text-xl font-bold text-teal">{b.title}</h3>
                <p className="text-navy/80 leading-relaxed text-lg">{b.text}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ── איך AI משתלב בתוך השיטה? ── */}
      <section className="relative bg-navy px-4 py-14 sm:py-20 overflow-visible">
        {/* Speech bubble — floats above the section */}
        <div className="absolute left-1/2 -translate-x-1/2 -top-16 z-10">
          <div className="bg-white rounded-2xl shadow-lg px-8 py-5 max-w-sm text-center">
            <p className="text-brown text-sm sm:text-base leading-relaxed">
              כשיש בהירות הבחירה נעשית פשוטה יותר.
              <br />
              <strong>AI שמנגיש את שיטת האימון של בני גל, צעד אחר צעד.</strong>
            </p>
          </div>
        </div>

        <div className="mx-auto max-w-7xl flex flex-col lg:flex-row-reverse items-end gap-0 pt-12 lg:pt-0">
          {/* Visually LEFT — Benny portrait cutout, overflows upward */}
          <div className="flex-shrink-0 lg:w-[40%] relative self-end lg:-mt-28">
            <img src="/images/benny-cutout.png" alt="בני גל" className="w-full h-auto max-w-[500px] mx-auto drop-shadow-2xl" />
          </div>

          {/* Visually RIGHT — AI features */}
          <div className="flex-1 px-4 py-10 sm:px-12 sm:py-14 flex flex-col justify-center">
            <h2 className="font-display text-3xl sm:text-4xl lg:text-[70px] text-cyan mb-4 text-right leading-tight">
              איך AI משתלב בתוך השיטה?
            </h2>
            <p className="text-white/80 text-base sm:text-lg lg:text-[24px] leading-relaxed mb-8 text-right">
              כאן ה-AI לא מאלתר. הוא פועל בתוך מסגרת אימון סדורה ומוכחת
            </p>
            <div className="space-y-6">
              {AI_FEATURES.map((text) => (
                <div key={text} className="flex flex-row-reverse items-center justify-end gap-3">
                  <p className="text-white text-lg lg:text-[24px] leading-relaxed">{text}</p>
                  <div className="size-6 shrink-0">
                    <img src="/images/check-icon.svg" alt="" className="size-full" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── מה התהליך יאפשר לי? ── */}
      <section id="benefits" className="bg-[#fff8e9] px-4 py-14 sm:py-20">
        <div className="mx-auto max-w-5xl">
          <div className="flex flex-col items-center mb-8">
            <img src="/images/tree-faq.png" alt="" className="w-40 sm:w-52 h-auto mb-4" />
            <h2 className="font-display text-4xl sm:text-5xl lg:text-[100px] text-navy text-center leading-tight">
              מה התהליך יאפשר לי?
            </h2>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            {PROCESS_ITEMS.map((text) => (
              <div key={text} className="bg-navy rounded-xl px-6 py-8 text-white/85 font-medium text-base sm:text-lg lg:text-xl leading-snug flex flex-row-reverse items-center justify-end gap-3">
                <span>{text}</span>
                <span className="text-cyan text-xl shrink-0">◇</span>
              </div>
            ))}
          </div>
          <p className="text-brown-muted text-center mt-8 leading-relaxed text-lg font-medium">
            אם זיהית את עצמך בלפחות אחד מהמשפטים האלה
            <br />
            הגיע הזמן שנדבר.
          </p>
        </div>
      </section>

      {/* ── מתאמנים מספרים ── */}
      <section className="px-4 py-14 sm:py-20">
        <div className="mx-auto max-w-5xl">
          <h2 className="font-display text-5xl sm:text-6xl lg:text-[100px] text-navy text-center mb-10 leading-tight">
            מתאמנים מספרים
          </h2>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {TESTIMONIALS.map((t) => (
              <blockquote key={t.name} className="bg-white/95 border border-brown/10 p-7 flex flex-col">
                <p className="text-brown text-base lg:text-lg leading-relaxed mb-6 flex-1 text-right">
                  {t.quote}
                </p>
                <footer className="flex items-center justify-end gap-3 border-t border-brown/10 pt-4">
                  <div className="text-right">
                    <p className="font-medium text-brown text-sm">{t.name}</p>
                    <p className="text-brown-muted text-xs">{t.role}</p>
                  </div>
                  <div className="size-12 rounded-full overflow-hidden shadow-[0_0_4px_rgba(0,0,0,0.25)] shrink-0">
                    <img src={t.photo} alt={t.name} className="w-full h-full object-cover" />
                  </div>
                </footer>
              </blockquote>
            ))}
          </div>
        </div>
      </section>

      {/* ── שאלות נפוצות ── */}
      <section id="faq" className="px-4 py-14 sm:py-20">
        <div className="mx-auto max-w-4xl">
          <div className="flex flex-col items-center gap-4 mb-10">
            <img src="/images/benny-explain.png" alt="" className="w-44 sm:w-52 h-auto" />
            <h2 className="font-display text-5xl sm:text-6xl lg:text-[100px] text-navy text-center leading-tight">
              שאלות נפוצות
            </h2>
          </div>
          <div className="space-y-5">
            {FAQ_ITEMS.map((item) => (
              <FaqItem key={item.q} question={item.q} answer={item.a} />
            ))}
          </div>
        </div>
      </section>

      {/* ── Feature cards — overlap into CTA section ── */}
      <div className="relative z-10 px-4 -mb-32 sm:-mb-36">
        <div className="mx-auto max-w-5xl grid gap-6 sm:grid-cols-3">
          <FeatureCard
            icon="/images/icon-book.svg"
            title="ספר המסע האישי"
            text="כל התובנות והבחירות שלך נשמרות לאורך הדרך."
          />
          <FeatureCard
            icon="/images/icon-save.svg"
            title="נשמר אוטומטית"
            text="אפשר לעצור ולהמשיך בדיוק מהמקום שבו הפסקת."
          />
          <FeatureCard
            icon="/images/icon-lock.svg"
            title="פרטי לחלוטין"
            text="כל המידע נשמר עבורך. ועבורך בלבד."
          />
        </div>
      </div>

      {/* ── CTA סופי ── */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0">
          <img src="/images/cta-bg.png" alt="" className="w-full h-full object-cover" />
          <div className="absolute inset-0 bg-gradient-to-b from-white via-white/60 to-transparent" style={{ height: '35%' }} />
          <div className="absolute inset-0 bg-black/25" />
        </div>
        <div className="relative z-10 mx-auto max-w-xl text-center text-white px-4 pt-52 sm:pt-60 pb-24 sm:pb-32">
          <h2 className="font-bold text-3xl sm:text-[40px] lg:text-[68px] leading-tight mb-4">
            הגיע הזמן להתחיל
            <br />
            את המסע שלך.
          </h2>
          <p className="text-xl sm:text-2xl lg:text-[34px] font-light leading-relaxed mb-10">
            השיטה של בני גל,
            <br />
            עכשיו זמינה עבורך בכל רגע.
          </p>
          <a
            href={APP_URL}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center justify-center rounded-full bg-cyan text-navy text-xl font-medium px-16 py-3.5 hover:brightness-90 transition"
          >
            התחלת האימון
          </a>
        </div>
      </section>

    </>
  )
}

/* ── Local Components ── */

function FaqItem({ question, answer }: { question: string; answer: string }) {
  const [open, setOpen] = useState(false)

  return (
    <div
      className="bg-cream-warm shadow-[0_0_4px_rgba(0,0,0,0.25)] overflow-hidden cursor-pointer"
      onClick={() => setOpen((v) => !v)}
    >
      <div className="flex items-center justify-between px-6 py-5 gap-4">
        <img
          src="/images/faq-chevron.svg"
          alt=""
          className={`size-6 shrink-0 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
        />
        <p className="font-semibold text-navy text-lg sm:text-xl lg:text-[24px] text-right flex-1">{question}</p>
      </div>
      {open && (
        <div className="px-6 pb-5 text-navy/70 leading-relaxed border-t border-navy/10 pt-4 text-right">
          {answer}
        </div>
      )}
    </div>
  )
}

function FeatureCard({ icon, title, text }: { icon: string; title: string; text: string }) {
  return (
    <article className="bg-white/80 border border-brown/10 rounded-xl p-8 text-center flex flex-col items-center gap-4">
      <div className="size-7">
        <img src={icon} alt="" className="size-full" />
      </div>
      <h3 className="font-semibold text-2xl sm:text-[36px] text-teal-light">{title}</h3>
      <p className="text-navy/80 text-lg lg:text-[20px] leading-relaxed">{text}</p>
    </article>
  )
}
