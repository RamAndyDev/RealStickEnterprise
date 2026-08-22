import { Navigate, Outlet } from 'react-router-dom';

import { useAuth } from '../../features/auth/AuthProvider';
import { canAccessAudit, staffLandingPath } from '../../features/auth/nav';

export function AuditProtectedRoute() {
  const { loading, session, profile } = useAuth();

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

  if (!canAccessAudit(profile.role, profile.franchise_owner_audit_enabled)) {
    return <Navigate to={staffLandingPath(profile.role)} replace />;
  }

  return <Outlet />;
}
