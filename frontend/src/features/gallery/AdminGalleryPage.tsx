import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
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
  createAdminGalleryItem,
  listAdminGallery,
  updateAdminGalleryItem,
  uploadAdminGalleryMedia,
} from '../../lib/publicApi';
import type { AdminGalleryItem } from '../../types/public';
import { apiErrorMessage } from '../franchises/status';
import { VideoEmbedFrame } from '../public/videoEmbed';

type FormState = {
  media_type: AdminGalleryItem['media_type'];
  title: string;
  caption: string;
  author_name: string;
  media_url: string;
  display_order: string;
};

const emptyForm = (): FormState => ({
  media_type: 'IMAGE',
  title: '',
  caption: '',
  author_name: '',
  media_url: '',
  display_order: '0',
});

export function AdminGalleryPage() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<FormState>(emptyForm());
  const [showCreate, setShowCreate] = useState(false);
  const [editTarget, setEditTarget] = useState<AdminGalleryItem | null>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'ALL' | 'IMAGE' | 'VIDEO' | 'TESTIMONIAL' | 'ARCHIVED'>('ALL');

  const listQuery = useQuery({
    queryKey: ['admin-gallery'],
    queryFn: listAdminGallery,
  });

  const items = useMemo(() => {
    const rows = listQuery.data?.items ?? [];
    if (filter === 'ARCHIVED') return rows.filter((row) => row.is_archived);
    if (filter === 'ALL') return rows.filter((row) => !row.is_archived);
    return rows.filter((row) => !row.is_archived && row.media_type === filter);
  }, [listQuery.data, filter]);

  const createMutation = useMutation({
    mutationFn: async () => {
      const created = await createAdminGalleryItem({
        media_type: form.media_type,
        title: form.title.trim() || undefined,
        caption: form.caption.trim() || undefined,
        author_name: form.author_name.trim() || undefined,
        media_url: form.media_type === 'VIDEO' ? form.media_url.trim() : undefined,
        display_order: Number.parseInt(form.display_order, 10) || 0,
      });
      if (form.media_type === 'IMAGE' && imageFile) {
        return uploadAdminGalleryMedia(created.id, imageFile);
      }
      return created;
    },
    onSuccess: async () => {
      setShowCreate(false);
      setForm(emptyForm());
      setImageFile(null);
      setFeedback('Gallery item created.');
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ['admin-gallery'] });
    },
    onError: (err) => setError(apiErrorMessage(err, 'Unable to create gallery item.')),
  });

  const updateMutation = useMutation({
    mutationFn: async () => {
      if (!editTarget) throw new Error('Nothing to update');
      const updated = await updateAdminGalleryItem(editTarget.id, {
        title: form.title.trim() || null,
        caption: form.caption.trim() || null,
        author_name: form.author_name.trim() || null,
        media_url: editTarget.media_type === 'VIDEO' ? form.media_url.trim() : undefined,
        display_order: Number.parseInt(form.display_order, 10) || 0,
      });
      if (editTarget.media_type === 'IMAGE' && imageFile) {
        return uploadAdminGalleryMedia(editTarget.id, imageFile);
      }
      return updated;
    },
    onSuccess: async () => {
      setEditTarget(null);
      setImageFile(null);
      setFeedback('Gallery item updated.');
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ['admin-gallery'] });
    },
    onError: (err) => setError(apiErrorMessage(err, 'Unable to update gallery item.')),
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: { is_approved?: boolean; is_archived?: boolean } }) =>
      updateAdminGalleryItem(id, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['admin-gallery'] });
    },
    onError: (err) => setError(apiErrorMessage(err, 'Unable to update gallery item.')),
  });

  function openEdit(item: AdminGalleryItem) {
    setEditTarget(item);
    setForm({
      media_type: item.media_type,
      title: item.title ?? '',
      caption: item.caption ?? '',
      author_name: item.author_name ?? '',
      media_url: item.media_url ?? '',
      display_order: String(item.display_order),
    });
    setImageFile(null);
  }

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-serif text-3xl font-bold">Gallery Management</h1>
          <p className="mt-1 text-sm text-[#8A8A84]">Brand-level images, videos, and testimonials for the public website.</p>
        </div>
        <Button onClick={() => { setForm(emptyForm()); setImageFile(null); setShowCreate(true); }}>
          Add item
        </Button>
      </div>

      {feedback ? <div className="mb-4"><SuccessBanner message={feedback} /></div> : null}
      {error ? <div className="mb-4"><ErrorBanner message={error} /></div> : null}

      <div className="mb-4 flex flex-wrap gap-2">
        {(['ALL', 'IMAGE', 'VIDEO', 'TESTIMONIAL', 'ARCHIVED'] as const).map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => setFilter(key)}
            className={`min-h-11 rounded-full px-3 text-sm font-semibold ${
              filter === key ? 'bg-[#0D4F2E] text-white' : 'border border-[#E0DDD5] bg-white text-[#4A4A46]'
            }`}
          >
            {key === 'ALL' ? 'Active' : key.charAt(0) + key.slice(1).toLowerCase()}
          </button>
        ))}
      </div>

      {listQuery.isLoading ? <LoadingBlock label="Loading gallery…" /> : null}
      {listQuery.isError ? (
        <ErrorBanner message={apiErrorMessage(listQuery.error, 'Unable to load gallery items.')} />
      ) : null}
      {!listQuery.isLoading && !items.length ? (
        <EmptyState title="No gallery items" hint="Create an image, video URL, or testimonial." />
      ) : null}

      <div className="space-y-3">
        {items.map((item) => (
          <article key={item.id} className="rounded-xl border border-[#E0DDD5] bg-white p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <Badge>{item.media_type}</Badge>
                  {item.is_approved ? <Badge tone="green">Approved</Badge> : <Badge tone="muted">Unapproved</Badge>}
                  {item.is_archived ? <Badge tone="amber">Archived</Badge> : null}
                </div>
                <h2 className="font-semibold">{item.title || '(untitled)'}</h2>
                {item.caption ? <p className="mt-1 text-sm text-[#4A4A46]">{item.caption}</p> : null}
                {item.author_name ? <p className="mt-1 text-xs text-[#8A8A84]">{item.author_name}</p> : null}
                <p className="mt-1 text-xs text-[#8A8A84]">Order {item.display_order}</p>
                {item.media_type === 'IMAGE' && item.media_url ? (
                  <img src={item.media_url} alt={item.title || 'Gallery image'} className="mt-3 h-28 rounded-lg object-cover" />
                ) : null}
                {item.media_type === 'VIDEO' && item.media_url ? (
                  <div className="mt-3 aspect-video max-w-sm overflow-hidden rounded-lg bg-black">
                    <VideoEmbedFrame url={item.media_url} title={item.title || 'Video preview'} />
                  </div>
                ) : null}
              </div>
              <div className="flex flex-wrap gap-2">
                <Button size="sm" variant="outline" onClick={() => openEdit(item)}>
                  Edit
                </Button>
                <Button
                  size="sm"
                  variant="muted"
                  onClick={() =>
                    statusMutation.mutate({ id: item.id, payload: { is_approved: !item.is_approved } })
                  }
                >
                  {item.is_approved ? 'Unapprove' : 'Approve'}
                </Button>
                {!item.is_archived ? (
                  <Button
                    size="sm"
                    variant="danger"
                    onClick={() => statusMutation.mutate({ id: item.id, payload: { is_archived: true } })}
                  >
                    Archive
                  </Button>
                ) : (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => statusMutation.mutate({ id: item.id, payload: { is_archived: false } })}
                  >
                    Restore
                  </Button>
                )}
              </div>
            </div>
          </article>
        ))}
      </div>

      {showCreate ? (
        <Modal title="Add gallery item" onClose={() => setShowCreate(false)} wide>
          <GalleryForm
            form={form}
            setForm={setForm}
            imageFile={imageFile}
            setImageFile={setImageFile}
            submitting={createMutation.isPending}
            onSubmit={() => createMutation.mutate()}
            allowType
          />
        </Modal>
      ) : null}

      {editTarget ? (
        <Modal title="Edit gallery item" onClose={() => setEditTarget(null)} wide>
          <GalleryForm
            form={form}
            setForm={setForm}
            imageFile={imageFile}
            setImageFile={setImageFile}
            submitting={updateMutation.isPending}
            onSubmit={() => updateMutation.mutate()}
            allowType={false}
            mediaType={editTarget.media_type}
            existingUrl={editTarget.media_url}
          />
        </Modal>
      ) : null}
    </div>
  );
}

