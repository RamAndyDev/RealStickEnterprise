import { useQuery } from '@tanstack/react-query';

import {
  Badge,
  Button,
  EmptyState,
  ErrorBanner,
  LoadingBlock,
  Modal,
} from '../../components/ui';
import { listEmployeeSessions } from '../../lib/usersApi';
import type { ManagedUser } from '../../types/user';
import {
  formatActivityDate,
  formatActivityTime,
  logoutDisplay,
  sessionStatusLabel,
  toEmployeeActivityError,
} from './employeeActivity';
import { employeeUserIdLabel } from './labels';

export function EmployeeActivityDialog({
  employee,
  onClose,
}: {
  employee: Pick<ManagedUser, 'id' | 'full_name' | 'login_id'>;
  onClose: () => void;
}) {
  const query = useQuery({
    queryKey: ['owner-employee-sessions', employee.id],
    queryFn: () => listEmployeeSessions(employee.id),
  });

  const items = query.data?.items ?? [];
  const subtitle = `${employee.full_name}${
    employee.login_id?.trim() ? ` · ${employeeUserIdLabel(employee.login_id)}` : ''
  }`;

  return (
    <Modal
      title="Employee Activity"
      subtitle={subtitle}
      size="lg"
      footer={
        <div className="flex justify-end">
          <Button variant="muted" onClick={onClose}>
            Close
          </Button>
        </div>
      }
      onClose={onClose}
    >
      {query.isLoading ? <LoadingBlock label="Loading activity…" /> : null}
      {query.isError ? (
        <ErrorBanner message={toEmployeeActivityError(query.error)} />
      ) : null}
      {!query.isLoading && !query.isError && items.length === 0 ? (
        <EmptyState title="No login activity yet" hint="Recent employee login and logout history will appear here." />
      ) : null}
      {!query.isLoading && !query.isError && items.length > 0 ? (
        <div className="overflow-x-auto rounded-xl border border-[#E0DDD5] bg-white">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-[#E0DDD5] bg-[#FDFAF4] text-[11px] uppercase tracking-[.06em] text-[#8A8A84]">
              <tr>
                <th className="px-4 py-3 font-semibold">Date</th>
                <th className="px-4 py-3 font-semibold">Login</th>
                <th className="px-4 py-3 font-semibold">Logout</th>
                <th className="px-4 py-3 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-b border-[#E0DDD5] last:border-b-0">
                  <td className="px-4 py-3">{formatActivityDate(item.login_at)}</td>
                  <td className="px-4 py-3">{formatActivityTime(item.login_at)}</td>
                  <td className="px-4 py-3">{logoutDisplay(item)}</td>
                  <td className="px-4 py-3">
                    <Badge tone={item.status === 'ACTIVE' ? 'green' : 'muted'}>
                      {sessionStatusLabel(item)}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </Modal>
  );
}
