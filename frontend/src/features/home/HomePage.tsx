import { Navigate } from 'react-router-dom';

import { useAuth } from '../../features/auth/AuthProvider';
import { AdminDashboardPage } from '../dashboard/AdminDashboardPage';
import { OwnerDashboardPage } from '../dashboard/OwnerDashboardPage';

export function HomePage() {
  const { profile } = useAuth();

  if (profile?.role === 'EMPLOYEE') {
    return <Navigate to="/pos" replace />;
  }

  if (profile?.role === 'SYSTEM_ADMIN') {
    return <AdminDashboardPage />;
  }

  if (profile?.role === 'FRANCHISE_OWNER') {
    return <OwnerDashboardPage />;
  }

  return <Navigate to="/login" replace />;
}
