import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import {
  Badge,
  Button,
  EmptyState,
  ErrorBanner,
  Field,
  LoadingBlock,
  Modal,
  SuccessBanner,
} from '../../components/ui';
import { createOffer, listOffers, updateOffer } from '../../lib/settingsApi';
import type { Offer, OfferWritePayload } from '../../types/settings';
import { apiErrorMessage, formatDate } from '../franchises/status';

type OfferFormValues = {
  name: string;
  description: string;
  discount_value: string;
  valid_from: string;
  valid_to: string;
  is_active: boolean;
};

function emptyForm(): OfferFormValues {
  return {
    name: '',
    description: '',
    discount_value: '10',
    valid_from: '',
    valid_to: '',
    is_active: true,
  };
}

function offerToForm(offer: Offer): OfferFormValues {
  return {
    name: offer.name,
    description: offer.description ?? '',
    discount_value: String(offer.discount_value),
    valid_from: offer.valid_from ? offer.valid_from.slice(0, 10) : '',
    valid_to: offer.valid_to ? offer.valid_to.slice(0, 10) : '',
    is_active: offer.is_active,
  };
}

function toPayload(values: OfferFormValues): OfferWritePayload {
  const discount = Number.parseFloat(values.discount_value);
  return {
    name: values.name.trim(),
    description: values.description.trim() || null,
    discount_type: 'PERCENTAGE',
    discount_value: discount,
    is_active: values.is_active,
    valid_from: values.valid_from ? `${values.valid_from}T00:00:00.000Z` : null,
    valid_to: values.valid_to ? `${values.valid_to}T23:59:59.999Z` : null,
  };
}

