import './pwaInstallCapture'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { registerSW } from 'virtual:pwa-register'
import './index.css'
import './i18n'
import App from './App.tsx'

registerSW({ immediate: true })
import { I18nextProvider } from 'react-i18next'
import i18n from './i18n'
import { ClerkProviderBridge } from './ClerkProviderBridge'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <I18nextProvider i18n={i18n}>
      <ClerkProviderBridge>
        <App />
      </ClerkProviderBridge>
    </I18nextProvider>
  </StrictMode>,
)
