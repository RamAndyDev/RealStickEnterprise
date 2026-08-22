import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';

import {
  ActionButton,
  ActionsTd,
  ActionsTh,
  Badge,
  Button,
  EmptyState,
  ErrorBanner,
  Field,
  LoadingBlock,
  Modal,
  SuccessBanner,
} from '../../components/ui';
import { listFranchises } from '../../lib/franchisesApi';
import { createPromotion, listPromotions, updatePromotion } from '../../lib/settingsApi';
import type { Promotion, PromotionWritePayload } from '../../types/settings';
import { validateDateRange, validateRequiredText } from '../../lib/validation';
import { apiErrorMessage, formatDate } from '../franchises/status';

type FormValues = {
  name: string;
  description: string;
  promo_code: string;
  valid_from: string;
  valid_to: string;
  is_active: boolean;
  franchise_ids: string[];
};

function emptyForm(): FormValues {
  return {
    name: '',
    description: '',
    promo_code: '',
    valid_from: '',
    valid_to: '',
    is_active: true,
    franchise_ids: [],
  };
}

function toPayload(values: FormValues): PromotionWritePayload {
  return {
    name: values.name.trim(),
    description: values.description.trim() || null,
    promo_code: values.promo_code.trim(),
    is_active: values.is_active,
    valid_from: values.valid_from ? `${values.valid_from}T00:00:00.000Z` : null,
    valid_to: values.valid_to ? `${values.valid_to}T23:59:59.999Z` : null,
    franchise_ids: values.franchise_ids,
  };
}

