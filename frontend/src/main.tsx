import './pwaInstallCapture'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { registerSW } from 'virtual:pwa-register'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { I18nextProvider } from 'react-i18next'
import './index.css'
import './i18n'
import i18n from './i18n'
import App from './App.tsx'
import CoachFeedbackSurveyPage from './pages/CoachFeedbackSurveyPage.tsx'
import { ClerkProviderBridge } from './ClerkProviderBridge'

registerSW({ immediate: true })

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <I18nextProvider i18n={i18n}>
      <ClerkProviderBridge>
        <BrowserRouter>
          <Routes>
            <Route path="/coach-feedback-survey" element={<CoachFeedbackSurveyPage />} />
            <Route path="/*" element={<App />} />
          </Routes>
        </BrowserRouter>
      </ClerkProviderBridge>
    </I18nextProvider>
  </StrictMode>,
)
