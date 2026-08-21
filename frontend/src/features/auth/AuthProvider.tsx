import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import type { Session } from '@supabase/supabase-js';

import { api, fetchCurrentProfile } from '../../lib/api';
import { supabase } from '../../lib/supabase';
import type { AuthProfile, UserRole } from '../../types/auth';
import {
  clearEmployeeSessionId,
  readEmployeeSessionId,
  storeEmployeeSessionId,
} from './employeeSession';
import { toLoginErrorMessage } from './loginError';

type AuthContextValue = {
  session: Session | null;
  profile: AuthProfile | null;
  loading: boolean;
  error: string | null;
  signIn: (identifier: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  requestPasswordReset: (email: string) => Promise<void>;
  updatePassword: (password: string) => Promise<void>;
  hasRole: (...roles: UserRole[]) => boolean;
  refreshProfile: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function toErrorMessage(error: unknown, fallback: string): string {
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const response = (error as { response?: { data?: { detail?: string } } }).response;
    if (response?.data?.detail) return response.data.detail;
  }
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [profile, setProfile] = useState<AuthProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadProfile = useCallback(async (
    activeSession: Session | null,
    options?: { rethrow?: boolean },
  ) => {
    if (!activeSession?.access_token) {
      setProfile(null);
      return;
    }
    try {
      const nextProfile = await fetchCurrentProfile();
      setProfile(nextProfile);
      setError(null);
    } catch (err) {
      setProfile(null);
      setError(
        options?.rethrow ? toLoginErrorMessage(err) : toErrorMessage(err, 'Unable to load profile'),
      );
      // Invalid/inactive application access: clear Supabase session.
      await supabase.auth.signOut();
      setSession(null);
      if (options?.rethrow) throw err;
    }
  }, []);

  useEffect(() => {
    let mounted = true;

    supabase.auth.getSession().then(async ({ data }) => {
      if (!mounted) return;
      setSession(data.session);
      await loadProfile(data.session);
      if (mounted) setLoading(false);
    });

    const { data: subscription } = supabase.auth.onAuthStateChange(async (event, nextSession) => {
      setSession(nextSession);
      if (event === 'SIGNED_OUT') {
        setProfile(null);
        setError(null);
        setLoading(false);
        return;
      }
      if (event === 'PASSWORD_RECOVERY') {
        setLoading(false);
        return;
      }
      setLoading(true);
      await loadProfile(nextSession);
      setLoading(false);
    });

    return () => {
      mounted = false;
      subscription.subscription.unsubscribe();
    };
  }, [loadProfile]);

  const signIn = useCallback(async (identifier: string, password: string) => {
    setError(null);
    try {
      const { data } = await api.post<{
        access_token: string;
        refresh_token: string;
        employee_session_id?: string | null;
      }>('/auth/login', { identifier, password });
      const { data: sessionData, error: sessionError } = await supabase.auth.setSession({
        access_token: data.access_token,
        refresh_token: data.refresh_token,
      });
      if (sessionError || !sessionData.session) {
        const message = toLoginErrorMessage(sessionError ?? new Error('Unable to start a session.'));
        setError(message);
        throw new Error(message);
      }
      storeEmployeeSessionId(data.employee_session_id);
      setSession(sessionData.session);
      await loadProfile(sessionData.session, { rethrow: true });
    } catch (err) {
      console.error('Sign-in failed', err);
      const message = toLoginErrorMessage(err);
      setError(message);
      throw new Error(message);
    }
  }, [loadProfile]);

  const signOut = useCallback(async () => {
    setError(null);
    const employeeSessionId = readEmployeeSessionId();
    try {
      if (profile?.role === 'EMPLOYEE' || employeeSessionId) {
        await api.post('/auth/employee-sessions/logout', {
          employee_session_id: employeeSessionId || undefined,
        });
      }
    } catch (err) {
      console.error('Employee session tracking failed on logout', err);
    } finally {
      clearEmployeeSessionId();
    }
    await supabase.auth.signOut();
    setSession(null);
    setProfile(null);
  }, [profile]);

  const requestPasswordReset = useCallback(async (email: string) => {
    const redirectTo = `${window.location.origin}/reset-password`;
    const { error: resetError } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo,
    });
    if (resetError) throw resetError;
  }, []);

  const updatePassword = useCallback(async (password: string) => {
    const { error: updateError } = await supabase.auth.updateUser({ password });
    if (updateError) throw updateError;
  }, []);

  const refreshProfile = useCallback(async () => {
    await loadProfile(session);
  }, [loadProfile, session]);

  const hasRole = useCallback(
    (...roles: UserRole[]) => (profile ? roles.includes(profile.role) : false),
    [profile],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      profile,
      loading,
      error,
      signIn,
      signOut,
      requestPasswordReset,
      updatePassword,
      hasRole,
      refreshProfile,
    }),
    [
      session,
      profile,
      loading,
      error,
      signIn,
      signOut,
      requestPasswordReset,
      updatePassword,
      hasRole,
      refreshProfile,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
