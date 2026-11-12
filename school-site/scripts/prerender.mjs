// After `vite build` (client) and `vite build --ssr src/entry-server.tsx --outDir dist-ssr`:
// write dist/<route>/index.html for every page, with the page's own <title>, description and canonical in <head>
// and its full HTML in #root (main.tsx hydrates it). dist/spa.html keeps the empty shell for unknown paths
// (staticwebapp.config.json navigationFallback), so a 404 never shows the home page's content.
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const dist = path.join(root, 'dist')
const { render, ROUTES } = await import(pathToFileURL(path.join(root, 'dist-ssr', 'entry-server.js')).href)

const template = fs.readFileSync(path.join(dist, 'index.html'), 'utf8')
fs.writeFileSync(path.join(dist, 'spa.html'), template)

// React 19 hoists <title>/<meta>/<link> rendered inside pages; outside a full <html> render they lead the output
const HEAD_TAG = /<(title)[^>]*>[\s\S]*?<\/title>|<(meta|link)\b[^>]*\/?>/g

const problems = []
for (const route of ROUTES) {
  const html = await render(route)
  const firstContent = html.search(/<(?!title|meta|link|\/title)[a-z]/i)
  const lead = firstContent > 0 ? html.slice(0, firstContent) : ''
  // Only the head tags move; Suspense markers (<!--$-->) and anything else in the lead stay, or hydration breaks
  const body = firstContent > 0 ? lead.replace(HEAD_TAG, '') + html.slice(firstContent) : html
  const headTags = (lead.match(HEAD_TAG) || []).join('\n    ')
  const title = (headTags.match(/<title[^>]*>([\s\S]*?)<\/title>/) || [])[1]
  if (!title) problems.push(`${route}: no <title>`)
  if (!/name="description"/.test(headTags)) problems.push(`${route}: no description`)
  if (!/<h1[\s>]/.test(body)) problems.push(`${route}: no <h1>`)
  const page = template
    .replace(/<title>[\s\S]*?<\/title>/, headTags)
    .replace('<div id="root"></div>', `<div id="root">${body}</div>`)
  const out = route === '/' ? path.join(dist, 'index.html') : path.join(dist, route.slice(1), 'index.html')
  fs.mkdirSync(path.dirname(out), { recursive: true })
  fs.writeFileSync(out, page)
  const words = body.replace(/<[^>]+>/g, ' ').split(/\s+/).filter(Boolean).length
  console.log(`prerendered ${route.padEnd(30)} ${String(words).padStart(5)} words  ${title || ''}`)
}
fs.rmSync(path.join(root, 'dist-ssr'), { recursive: true, force: true })
if (problems.length) {
  console.error('prerender problems:\n  ' + problems.join('\n  '))
  process.exit(1)
}
