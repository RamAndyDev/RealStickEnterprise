import { Navigate, Outlet } from 'react-router-dom';

import { useAuth } from '../../features/auth/AuthProvider';
import { staffLandingPath } from '../../features/auth/nav';
import type { UserRole } from '../../types/auth';

type ProtectedRouteProps = {
  roles?: UserRole[];
};

export function ProtectedRoute({ roles }: ProtectedRouteProps) {
  const { loading, session, profile, hasRole } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#FDFAF4] text-sm text-[#8A8A84]">
        Restoring session…
      </div>
    );
  }

  if (!session || !profile) {
    return <Navigate to="/login" replace />;
  }

  if (roles && roles.length > 0 && !hasRole(...roles)) {
    return <Navigate to={staffLandingPath(profile.role)} replace />;
  }

  return <Outlet />;
}
