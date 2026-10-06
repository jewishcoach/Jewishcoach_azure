import { Route, Routes, useParams, Navigate } from 'react-router-dom'
import { SiteLayout } from './components/SiteLayout'
import { HomePage } from './pages/HomePage'
import { PersonalTrackPage } from './pages/PersonalTrackPage'
import { FindCoachPage } from './pages/FindCoachPage'
import { CertifiedCoachesPage } from './pages/CertifiedCoachesPage'
import { BookPage } from './pages/BookPage'
import { ContactPage } from './pages/ContactPage'
import { AboutPage } from './pages/AboutPage'
import { InsightsPage } from './pages/InsightsPage'
import { ArticlePage } from './pages/ArticlePage'
import { TryAiPage } from './pages/TryAiPage'
import { TestimonialsPage } from './pages/TestimonialsPage'

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
    <Routes>
      <Route element={<SiteLayout />}>
        <Route index element={<HomePage />} />
        <Route path="programs/personal" element={<PersonalTrackPage />} />
        <Route path="programs/find-coach" element={<FindCoachPage />} />
        <Route path="programs/certified-coaches" element={<CertifiedCoachesPage />} />
        <Route path="book" element={<BookPage />} />
        <Route path="contact" element={<ContactPage />} />
        <Route path="about" element={<AboutPage />} />
        <Route path="insights" element={<InsightsPage />} />
        <Route path="insights/:slug" element={<ArticlePage />} />
        <Route path="bsd-ai" element={<TryAiPage />} />
        <Route path="testimonials" element={<TestimonialsPage />} />
      </Route>
      <Route path="blog/:slug" element={<BlogRedirect />} />
    </Routes>
  )
}
