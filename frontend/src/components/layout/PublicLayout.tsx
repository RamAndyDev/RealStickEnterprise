import { useEffect, useId, useState } from 'react';
import { Link, NavLink, Outlet } from 'react-router-dom';

import { PUBLIC_NAV } from '../../features/auth/nav';
import { useDocumentMeta } from '../seo/useDocumentMeta';

export function PublicLayout() {
  const [open, setOpen] = useState(false);
  const menuId = useId();

  useEffect(() => {
    if (!open) return undefined;
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpen(false);
    }
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [open]);

  return (
    <div className="flex min-h-screen flex-col bg-[#FDFAF4] text-[#1A1A18]">
      <a href="#main-content" className="skip-link">
        Skip to content
      </a>
      <header className="sticky top-0 z-30 border-b border-[#E0DDD5]/80 bg-[#FDFAF4]/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <Link to="/" className="group flex min-h-11 items-center gap-2" aria-label="RealStick home">
            <span className="font-serif text-2xl font-bold tracking-tight text-[#0D4F2E] sm:text-[1.7rem]">
              RealStick™
            </span>
          </Link>

          <nav className="hidden items-center gap-1 lg:flex" aria-label="Primary">
            {PUBLIC_NAV.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.path === '/'}
                className={({ isActive }) =>
                  [
                    'rounded-full px-3.5 py-2 text-sm font-medium transition',
                    'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1A7A4A]',
                    isActive
                      ? 'bg-[#0D4F2E] text-white'
                      : 'text-[#4A4A46] hover:bg-[#E6F4EC] hover:text-[#0D4F2E]',
                  ].join(' ')
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          <button
            type="button"
            className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg text-[#0D4F2E] lg:hidden"
            aria-expanded={open}
            aria-controls={menuId}
            aria-label={open ? 'Close menu' : 'Open menu'}
            onClick={() => setOpen((value) => !value)}
          >
            <span className="sr-only">{open ? 'Close menu' : 'Open menu'}</span>
            <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
              {open ? (
                <path d="M6 6l12 12M18 6L6 18" />
              ) : (
                <path d="M4 7h16M4 12h16M4 17h16" />
              )}
            </svg>
          </button>
        </div>

        {open ? (
          <div className="border-t border-[#E0DDD5] bg-[#FDFAF4] lg:hidden" id={menuId}>
            <nav className="mx-auto flex max-w-6xl flex-col gap-1 px-4 py-3 sm:px-6" aria-label="Mobile">
              {PUBLIC_NAV.map((item) => (
                <NavLink
                  key={item.path}
                  to={item.path}
                  end={item.path === '/'}
                  onClick={() => setOpen(false)}
                  className={({ isActive }) =>
                    [
                      'rounded-xl px-4 py-3 text-base font-medium',
                      'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1A7A4A]',
                      isActive ? 'bg-[#0D4F2E] text-white' : 'text-[#1A1A18] hover:bg-[#E6F4EC]',
                    ].join(' ')
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>
          </div>
        ) : null}
      </header>

      <main id="main-content" className="flex-1">
        <Outlet />
      </main>

      <footer className="mt-auto border-t border-[#E0DDD5] bg-[#0D4F2E] text-white">
        <div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 sm:px-6 md:grid-cols-3">
          <div>
            <div className="font-serif text-2xl font-bold">RealStick™</div>
            <p className="mt-2 text-sm text-white/70">Natural Popsicles &amp; Kulfi</p>
            <p className="mt-1 text-sm text-white/55">Real Fruits. Real Goodness.</p>
          </div>
          <nav aria-label="Footer">
            <div className="text-xs font-semibold uppercase tracking-[.14em] text-white/45">Explore</div>
            <ul className="mt-3 space-y-2 text-sm">
              {PUBLIC_NAV.map((item) => (
                <li key={item.path}>
                  <Link to={item.path} className="text-white/80 hover:text-white">
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
          <div>
            <div className="text-xs font-semibold uppercase tracking-[.14em] text-white/45">Visit</div>
            <p className="mt-3 text-sm text-white/70">Zero Artificial · Zero Preservatives</p>
            <p className="mt-6 text-xs text-white/40">
              <Link to="/login" className="hover:text-white/70">
                Staff / POS Login
              </Link>
            </p>
          </div>
        </div>
        <div className="border-t border-white/10 px-4 py-4 text-center text-[11px] text-white/35 sm:px-6">
          RealStick. Natural popsicles and kulfi.
        </div>
      </footer>
    </div>
  );
}

export function PublicPageMeta({
  title,
  description,
}: {
  title: string;
  description?: string;
}) {
  useDocumentMeta(title, description);
  return null;
}
