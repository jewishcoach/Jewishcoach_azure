import { useState } from 'react'
import { Link, Outlet, useLocation } from 'react-router-dom'
import { Menu, X } from 'lucide-react'

const nav: { to: string; label: string; external?: boolean }[] = [
  { to: '/', label: 'בית' },
  { to: '/bsd-ai', label: 'אימון יהודי AI' },
  { to: '/programs/personal', label: 'מסלולים' },
  { to: '/book', label: 'הספר' },
  { to: '/api/blog', label: 'בלוג', external: true },
  { to: '/testimonials', label: 'המלצות' },
  { to: '/about', label: 'אודות' },
  { to: '/contact', label: 'צור קשר' },
]

function NavLink({ item, className, onClick }: { item: typeof nav[number]; className: string; onClick?: () => void }) {
  if (item.external) {
    return <a href={item.to} className={className} onClick={onClick}>{item.label}</a>
  }
  return <Link to={item.to} className={className} onClick={onClick}>{item.label}</Link>
}

export function SiteLayout() {
  const [open, setOpen] = useState(false)
  const location = useLocation()

  return (
    <div className="min-h-screen flex flex-col" dir="rtl">
      <header className="sticky top-0 z-50 bg-navy">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <Link to="/" className="flex items-center gap-2 shrink-0">
            <img src="/images/logo.svg" alt="BSD" className="h-10 w-auto" />
          </Link>

          <nav className="hidden lg:flex items-center gap-6 text-sm font-medium">
            {nav.map((item) => (
              <NavLink
                key={item.to}
                item={item}
                className={
                  location.pathname === item.to ||
                  (item.to !== '/' && location.pathname.startsWith(item.to))
                    ? 'text-cyan'
                    : 'text-cyan/70 hover:text-cyan'
                }
              />
            ))}
          </nav>

          <div className="flex items-center gap-2">
            <button
              type="button"
              className="lg:hidden p-2 text-cyan"
              onClick={() => setOpen((v) => !v)}
              aria-label="תפריט"
            >
              {open ? <X size={22} /> : <Menu size={22} />}
            </button>
          </div>
        </div>

        {open ? (
          <nav className="lg:hidden border-t border-white/10 px-4 py-3 flex flex-col gap-2 bg-navy">
            {nav.map((item) => (
              <NavLink
                key={item.to}
                item={item}
                onClick={() => setOpen(false)}
                className="py-2 text-cyan/80 font-medium hover:text-cyan"
              />
            ))}
          </nav>
        ) : null}
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <footer className="bg-navy text-sm">
        <div className="mx-auto max-w-6xl px-4 py-10 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <p className="font-semibold text-white mb-2">בית הספר לאימון יהודי BSD</p>
            <p className="leading-relaxed text-white/50">
              ממשיכים את שיטת האימון היהודי שהקים בני גל ז״ל — כלים, תהליכים ועומק.
            </p>
          </div>
          <div>
            <p className="font-semibold text-white mb-2">מסלולים</p>
            <ul className="space-y-1 text-white/50">
              <li>
                <Link to="/programs/personal" className="hover:text-cyan">
                  אימון אישי
                </Link>
              </li>
              <li>
                <Link to="/programs/find-coach" className="hover:text-cyan">
                  התאמת מאמן
                </Link>
              </li>
              <li>
                <Link to="/programs/certified-coaches" className="hover:text-cyan">
                  התמחות למאמנים
                </Link>
              </li>
            </ul>
          </div>
          <div>
            <p className="font-semibold text-white mb-2">עוד</p>
            <ul className="space-y-1 text-white/50">
              <li>
                <Link to="/testimonials" className="hover:text-cyan">
                  המלצות ועיתונות
                </Link>
              </li>
              <li>
                <Link to="/media" className="hover:text-cyan">
                  וידאו והאזנה
                </Link>
              </li>
              <li>
                <a href="/api/blog" className="hover:text-cyan">
                  בלוג
                </a>
              </li>
              <li>
                <Link to="/about" className="hover:text-cyan">
                  אודות בני גל ז״ל
                </Link>
              </li>
            </ul>
          </div>
          <div>
            <p className="font-semibold text-white mb-2">יצירת קשר</p>
            <Link to="/contact" className="text-cyan hover:text-cyan/80 font-medium">
              טופס יצירת קשר ←
            </Link>
          </div>
        </div>
        <div className="border-t border-white/10 text-center py-4 text-xs text-cyan/60">
          © {new Date().getFullYear()} אימון יהודי | שיטת BSD של בני גל. כל הזכויות שמורות.
        </div>
      </footer>

      {/* WhatsApp floating button */}
      <a
        href="https://wa.me/972523288607"
        target="_blank"
        rel="noreferrer"
        className="fixed bottom-6 left-6 z-50 size-16 rounded-full shadow-lg hover:scale-110 transition-transform"
        aria-label="WhatsApp"
      >
        <img src="/images/whatsapp.svg" alt="" className="size-full" />
      </a>
    </div>
  )
}
