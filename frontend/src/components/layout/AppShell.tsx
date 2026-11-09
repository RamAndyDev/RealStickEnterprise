import { useEffect, useId, useState } from 'react';
import { LogOut, Menu, X } from 'lucide-react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';

import { useAuth } from '../../features/auth/AuthProvider';
import { navForRole } from '../../features/auth/nav';

export function AppShell() {
  const { profile, signOut } = useAuth();
  const { pathname } = useLocation();
  const ownerAuditEnabled =
    profile?.role === 'FRANCHISE_OWNER' ? profile.franchise_owner_audit_enabled === true : true;
  const items = navForRole(profile?.role, { franchiseOwnerAuditEnabled: ownerAuditEnabled });
  const isPos = pathname === '/pos';
  const [drawerOpen, setDrawerOpen] = useState(false);
  const drawerId = useId();

  useEffect(() => {
    setDrawerOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!isPos) return undefined;

    const htmlStyle = document.documentElement.style;
    const bodyStyle = document.body.style;
    const previousHtml = {
      height: htmlStyle.height,
      overflow: htmlStyle.overflow,
    };
    const previousBody = {
      height: bodyStyle.height,
      minHeight: bodyStyle.minHeight,
      overflow: bodyStyle.overflow,
    };

    htmlStyle.height = '100dvh';
    htmlStyle.overflow = 'hidden';
    bodyStyle.height = '100dvh';
    bodyStyle.minHeight = '0';
    bodyStyle.overflow = 'hidden';

    return () => {
      htmlStyle.height = previousHtml.height;
      htmlStyle.overflow = previousHtml.overflow;
      bodyStyle.height = previousBody.height;
      bodyStyle.minHeight = previousBody.minHeight;
      bodyStyle.overflow = previousBody.overflow;
    };
  }, [isPos]);

  useEffect(() => {
    if (!drawerOpen) return undefined;
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') setDrawerOpen(false);
    }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [drawerOpen]);

  const navLinks = (
    <nav
      className={
        isPos
          ? 'scrollbar-hidden min-h-0 flex-1 space-y-1 overflow-y-auto overscroll-contain p-3'
          : 'scrollbar-hidden space-y-1 p-3 md:min-h-0 md:flex-1 md:overflow-y-auto md:overscroll-contain'
      }
    >
      {items.map((item) => (
        <NavLink
          key={`${item.path}-${item.label}`}
          to={item.path}
          end={item.path === '/dashboard'}
          onClick={() => setDrawerOpen(false)}
          className={({ isActive }) =>
            [
              'flex min-h-11 w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm',
              isActive
                ? 'bg-white/15 text-white'
                : 'text-white/70 hover:bg-white/10 hover:text-white',
            ].join(' ')
          }
        >
          {item.label}
        </NavLink>
      ))}
    </nav>
  );

  const userBlock = (
    <div className="shrink-0 border-t border-white/10 p-4">
      <div className="text-sm">{profile?.full_name}</div>
      <div className="mb-1 text-xs text-white/45">{profile?.role}</div>
      {profile?.role === 'EMPLOYEE' && profile.login_id ? (
        <div className="mb-3 truncate text-xs text-white/35">{profile.login_id}</div>
      ) : profile?.email ? (
        <div className="mb-3 truncate text-xs text-white/35">{profile.email}</div>
      ) : (
        <div className="mb-3" />
      )}
      <button
        type="button"
        onClick={() => void signOut()}
        className="flex min-h-11 items-center gap-2 text-xs text-white/55 hover:text-white"
      >
        <LogOut size={14} />
        Sign out
      </button>
    </div>
  );

  return (
    <div
      className={
        isPos
          ? 'flex h-[100vh] h-dvh flex-col overflow-hidden overscroll-none bg-[#FDFAF4] md:flex-row'
          : 'min-h-dvh bg-[#FDFAF4] md:flex md:h-dvh md:overflow-hidden'
      }
    >
      {isPos ? (
        <header className="flex shrink-0 items-center gap-3 bg-[#0D4F2E] px-3 py-2 text-white md:hidden">
          <button
            type="button"
            className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg"
            aria-expanded={drawerOpen}
            aria-controls={drawerId}
            aria-label={drawerOpen ? 'Close navigation' : 'Open navigation'}
            onClick={() => setDrawerOpen((value) => !value)}
          >
            {drawerOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
          <div className="font-serif text-xl font-bold">RealStick™</div>
        </header>
      ) : null}

      {isPos && drawerOpen ? (
        <button
          type="button"
          className="fixed inset-0 z-30 bg-black/40 md:hidden"
          aria-label="Close navigation"
          onClick={() => setDrawerOpen(false)}
        />
      ) : null}

      <aside
        id={isPos ? drawerId : undefined}
        className={
          isPos
            ? `fixed inset-y-0 left-0 z-40 flex h-[100vh] h-dvh max-h-dvh w-60 flex-col bg-[#0D4F2E] text-white transition-transform md:static md:h-full md:max-h-none md:w-44 md:shrink-0 md:translate-x-0 lg:w-52 xl:w-60 ${
                drawerOpen ? 'translate-x-0' : '-translate-x-full'
              }`
            : `flex w-full flex-col bg-[#0D4F2E] text-white md:h-full md:w-60 md:shrink-0`
        }
      >
        <div className="shrink-0 border-b border-white/10 px-5 py-5">
          <div className="font-serif text-2xl font-bold">RealStick™</div>
          <div className="mt-1 text-[10px] uppercase tracking-[.18em] text-white/45">
            Enterprise
          </div>
        </div>
        {navLinks}
        {userBlock}
      </aside>

      <main
        className={
          isPos
            ? 'flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden'
            : 'min-w-0 flex-1 p-5 md:min-h-0 md:overflow-y-auto md:p-8'
        }
      >
        <Outlet />
      </main>
    </div>
  );
}