function GalleryForm({
  form,
  setForm,
  imageFile,
  setImageFile,
  submitting,
  onSubmit,
  allowType,
  mediaType,
  existingUrl,
}: {
  form: FormState;
  setForm: (value: FormState) => void;
  imageFile: File | null;
  setImageFile: (file: File | null) => void;
  submitting: boolean;
  onSubmit: () => void;
  allowType: boolean;
  mediaType?: AdminGalleryItem['media_type'];
  existingUrl?: string | null;
}) {
  const type = mediaType ?? form.media_type;
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      {allowType ? (
        <SelectField
          label="Type"
          value={form.media_type}
          onChange={(e) => setForm({ ...form, media_type: e.target.value as FormState['media_type'] })}
        >
          <option value="IMAGE">Image</option>
          <option value="VIDEO">Video URL</option>
          <option value="TESTIMONIAL">Testimonial</option>
        </SelectField>
      ) : null}
      <Field label="Title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
      {type === 'TESTIMONIAL' ? (
        <Field
          label="Author"
          required
          value={form.author_name}
          onChange={(e) => setForm({ ...form, author_name: e.target.value })}
        />
      ) : null}
      <label className="mb-3 block">
        <span className="mb-1 block text-[11px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">
          {type === 'TESTIMONIAL' ? 'Quote' : 'Caption'}
        </span>
        <textarea
          required={type === 'TESTIMONIAL'}
          rows={4}
          value={form.caption}
          onChange={(e) => setForm({ ...form, caption: e.target.value })}
          className="w-full rounded-lg border border-[#E0DDD5] px-3 py-2.5 text-sm outline-none focus:border-[#1A7A4A]"
        />
      </label>
      {type === 'VIDEO' ? (
        <Field
          label="Video URL"
          required
          value={form.media_url}
          onChange={(e) => setForm({ ...form, media_url: e.target.value })}
          placeholder="https://www.youtube.com/watch?v=..."
        />
      ) : null}
      {type === 'IMAGE' ? (
        <label className="mb-3 block">
          <span className="mb-1 block text-[11px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">
            Image (JPEG, PNG, WEBP)
          </span>
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={(e) => setImageFile(e.target.files?.[0] ?? null)}
          />
          {existingUrl ? (
            <img src={existingUrl} alt="Current" className="mt-2 h-24 rounded-lg object-cover" />
          ) : null}
          {imageFile ? <p className="mt-1 text-xs text-[#8A8A84]">{imageFile.name}</p> : null}
        </label>
      ) : null}
      <Field
        label="Display order"
        type="number"
        min={0}
        value={form.display_order}
        onChange={(e) => setForm({ ...form, display_order: e.target.value })}
      />
      <div className="mt-4 flex justify-end">
        <Button type="submit" disabled={submitting}>
          {submitting ? 'Saving…' : 'Save'}
        </Button>
      </div>
    </form>
  );
}
