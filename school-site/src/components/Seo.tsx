const SITE = 'https://www.bsdcoaching.co.il'

// React 19 hoists these into <head>; each page gets its own title, description and canonical URL.
export function Seo({ title, description, path }: { title: string; description: string; path: string }) {
  return (
    <>
      <title>{title}</title>
      <meta name="description" content={description} />
      <link rel="canonical" href={`${SITE}${path}`} />
    </>
  )
}
