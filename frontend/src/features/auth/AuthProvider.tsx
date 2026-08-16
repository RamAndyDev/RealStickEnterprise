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

  const loadProfile = useCallback(async (activeSession: Session | null) => {
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
      setError(toErrorMessage(err, 'Unable to load profile'));
      // Invalid/inactive application access: clear Supabase session.
      await supabase.auth.signOut();
      setSession(null);
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
      }>('/auth/login', { identifier, password });
      const { data: sessionData, error: sessionError } = await supabase.auth.setSession({
        access_token: data.access_token,
        refresh_token: data.refresh_token,
      });
      if (sessionError || !sessionData.session) {
        const message = sessionError?.message || 'Unable to start a session.';
        setError(message);
        throw new Error(message);
      }
      setSession(sessionData.session);
      await loadProfile(sessionData.session);
    } catch (err) {
      const message = toErrorMessage(err, 'Unable to sign in. Check your credentials.');
      setError(message);
      throw err instanceof Error ? err : new Error(message);
    }
  }, [loadProfile]);

  const signOut = useCallback(async () => {
    setError(null);
    await supabase.auth.signOut();
    setSession(null);
    setProfile(null);
  }, []);

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
