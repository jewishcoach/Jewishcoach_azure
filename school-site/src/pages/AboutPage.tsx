import { Hero, PrimaryButton, Section } from '../components/ui'
import { LEGACY_URL } from '../config'
import { Seo } from '../components/Seo'

export function AboutPage() {
  return (
    <>
      <Seo title="אודות בית הספר לאימון יהודי ומורשת בני גל ז״ל" description="ממשיכים את שיטת האימון היהודי (BSD) שהקים בני גל ז״ל: שפה, כלים ותהליכים." path="/about" />
      <Hero
        title="אודות בית הספר"
        subtitle="ממשיכים את שיטת האימון היהודי (BSD) — שפה, כלים ותהליכים — שהקים בני גל ז״ל."
      />

      <Section>
        <p>
          בית הספר לאימון יהודי BSD הוא הבית הראשון בעולם להכשרת מאמנים בשיטה יהודית. למעלה מ-25
          שנות פעילות, אלפי בוגרים, וספר רב-המכר שתורגם לשפות רבות.
        </p>
        <p>
          <strong>שיטת BSD</strong> כוללת יסודות, שפה מקצועית, ארגז כלים (חזון, פער, דפוסים, כמ״ז,
          מדדים ועוד), ותהליכים מגוונים — ביניהם <strong>תהליך השיבה</strong>, מודל לכיוונון וגילוי
          לפני עבודת האימון העמוקה.
        </p>
        <p>
          האפליקציה Jewish Coach AI מציעה טעימה מ«תהליך השיבה» — כלי דיגיטלי להיכרות, לא תחליף
          לאימון מלא או להכשרת מאמנים.
        </p>
      </Section>

      <section className="px-4 py-12 bg-white text-center">
        <p className="text-navy/60 mb-6 max-w-xl mx-auto">
          לביוגרפיה המלאה, ארגז הכלים, שערי משנה ומורשת בני גל ז״ל —
        </p>
        <PrimaryButton href={LEGACY_URL}>מורשת בני גל ז״ל ←</PrimaryButton>
      </section>
    </>
  )
}
