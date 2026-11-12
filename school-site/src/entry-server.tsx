// Build-time prerender (scripts/prerender.mjs): every page as real HTML for Google, hydrated in the browser.
// Before this (2026-11-12) Google got the same 6-word shell for every page — one title, no description, no H1 —
// and had never even crawled /bsd-ai ("URL is unknown to Google"); only the server-rendered blog got impressions.
import { StrictMode } from 'react'
import { prerender } from 'react-dom/static'
import { StaticRouter } from 'react-router'
import App from './App'

export const ROUTES = [
  '/',
  '/programs/personal',
  '/programs/find-coach',
  '/programs/certified-coaches',
  '/book',
  '/contact',
  '/about',
  '/bsd-ai',
  '/testimonials',
  '/media',
]

export async function render(url: string): Promise<string> {
  // prerender waits for every lazy page (Suspense) to resolve, so the HTML holds the full page
  const { prelude } = await prerender(
    <StrictMode>
      <StaticRouter location={url}>
        <App />
      </StaticRouter>
    </StrictMode>,
  )
  return new Response(prelude).text()
}
