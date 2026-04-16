import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { ArrowRight, Scale } from 'lucide-react';
import { TERMS_SECTIONS_EN, TERMS_SECTIONS_HE } from '../legal/termsOfUseSections';

const COLORS = {
  bg: '#F0F1F3',
  card: '#FFFFFF',
  text: '#2E3A56',
  textMuted: '#5A6B8A',
  accent: '#2E3A56',
  border: '#E2E4E8',
  shadow: '0 1px 2px rgba(46, 58, 86, 0.06)',
};

interface TermsOfUsePageProps {
  onBack: () => void;
}

export const TermsOfUsePage = ({ onBack }: TermsOfUsePageProps) => {
  const { t, i18n } = useTranslation();
  const isHe = i18n.language === 'he';
  const sections = isHe ? TERMS_SECTIONS_HE : TERMS_SECTIONS_EN;

  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  return (
    <div
      className="flex flex-col h-full overflow-hidden min-h-0"
      dir={i18n.dir() as 'ltr' | 'rtl'}
      style={{ background: COLORS.bg }}
    >
      <header
        className="flex-shrink-0 flex items-center gap-3 px-4 py-3 md:px-6 border-b"
        style={{ background: COLORS.card, borderColor: COLORS.border, boxShadow: COLORS.shadow }}
      >
        <button
          type="button"
          onClick={onBack}
          className="flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium transition-colors hover:bg-gray-100"
          style={{ color: COLORS.textMuted }}
        >
          <ArrowRight className="w-4 h-4" />
          {t('privacy.back')}
        </button>
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <Scale className="w-5 h-5 flex-shrink-0" style={{ color: COLORS.accent }} />
          <h1 className="text-base md:text-lg font-semibold truncate" style={{ color: COLORS.text }}>
            {t('sidebar.terms')}
          </h1>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto custom-scrollbar">
        <div className="max-w-3xl mx-auto px-4 md:px-8 py-6 md:py-10 pb-24">
          <p className="text-sm mb-8" style={{ color: COLORS.textMuted }}>
            {t('terms.updated')}
          </p>

          <article className="space-y-8">
            {sections.map((section) => (
              <section key={section.id} className="rounded-xl p-5 md:p-6" style={{ background: COLORS.card, boxShadow: COLORS.shadow }}>
                <h2 className="text-lg font-semibold mb-3" style={{ color: COLORS.text }}>
                  {section.title}
                </h2>
                <div className="space-y-3 text-sm leading-relaxed" style={{ color: COLORS.text }}>
                  {section.paragraphs.map((p, i) => (
                    <p key={i}>{p}</p>
                  ))}
                </div>
              </section>
            ))}
          </article>

          <div className="mt-10 pt-6 border-t border-[#E2E4E8]">
            <button
              type="button"
              onClick={onBack}
              className="w-full md:w-auto px-6 py-3 rounded-xl text-sm font-medium text-white transition-opacity hover:opacity-90"
              style={{ background: COLORS.accent }}
            >
              {t('privacy.back')}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
};
