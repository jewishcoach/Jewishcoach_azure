// The SPA fallback answers every unknown path with 200, so noindex keeps them out of Google.
export function NotFoundPage() {
  return (
    <section className="px-4 py-20 text-center">
      <meta name="robots" content="noindex" />
      <title>הדף לא נמצא · BSD</title>
      <p className="text-navy/60 mb-4">הדף שחיפשת לא נמצא.</p>
      <a href="/" className="text-teal font-medium">
        חזרה לדף הבית
      </a>
    </section>
  )
}
