import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './i18n'
import App from './App.tsx'
import { I18nextProvider } from 'react-i18next'
import i18n from './i18n'
import { ClerkProvider } from '@clerk/clerk-react'

// Get Clerk Publishable Key
const PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY

if (!PUBLISHABLE_KEY) {
  throw new Error("Missing Publishable Key")
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ClerkProvider publishableKey={PUBLISHABLE_KEY}>
      <I18nextProvider i18n={i18n}>
        <App />
      </I18nextProvider>
    </ClerkProvider>
  </StrictMode>,
)
