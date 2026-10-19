export type ContentBlock =
  | { type: 'paragraph'; text: string }
  | { type: 'image'; src: string; alt?: string }

export type Article = {
  title: string
  slug: string
  excerpt: string
  body: string
  featuredImage?: string
  blocks?: ContentBlock[]
}

export type Testimonial = {
  quote: string
  author: string
  company?: string
  link?: string
  kind: 'press' | 'reader' | 'other'
}

export type PressItem = {
  title: string
  summary: string
  image: string
  url: string
  published?: string
  source?: string
}

export type PressData = {
  intro?: string
  items: PressItem[]
  pdfs: { title: string; url: string; image?: string; summary?: string }[]
}

export function normalizeSlug(value: string): string {
  try {
    return decodeURIComponent(value)
  } catch {
    return value
  }
}

export function articlePath(slug: string): string {
  return `/insights/${encodeURIComponent(normalizeSlug(slug))}`
}
