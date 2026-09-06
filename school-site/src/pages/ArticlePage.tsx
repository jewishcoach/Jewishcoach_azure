import { useParams } from 'react-router-dom'
import articlesData from '../data/articles.json'
import { normalizeSlug, type Article, type ContentBlock } from '../data/types'

const articles = articlesData as Article[]

function findArticle(slugParam: string | undefined): Article | undefined {
  if (!slugParam) return undefined
  const normalized = normalizeSlug(slugParam)
  return articles.find((a) => normalizeSlug(a.slug) === normalized)
}

function ArticleBody({ article }: { article: Article }) {
  const blocks: ContentBlock[] =
    article.blocks && article.blocks.length > 0
      ? article.blocks
      : article.body.split(/\n\n+/).filter(Boolean).map((text) => ({ type: 'paragraph' as const, text }))

  return (
    <div className="prose-site text-navy/80">
      {article.featuredImage ? (
        <figure className="mb-8 overflow-hidden rounded-xl border border-navy/10">
          <img
            src={article.featuredImage}
            alt=""
            className="w-full h-auto max-h-96 object-cover"
            loading="lazy"
          />
        </figure>
      ) : null}
      {blocks.map((block, index) => {
        if (block.type === 'image') {
          return (
            <figure key={`${block.src}-${index}`} className="my-8 overflow-hidden rounded-xl border border-navy/10">
              <img
                src={block.src}
                alt={block.alt ?? ''}
                className="w-full h-auto"
                loading="lazy"
              />
            </figure>
          )
        }
        return <p key={`${block.text.slice(0, 40)}-${index}`}>{block.text}</p>
      })}
    </div>
  )
}

export function ArticlePage() {
  const { slug } = useParams<{ slug: string }>()
  const article = findArticle(slug)

  if (!article) {
    return (
      <section className="px-4 py-20 text-center">
        <p className="text-navy/60 mb-4">המאמר לא נמצא.</p>
        <a href="/insights" className="text-teal font-medium">
          חזרה למאמרים
        </a>
      </section>
    )
  }

  return (
    <article className="px-4 py-12">
      <div className="mx-auto max-w-2xl">
        <a href="/insights" className="text-sm text-teal font-medium mb-6 inline-block">
          → חזרה למאמרים
        </a>
        <h1 className="font-display text-4xl text-navy mb-8">{article.title}</h1>
        <ArticleBody article={article} />
      </div>
    </article>
  )
}