export function PromotionsPage() {
  const queryClient = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const [editTarget, setEditTarget] = useState<Promotion | null>(null);
  const [form, setForm] = useState<FormValues>(emptyForm());
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const listQuery = useQuery({
    queryKey: ['admin-promotions'],
    queryFn: listPromotions,
  });
  const franchisesQuery = useQuery({
    queryKey: ['admin-franchises-options'],
    queryFn: () => listFranchises({ include_archived: true }),
  });
  const franchiseNames = useMemo(() => {
    const map = new Map<string, string>();
    for (const item of franchisesQuery.data?.items ?? []) {
      map.set(item.id, item.name);
    }
    return map;
  }, [franchisesQuery.data]);

  const createMutation = useMutation({
    mutationFn: () => createPromotion(toPayload(form)),
    onSuccess: async () => {
      setShowAdd(false);
      setForm(emptyForm());
      setFeedback('Promotion created.');
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ['admin-promotions'] });
    },
    onError: (err) => setError(apiErrorMessage(err, 'Unable to create promotion.')),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<PromotionWritePayload> }) =>
      updatePromotion(id, payload),
    onSuccess: async () => {
      setEditTarget(null);
      setFeedback('Promotion updated.');
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ['admin-promotions'] });
    },
    onError: (err) => setError(apiErrorMessage(err, 'Unable to update promotion.')),
  });

  const items = listQuery.data?.items ?? [];

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="font-serif text-2xl font-bold text-[#1A1A18]">Promotions</h1>
          <p className="text-xs text-[#8A8A84]">
            Internal admin promotions. Franchise owners set their own offer percentages.
          </p>
        </div>
        <Button
          onClick={() => {
            setForm(emptyForm());
            setShowAdd(true);
            setError(null);
          }}
        >
          + Add Promotion
        </Button>
      </div>

      {feedback ? (
        <div className="mb-4">
          <SuccessBanner message={feedback} />
        </div>
      ) : null}
      {error && !showAdd && !editTarget ? (
        <div className="mb-4">
          <ErrorBanner message={error} />
        </div>
      ) : null}

      {listQuery.isLoading ? <LoadingBlock label="Loading promotions…" /> : null}
      {listQuery.isError ? (
        <ErrorBanner message={apiErrorMessage(listQuery.error, 'Unable to load promotions.')} />
      ) : null}
      {!listQuery.isLoading && !items.length ? (
        <EmptyState title="No promotions yet" hint="Create an internal promotion and assign franchises." />
      ) : null}

      {items.length ? (
        <div className="overflow-x-auto rounded-xl border border-[#E0DDD5] bg-white">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="border-b border-[#E0DDD5] bg-[#FDFAF4] text-[11px] uppercase tracking-[.06em] text-[#8A8A84]">
              <tr>
                <th className="px-4 py-3 font-semibold">Promotion</th>
                <th className="px-4 py-3 font-semibold">Promo code</th>
                <th className="px-4 py-3 font-semibold">Franchises</th>
                <th className="px-4 py-3 font-semibold">Validity</th>
                <th className="px-4 py-3 font-semibold">Status</th>
                <ActionsTh />
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-b border-[#E0DDD5] last:border-0">
                  <td className="px-4 py-3">
                    <div className="font-medium">{item.name}</div>
                    {item.description ? <div className="text-xs text-[#8A8A84]">{item.description}</div> : null}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">{item.promo_code}</td>
                  <td className="px-4 py-3 text-xs">
                    {item.franchise_ids.length
                      ? item.franchise_ids.map((id) => franchiseNames.get(id) || id).join(', ')
                      : 'None'}
                  </td>
                  <td className="px-4 py-3 text-xs">
                    {item.valid_from || item.valid_to
                      ? `${formatDate(item.valid_from)} – ${formatDate(item.valid_to)}`
                      : 'Always'}
                  </td>
                  <td className="px-4 py-3">
                    <Badge tone={item.is_active ? 'green' : 'muted'}>
                      {item.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </td>
                  <ActionsTd>
                    <ActionButton
                      variant="outline"
                      onClick={() => {
                        setForm({
                          name: item.name,
                          description: item.description ?? '',
                          promo_code: item.promo_code,
                          valid_from: item.valid_from ? item.valid_from.slice(0, 10) : '',
                          valid_to: item.valid_to ? item.valid_to.slice(0, 10) : '',
                          is_active: item.is_active,
                          franchise_ids: item.franchise_ids,
                        });
                        setEditTarget(item);
                        setError(null);
                      }}
                    >
                      Edit
                    </ActionButton>
                    <ActionButton
                      fit="status"
                      variant={item.is_active ? 'muted' : 'outline'}
                      onClick={() =>
                        updateMutation.mutate({
                          id: item.id,
                          payload: { is_active: !item.is_active },
                        })
                      }
                    >
                      {item.is_active ? 'Deactivate' : 'Activate'}
                    </ActionButton>
                  </ActionsTd>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {showAdd || editTarget ? (
        <Modal
          title={editTarget ? 'Edit promotion' : 'Add promotion'}
          onClose={() => {
            setShowAdd(false);
            setEditTarget(null);
          }}
        >
          {error ? (
            <div className="mb-3">
              <ErrorBanner message={error} />
            </div>
          ) : null}
          <Field
            label="Name"
            required
            value={form.name}
            error={formErrors.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <Field
            label="Description"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
          <Field
            label="Promo code"
            required
            value={form.promo_code}
            error={formErrors.promo_code}
            onChange={(e) => setForm({ ...form, promo_code: e.target.value })}
          />
          <Field
            label="Valid from"
            type="date"
            value={form.valid_from}
            error={formErrors.valid_from}
            onChange={(e) => setForm({ ...form, valid_from: e.target.value })}
          />
          <Field
            label="Valid to"
            type="date"
            value={form.valid_to}
            error={formErrors.valid_to}
            onChange={(e) => setForm({ ...form, valid_to: e.target.value })}
          />
          <fieldset className="mb-3">
            <legend className="mb-1 text-[11px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">
              Applicable franchises
            </legend>
            <div className="max-h-40 space-y-2 overflow-auto rounded-lg border border-[#E0DDD5] p-3">
              {(franchisesQuery.data?.items ?? []).map((franchise) => (
                <label key={franchise.id} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={form.franchise_ids.includes(franchise.id)}
                    onChange={(event) => {
                      setForm((current) => ({
                        ...current,
                        franchise_ids: event.target.checked
                          ? [...current.franchise_ids, franchise.id]
                          : current.franchise_ids.filter((id) => id !== franchise.id),
                      }));
                    }}
                  />
                  {franchise.name}
                </label>
              ))}
            </div>
          </fieldset>
          <label className="mb-4 flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
            />
            Active
          </label>
          <div className="flex justify-end gap-2">
            <Button
              variant="muted"
              onClick={() => {
                setShowAdd(false);
                setEditTarget(null);
              }}
            >
              Cancel
            </Button>
            <Button
              disabled={createMutation.isPending || updateMutation.isPending}
              onClick={() => {
                const errors: Record<string, string> = {};
                const nameError = validateRequiredText(form.name, 'Name is required.');
                const codeError = validateRequiredText(form.promo_code, 'Promo code is required.');
                if (nameError) errors.name = nameError;
                if (codeError) errors.promo_code = codeError;
                const range = validateDateRange(form.valid_from, form.valid_to);
                if (range.start) errors.valid_from = range.start;
                if (range.end) errors.valid_to = range.end;
                setFormErrors(errors);
                if (Object.keys(errors).length) return;
                if (editTarget) {
                  updateMutation.mutate({ id: editTarget.id, payload: toPayload(form) });
                } else {
                  createMutation.mutate();
                }
              }}
            >
              {createMutation.isPending || updateMutation.isPending ? 'Saving…' : 'Save'}
            </Button>
          </div>
        </Modal>
      ) : null}
    </div>
  );
}
