import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { Badge, ErrorBanner, LoadingBlock, SuccessBanner } from '../../components/ui';
import { fetchFranchiseAuditSetting, updateFranchiseAuditSetting } from '../../lib/settingsApi';
import {
  FRANCHISE_AUDIT_SETTING_COPY,
  franchiseAuditSettingStateLabel,
  resolveFranchiseAuditToggle,
} from './franchiseAuditSetting';

export function FranchiseAuditSettings() {
  const queryClient = useQueryClient();
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const settingQuery = useQuery({
    queryKey: ['admin-franchise-audit-setting'],
    queryFn: fetchFranchiseAuditSetting,
  });

  const persisted = settingQuery.data?.franchise_owner_audit_enabled ?? false;
  const displayed = enabled ?? persisted;

  const saveMutation = useMutation({
    mutationFn: (next: boolean) => updateFranchiseAuditSetting(next),
    onSuccess: async (data) => {
      const result = resolveFranchiseAuditToggle(displayed, data.franchise_owner_audit_enabled, true);
      setEnabled(result.value);
      setFeedback(result.feedback);
      setError(result.error);
      await queryClient.invalidateQueries({ queryKey: ['admin-franchise-audit-setting'] });
    },
  });

  function onToggle(next: boolean) {
    const previous = displayed;
    setEnabled(next);
    setFeedback(null);
    setError(null);
    saveMutation.mutate(next, {
      onError: () => {
        const result = resolveFranchiseAuditToggle(previous, next, false);
        setEnabled(result.value);
        setFeedback(result.feedback);
        setError(result.error);
      },
    });
  }

  return (
    <section className="mb-6 rounded-xl border border-[#E0DDD5] bg-white p-5">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-serif text-lg font-bold text-[#1A1A18]">
            {FRANCHISE_AUDIT_SETTING_COPY.heading}
          </h2>
          <p className="mt-1 text-xs text-[#8A8A84]">{FRANCHISE_AUDIT_SETTING_COPY.description}</p>
        </div>
        {settingQuery.isSuccess ? (
          <Badge tone={displayed ? 'green' : 'muted'}>{franchiseAuditSettingStateLabel(displayed)}</Badge>
        ) : null}
      </div>

      {feedback ? (
        <div className="mb-3">
          <SuccessBanner message={feedback} />
        </div>
      ) : null}
      {error ? (
        <div className="mb-3">
          <ErrorBanner message={error} />
        </div>
      ) : null}

      {settingQuery.isLoading ? <LoadingBlock label="Loading Franchise Audit access…" /> : null}
      {settingQuery.isError ? (
        <ErrorBanner message={FRANCHISE_AUDIT_SETTING_COPY.loadError} />
      ) : null}

      {settingQuery.isSuccess ? (
        <label className="flex items-center gap-2 text-sm text-[#1A1A18]">
          <input
            type="checkbox"
            checked={displayed}
            disabled={saveMutation.isPending}
            onChange={(event) => onToggle(event.target.checked)}
          />
          {FRANCHISE_AUDIT_SETTING_COPY.label}
        </label>
      ) : null}
    </section>
  );
}
