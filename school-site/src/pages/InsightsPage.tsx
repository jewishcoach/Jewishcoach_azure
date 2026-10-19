import { Link } from 'react-router-dom'
import { Hero } from '../components/ui'
import articlesData from '../data/articles.json'
import { articlePath, type Article } from '../data/types'

const articles = articlesData as Article[]

export function InsightsPage() {
  return (
    <>
      <Hero
        title="תובנות ומאמרים"
        subtitle="מאמרים, תובנות וכלים מעולם האימון היהודי בשיטת BSD."
      />

      <section className="px-4 py-12">
        <ul className="mx-auto max-w-3xl divide-y divide-navy/10">
          {articles.map((article) => (
            <li key={article.slug} className="py-6">
              <Link to={articlePath(article.slug)} className="group flex gap-5">
                {article.featuredImage ? (
                  <div className="hidden sm:block shrink-0 w-28 h-20 overflow-hidden rounded-lg border border-navy/10 bg-cream-warm">
                    <img
                      src={article.featuredImage}
                      alt=""
                      className="w-full h-full object-cover"
                      loading="lazy"
                    />
                  </div>
                ) : null}
                <div className="min-w-0 flex-1">
                  <h2 className="font-display text-2xl text-navy group-hover:text-teal mb-2">
                    {article.title}
                  </h2>
                  <p className="text-sm text-navy/70 leading-relaxed line-clamp-3">{article.excerpt}</p>
                  <span className="inline-block mt-2 text-sm font-medium text-teal">קרא עוד ←</span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </>
  )
}
