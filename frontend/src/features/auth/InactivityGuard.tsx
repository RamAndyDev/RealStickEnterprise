import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { useAuth } from './AuthProvider';
import {
  ACTIVITY_EVENTS,
  INACTIVITY_TIMEOUT_MS,
  INACTIVITY_WARNING_MESSAGE,
  shouldLogout,
  shouldWarn,
} from './inactivity';

export function InactivityGuard() {
  const { session, signOut } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const lastActivity = useRef(Date.now());
  const [warning, setWarning] = useState(false);

  useEffect(() => {
    lastActivity.current = Date.now();
    setWarning(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!session) {
      setWarning(false);
      return undefined;
    }

    lastActivity.current = Date.now();

    const markActivity = () => {
      lastActivity.current = Date.now();
      setWarning(false);
    };

    for (const eventName of ACTIVITY_EVENTS) {
      window.addEventListener(eventName, markActivity, { passive: true });
    }

    const timer = window.setInterval(() => {
      const idle = Date.now() - lastActivity.current;
      if (shouldLogout(idle)) {
        window.clearInterval(timer);
        void signOut().then(() => navigate('/login', { replace: true }));
        return;
      }
      setWarning(shouldWarn(idle));
    }, 1000);

    return () => {
      for (const eventName of ACTIVITY_EVENTS) {
        window.removeEventListener(eventName, markActivity);
      }
      window.clearInterval(timer);
    };
  }, [session, signOut, navigate]);

  if (!session || !warning) return null;

  return (
    <div
      role="status"
      className="fixed inset-x-0 top-0 z-[60] bg-[#D97706] px-4 py-3 text-center text-sm font-semibold text-white shadow"
    >
      {INACTIVITY_WARNING_MESSAGE}
      <span className="ml-2 font-normal text-white/80">
        Move or tap to stay signed in. Timeout is {INACTIVITY_TIMEOUT_MS / 60000} minutes.
      </span>
    </div>
  );
}
