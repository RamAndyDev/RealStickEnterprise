import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

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
  SelectField,
  SuccessBanner,
} from '../../components/ui';
import {
  createOwnerOffer,
  listOwnerOffers,
  listOwnerPromotions,
  updateOwnerOffer,
} from '../../lib/settingsApi';
import type { Offer, OfferWritePayload } from '../../types/settings';
import { validateDateRange, validatePercentage, validateRequiredText } from '../../lib/validation';
import { apiErrorMessage, formatDate } from '../franchises/status';

type FormValues = {
  name: string;
  description: string;
  discount_value: string;
  valid_from: string;
  valid_to: string;
  is_active: boolean;
  promotion_id: string;
};

function emptyForm(): FormValues {
  return {
    name: '',
    description: '',
    discount_value: '10',
    valid_from: '',
    valid_to: '',
    is_active: true,
    promotion_id: '',
  };
}

function toPayload(values: FormValues): OfferWritePayload {
  return {
    name: values.name.trim(),
    description: values.description.trim() || null,
    discount_type: 'PERCENTAGE',
    discount_value: Number.parseFloat(values.discount_value),
    is_active: values.is_active,
    valid_from: values.valid_from ? `${values.valid_from}T00:00:00.000Z` : null,
    valid_to: values.valid_to ? `${values.valid_to}T23:59:59.999Z` : null,
    promotion_id: values.promotion_id || null,
    clear_promotion_id: !values.promotion_id,
  };
}

export function OffersPage() {
  const queryClient = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const [editTarget, setEditTarget] = useState<Offer | null>(null);
  const [form, setForm] = useState<FormValues>(emptyForm());
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const listQuery = useQuery({
    queryKey: ['owner-offers'],
    queryFn: listOwnerOffers,
  });
  const promotionsQuery = useQuery({
    queryKey: ['owner-promotions'],
    queryFn: listOwnerPromotions,
  });

  const createMutation = useMutation({
    mutationFn: () => createOwnerOffer(toPayload(form)),
    onSuccess: async () => {
      setShowAdd(false);
      setForm(emptyForm());
      setFeedback('Offer created.');
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ['owner-offers'] });
    },
    onError: (err) => setError(apiErrorMessage(err, 'Unable to create offer.')),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<OfferWritePayload> }) =>
      updateOwnerOffer(id, payload),
    onSuccess: async () => {
      setEditTarget(null);
      setFeedback('Offer updated.');
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ['owner-offers'] });
    },
    onError: (err) => setError(apiErrorMessage(err, 'Unable to update offer.')),
  });

  const items = listQuery.data?.items ?? [];
  const promotions = promotionsQuery.data?.items ?? [];

  function openEdit(offer: Offer) {
    setForm({
      name: offer.name,
      description: offer.description ?? '',
      discount_value: String(offer.discount_value),
      valid_from: offer.valid_from ? offer.valid_from.slice(0, 10) : '',
      valid_to: offer.valid_to ? offer.valid_to.slice(0, 10) : '',
      is_active: offer.is_active,
      promotion_id: offer.promotion_id ?? '',
    });
    setEditTarget(offer);
    setError(null);
  }

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="font-serif text-2xl font-bold text-[#1A1A18]">Offers &amp; Discounts</h1>
          <p className="text-xs text-[#8A8A84]">
            Create a local offer, or optionally link it to an admin promotion. Customers never see promo codes.
          </p>
        </div>
        <Button
          onClick={() => {
            setForm(emptyForm());
            setShowAdd(true);
            setError(null);
          }}
        >
          + Add Offer
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

      {listQuery.isLoading ? <LoadingBlock label="Loading offers…" /> : null}
      {listQuery.isError ? (
        <ErrorBanner message={apiErrorMessage(listQuery.error, 'Unable to load offers.')} />
      ) : null}
      {!listQuery.isLoading && !items.length ? (
        <EmptyState title="No offers yet" hint="Create a local offer or link one to an admin promotion." />
      ) : null}

      {items.length ? (
        <div className="overflow-x-auto rounded-xl border border-[#E0DDD5] bg-white">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="border-b border-[#E0DDD5] bg-[#FDFAF4] text-[11px] uppercase tracking-[.06em] text-[#8A8A84]">
              <tr>
                <th className="px-4 py-3 font-semibold">Offer</th>
                <th className="px-4 py-3 font-semibold">Discount</th>
                <th className="px-4 py-3 font-semibold">Promotion</th>
                <th className="px-4 py-3 font-semibold">Validity</th>
                <th className="px-4 py-3 font-semibold">Status</th>
                <ActionsTh />
              </tr>
            </thead>
            <tbody>
              {items.map((offer) => (
                <tr key={offer.id} className="border-b border-[#E0DDD5] last:border-0">
                  <td className="px-4 py-3">
                    <div className="font-medium">{offer.name}</div>
                    {offer.description ? <div className="text-xs text-[#8A8A84]">{offer.description}</div> : null}
                  </td>
                  <td className="px-4 py-3">{Number(offer.discount_value).toFixed(0)}%</td>
                  <td className="px-4 py-3 text-xs">
                    {offer.promotion_promo_code || offer.promotion_name || 'Local offer'}
                  </td>
                  <td className="px-4 py-3 text-xs">
                    {offer.valid_from || offer.valid_to
                      ? `${formatDate(offer.valid_from)} – ${formatDate(offer.valid_to)}`
                      : 'Always'}
                  </td>
                  <td className="px-4 py-3">
                    <Badge tone={offer.is_active ? 'green' : 'muted'}>
                      {offer.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </td>
                  <ActionsTd>
                    <ActionButton variant="outline" onClick={() => openEdit(offer)}>
                      Edit
                    </ActionButton>
                    <ActionButton
                      fit="status"
                      variant={offer.is_active ? 'muted' : 'outline'}
                      onClick={() =>
                        updateMutation.mutate({
                          id: offer.id,
                          payload: { is_active: !offer.is_active },
                        })
                      }
                    >
                      {offer.is_active ? 'Deactivate' : 'Activate'}
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
          title={editTarget ? 'Edit offer' : 'Add offer'}
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
            label="Offer name"
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
            label="Discount %"
            type="number"
            min={0.01}
            max={100}
            step="0.01"
            required
            value={form.discount_value}
            error={formErrors.discount_value}
            onChange={(e) => setForm({ ...form, discount_value: e.target.value })}
          />
          <SelectField
            label="Admin promotion (optional)"
            value={form.promotion_id}
            onChange={(e) => setForm({ ...form, promotion_id: e.target.value })}
          >
            <option value="">Local offer — no admin promotion</option>
            {promotions.map((promotion) => (
              <option key={promotion.id} value={promotion.id}>
                {promotion.promo_code} — {promotion.name}
              </option>
            ))}
          </SelectField>
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
                const nameError = validateRequiredText(form.name, 'Offer name is required.');
                const percentError = validatePercentage(form.discount_value, {
                  allowZero: false,
                  min: 0.01,
                  max: 100,
                });
                if (nameError) errors.name = nameError;
                if (percentError) errors.discount_value = percentError;
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
