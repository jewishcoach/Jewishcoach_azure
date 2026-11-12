import { StrictMode } from 'react'
import { createRoot, hydrateRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App'

const app = (
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>
)
const container = document.getElementById('root')!
// Pages are prerendered at build time (scripts/prerender.mjs): hydrate their HTML; the shell (spa.html, unknown paths) renders
if (container.firstElementChild) hydrateRoot(container, app)
else createRoot(container).render(app)