export function OffersPage() {
  const queryClient = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const [editTarget, setEditTarget] = useState<Offer | null>(null);
  const [form, setForm] = useState<OfferFormValues>(emptyForm());
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const listQuery = useQuery({
    queryKey: ['admin-offers'],
    queryFn: listOffers,
  });

  const createMutation = useMutation({
    mutationFn: () => createOffer(toPayload(form)),
    onSuccess: async () => {
      setShowAdd(false);
      setForm(emptyForm());
      setFeedback('Offer created.');
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ['admin-offers'] });
    },
    onError: (err) => setError(apiErrorMessage(err, 'Unable to create offer.')),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<OfferWritePayload> }) =>
      updateOffer(id, payload),
    onSuccess: async () => {
      setEditTarget(null);
      setFeedback('Offer updated.');
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ['admin-offers'] });
    },
    onError: (err) => setError(apiErrorMessage(err, 'Unable to update offer.')),
  });

  const items = listQuery.data?.items ?? [];

  function openAdd() {
    setForm(emptyForm());
    setShowAdd(true);
    setError(null);
  }

  function openEdit(offer: Offer) {
    setForm(offerToForm(offer));
    setEditTarget(offer);
    setError(null);
  }

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="font-serif text-2xl font-bold text-[#1A1A18]">Offers</h1>
          <p className="text-xs text-[#8A8A84]">Basic percentage offers displayed at POS billing.</p>
        </div>
        <Button onClick={openAdd}>+ Add Offer</Button>
      </div>

      {feedback ? <div className="mb-4"><SuccessBanner message={feedback} /></div> : null}
      {error && !showAdd && !editTarget ? (
        <div className="mb-4"><ErrorBanner message={error} /></div>
      ) : null}

      {listQuery.isLoading ? <LoadingBlock label="Loading offers…" /> : null}
      {listQuery.isError ? (
        <ErrorBanner message={apiErrorMessage(listQuery.error, 'Unable to load offers.')} />
      ) : null}

      {!listQuery.isLoading && !items.length ? (
        <EmptyState title="No offers yet" hint="Create a percentage offer for POS billing." />
      ) : null}

      {items.length ? (
        <div className="overflow-x-auto rounded-xl border border-[#E0DDD5] bg-white">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="border-b border-[#E0DDD5] bg-[#FDFAF4] text-[11px] uppercase tracking-[.06em] text-[#8A8A84]">
              <tr>
                <th className="px-4 py-3 font-semibold">Offer Name</th>
                <th className="px-4 py-3 font-semibold">Discount</th>
                <th className="px-4 py-3 font-semibold">Validity</th>
                <th className="px-4 py-3 font-semibold">Status</th>
                <th className="px-4 py-3 font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((offer) => (
                <tr key={offer.id} className="border-b border-[#E0DDD5] last:border-0">
                  <td className="px-4 py-3">
                    <div className="font-medium text-[#1A1A18]">{offer.name}</div>
                    {offer.description ? (
                      <div className="text-xs text-[#8A8A84]">{offer.description}</div>
                    ) : null}
                  </td>
                  <td className="px-4 py-3">{Number(offer.discount_value).toFixed(0)}%</td>
                  <td className="px-4 py-3 text-xs text-[#4A4A46]">
                    {offer.valid_from || offer.valid_to
                      ? `${formatDate(offer.valid_from)} – ${formatDate(offer.valid_to)}`
                      : 'Always'}
                  </td>
                  <td className="px-4 py-3">
                    <Badge tone={offer.is_active ? 'green' : 'muted'}>
                      {offer.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      <Button size="sm" variant="outline" onClick={() => openEdit(offer)}>
                        Edit
                      </Button>
                      <Button
                        size="sm"
                        variant={offer.is_active ? 'muted' : 'outline'}
                        onClick={() =>
                          updateMutation.mutate({
                            id: offer.id,
                            payload: { is_active: !offer.is_active },
                          })
                        }
                      >
                        {offer.is_active ? 'Deactivate' : 'Activate'}
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {showAdd ? (
        <Modal title="Add Offer" onClose={() => setShowAdd(false)}>
          <OfferForm
            values={form}
            onChange={setForm}
            error={error}
            submitting={createMutation.isPending}
            onSubmit={() => createMutation.mutate()}
            onCancel={() => setShowAdd(false)}
          />
        </Modal>
      ) : null}

      {editTarget ? (
        <Modal title="Edit Offer" onClose={() => setEditTarget(null)}>
          <OfferForm
            values={form}
            onChange={setForm}
            error={error}
            submitting={updateMutation.isPending}
            onSubmit={() =>
              updateMutation.mutate({ id: editTarget.id, payload: toPayload(form) })
            }
            onCancel={() => setEditTarget(null)}
          />
        </Modal>
      ) : null}
    </div>
  );
}

function OfferForm({
  values,
  onChange,
  error,
  submitting,
  onSubmit,
  onCancel,
}: {
  values: OfferFormValues;
  onChange: (values: OfferFormValues) => void;
  error: string | null;
  submitting: boolean;
  onSubmit: () => void;
  onCancel: () => void;
}) {
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
    >
      {error ? <div className="mb-3"><ErrorBanner message={error} /></div> : null}
      <Field
        label="Offer Name"
        value={values.name}
        onChange={(e) => onChange({ ...values, name: e.target.value })}
        required
      />
      <Field
        label="Description"
        value={values.description}
        onChange={(e) => onChange({ ...values, description: e.target.value })}
      />
      <Field
        label="Discount %"
        type="number"
        min={0.01}
        max={100}
        step="0.01"
        value={values.discount_value}
        onChange={(e) => onChange({ ...values, discount_value: e.target.value })}
        required
      />
      <Field
        label="Valid From"
        type="date"
        value={values.valid_from}
        onChange={(e) => onChange({ ...values, valid_from: e.target.value })}
      />
      <Field
        label="Valid To"
        type="date"
        value={values.valid_to}
        onChange={(e) => onChange({ ...values, valid_to: e.target.value })}
      />
      <label className="mb-4 flex items-center gap-2 text-sm text-[#4A4A46]">
        <input
          type="checkbox"
          checked={values.is_active}
          onChange={(e) => onChange({ ...values, is_active: e.target.checked })}
        />
        Active
      </label>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="muted" onClick={onCancel} disabled={submitting}>
          Cancel
        </Button>
        <Button type="submit" disabled={submitting}>
          {submitting ? 'Saving…' : 'Save'}
        </Button>
      </div>
    </form>
  );
}
