import { lazy, Suspense } from 'react'
import { Route, Routes, useParams, Navigate } from 'react-router-dom'
import { SiteLayout } from './components/SiteLayout'
import { HomePage } from './pages/HomePage'
import { NotFoundPage } from './pages/NotFoundPage'

// Every page but the home page loads on demand, so the first visit downloads only what it shows
const page = <K extends string>(load: () => Promise<Record<K, React.ComponentType>>, name: K) =>
  lazy(() => load().then((m) => ({ default: m[name] })))
const PersonalTrackPage = page(() => import('./pages/PersonalTrackPage'), 'PersonalTrackPage')
const FindCoachPage = page(() => import('./pages/FindCoachPage'), 'FindCoachPage')
const CertifiedCoachesPage = page(() => import('./pages/CertifiedCoachesPage'), 'CertifiedCoachesPage')
const BookPage = page(() => import('./pages/BookPage'), 'BookPage')
const ContactPage = page(() => import('./pages/ContactPage'), 'ContactPage')
const AboutPage = page(() => import('./pages/AboutPage'), 'AboutPage')
const TryAiPage = page(() => import('./pages/TryAiPage'), 'TryAiPage')
const TestimonialsPage = page(() => import('./pages/TestimonialsPage'), 'TestimonialsPage')
const MediaPage = page(() => import('./pages/MediaPage'), 'MediaPage')

function BlogRedirect() {
  const { slug } = useParams()
  if (slug) {
    window.location.href = `/api/blog/${slug}`
    return null
  }
  return <Navigate to="/api/blog" replace />
}

export default function App() {
  return (
    <Suspense fallback={null}>
      <Routes>
        <Route element={<SiteLayout />}>
          <Route index element={<HomePage />} />
          <Route path="programs/personal" element={<PersonalTrackPage />} />
          <Route path="programs/find-coach" element={<FindCoachPage />} />
          <Route path="programs/certified-coaches" element={<CertifiedCoachesPage />} />
          <Route path="book" element={<BookPage />} />
          <Route path="contact" element={<ContactPage />} />
          <Route path="about" element={<AboutPage />} />
          <Route path="bsd-ai" element={<TryAiPage />} />
          <Route path="testimonials" element={<TestimonialsPage />} />
          <Route path="media" element={<MediaPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
        <Route path="blog/:slug" element={<BlogRedirect />} />
      </Routes>
    </Suspense>
  )
}
