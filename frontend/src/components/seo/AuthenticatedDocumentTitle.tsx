import { useAuth } from '../../features/auth/AuthProvider';
import { documentTitleForRole } from './documentTitle';
import { useDocumentMeta } from './useDocumentMeta';

export function AuthenticatedDocumentTitle() {
  const { profile } = useAuth();
  useDocumentMeta(documentTitleForRole(profile?.role));
  return null;
}
