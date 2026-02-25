import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { LanguageSwitcher } from './components/LanguageSwitcher';
import './i18n';

function App() {
  const { t } = useTranslation();
  const [message, setMessage] = useState('');

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white p-8">
      {/* Header */}
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <img src="/bsd-logo.png" alt="BSD אימון יהודי" className="h-14 object-contain" />
          <LanguageSwitcher />
        </div>

        {/* Simple Test Card */}
        <div className="bg-white/10 backdrop-blur-md rounded-2xl p-8 shadow-xl">
          <h2 className="text-2xl font-bold mb-4 text-amber-400">
            🎉 Success! The app is working!
          </h2>
          <p className="text-lg mb-4">
            If you can see this, the basic setup is correct.
          </p>
          
          {/* Test Input */}
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder={t('chat.placeholder')}
            className="w-full px-4 py-3 rounded-lg bg-white/20 border border-amber-500/30 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-amber-500"
          />
          
          {message && (
            <div className="mt-4 p-4 bg-amber-500/20 rounded-lg">
              <p className="text-amber-300">You typed: {message}</p>
            </div>
          )}
        </div>

        {/* Status Info */}
        <div className="mt-8 text-center text-gray-400 text-sm">
          <p>✅ React is rendering</p>
          <p>✅ Tailwind CSS is working</p>
          <p>✅ i18next is loaded</p>
          <p>✅ State management works</p>
        </div>
      </div>
    </div>
  );
}

export default App;






