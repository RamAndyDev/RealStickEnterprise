-- M10: extend gallery_items for testimonials and brand-level admin content.
-- Do not create a second gallery table. Public website reads go through FastAPI.

-- ---------------------------------------------------------------------------
-- Enum: TESTIMONIAL content type
-- ---------------------------------------------------------------------------

alter type public.gallery_media_type add value if not exists 'TESTIMONIAL';

-- ---------------------------------------------------------------------------
-- Columns: nullable media for testimonials / image drafts; optional author
-- ---------------------------------------------------------------------------

alter table public.gallery_items
  alter column storage_path drop not null,
  alter column media_url drop not null;

alter table public.gallery_items
  add column if not exists author_name text;

comment on column public.gallery_items.author_name is
  'Display name for TESTIMONIAL items. Unused for IMAGE/VIDEO.';

comment on column public.gallery_items.franchise_id is
  'NULL for brand-level System Admin gallery content. Outlet-scoped items may set a franchise.';

-- Content-type rules (compare as text so this migration can run in one transaction):
-- IMAGE: both media fields null (draft) OR both present (complete)
-- VIDEO: external HTTPS media_url required
-- TESTIMONIAL: quote body (caption) required; no media required
alter table public.gallery_items
  drop constraint if exists gallery_items_content_check;

alter table public.gallery_items
  add constraint gallery_items_content_check check (
    (
      media_type::text = 'IMAGE'
      and (
        (storage_path is null and media_url is null)
        or (
          storage_path is not null
          and length(trim(storage_path)) > 0
          and media_url is not null
          and length(trim(media_url)) > 0
        )
      )
    )
    or (
      media_type::text = 'VIDEO'
      and media_url is not null
      and length(trim(media_url)) > 0
    )
    or (
      media_type::text = 'TESTIMONIAL'
      and caption is not null
      and length(trim(caption)) > 0
    )
  );

-- Public website must not read gallery_items via PostgREST/anon.
-- FastAPI service-role is the only public read path (whitelist schemas).
drop policy if exists gallery_items_select_public on public.gallery_items;

-- ---------------------------------------------------------------------------
-- Storage bucket: gallery (public read, no anonymous write)
-- Guarded so SQL-only environments without Storage still apply table changes.
-- ---------------------------------------------------------------------------

do $$
begin
  if exists (
    select 1
    from information_schema.tables
    where table_schema = 'storage'
      and table_name = 'buckets'
  ) then
    insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
    values (
      'gallery',
      'gallery',
      true,
      5242880,
      array['image/jpeg', 'image/png', 'image/webp']
    )
    on conflict (id) do nothing;
  end if;
end $$;

do $$
begin
  if exists (
    select 1
    from information_schema.tables
    where table_schema = 'storage'
      and table_name = 'objects'
  ) then
    execute 'drop policy if exists gallery_objects_select_public on storage.objects';
    execute $policy$
      create policy gallery_objects_select_public
        on storage.objects
        for select
        to anon, authenticated
        using (bucket_id = 'gallery')
    $policy$;
  end if;
end $$;

-- No INSERT/UPDATE/DELETE policies for anon or authenticated on storage.objects
-- for the gallery bucket. Uploads go through FastAPI with the service-role key.
