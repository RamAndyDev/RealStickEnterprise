import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { PublicPageMeta } from '../../components/layout/PublicLayout';
import { EmptyState, ErrorBanner, LoadingBlock } from '../../components/ui';
import { fetchPublicGallery } from '../../lib/publicApi';
import type { PublicGalleryItem } from '../../types/public';
import { apiErrorMessage } from '../franchises/status';
import { VideoEmbedFrame } from './videoEmbed';

export function PublicGalleryPage() {
  const query = useQuery({
    queryKey: ['public-gallery'],
    queryFn: fetchPublicGallery,
  });
  const [lightbox, setLightbox] = useState<PublicGalleryItem | null>(null);

  const grouped = useMemo(() => {
    const items = query.data?.items ?? [];
    return {
      images: items.filter((item) => item.media_type === 'IMAGE' && item.media_url),
      videos: items.filter((item) => item.media_type === 'VIDEO' && item.media_url),
      quotes: items.filter((item) => item.media_type === 'TESTIMONIAL'),
    };
  }, [query.data]);

  const empty =
    !query.isLoading &&
    !query.isError &&
    !grouped.images.length &&
    !grouped.videos.length &&
    !grouped.quotes.length;

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:py-14">
      <PublicPageMeta title="Gallery | RealStick" />
      <p className="text-xs font-semibold uppercase tracking-[.18em] text-[#1A7A4A]">Moments</p>
      <h1 className="mt-2 font-serif text-4xl font-bold text-[#0D4F2E]">Gallery</h1>
      <p className="mt-3 max-w-2xl text-[#4A4A46]">
        Product images, videos, and notes from people who have tasted RealStick.
      </p>

      {query.isLoading ? <div className="mt-8"><LoadingBlock label="Loading gallery…" /></div> : null}
      {query.isError ? (
        <div className="mt-8">
          <ErrorBanner message={apiErrorMessage(query.error, 'Unable to load the gallery.')} />
        </div>
      ) : null}
      {empty ? (
        <div className="mt-10">
          <EmptyState title="Gallery coming soon" hint="Approved images, videos, and testimonials will appear here." />
        </div>
      ) : null}

      {grouped.images.length ? (
        <section className="mt-10">
          <h2 className="font-serif text-2xl font-bold text-[#0D4F2E]">Images</h2>
          <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {grouped.images.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setLightbox(item)}
                className="group overflow-hidden rounded-2xl bg-[#F3F1EB] text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1A7A4A]"
              >
                <img
                  src={item.media_url ?? ''}
                  alt={item.title || item.caption || 'RealStick gallery image'}
                  className="aspect-[4/3] w-full object-cover transition duration-500 group-hover:scale-[1.03]"
                />
                {item.title ? (
                  <div className="px-4 py-3 text-sm font-medium text-[#1A1A18]">{item.title}</div>
                ) : null}
              </button>
            ))}
          </div>
        </section>
      ) : null}

      {grouped.videos.length ? (
        <section className="mt-12">
          <h2 className="font-serif text-2xl font-bold text-[#0D4F2E]">Videos</h2>
          <div className="mt-5 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {grouped.videos.map((item) => (
              <article key={item.id} className="overflow-hidden rounded-2xl bg-black shadow">
                <div className="aspect-video">
                  <VideoEmbedFrame url={item.media_url ?? ''} title={item.title || 'RealStick video'} />
                </div>
                {item.title ? (
                  <div className="bg-white px-4 py-3 text-sm font-medium">{item.title}</div>
                ) : null}
              </article>
            ))}
          </div>
        </section>
      ) : null}

      {grouped.quotes.length ? (
        <section className="mt-12">
          <h2 className="font-serif text-2xl font-bold text-[#0D4F2E]">Testimonials</h2>
          <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {grouped.quotes.map((item) => (
              <blockquote
                key={item.id}
                className="rounded-2xl border border-[#E0DDD5] bg-white px-6 py-8 shadow-[0_8px_30px_rgba(13,79,46,0.04)]"
              >
                <p className="font-serif text-xl leading-relaxed text-[#1A1A18]">
                  “{item.caption}”
                </p>
                <footer className="mt-4 text-sm font-semibold text-[#1A7A4A]">
                  {item.author_name}
                  {item.title ? <span className="block font-normal text-[#8A8A84]">{item.title}</span> : null}
                </footer>
              </blockquote>
            ))}
          </div>
        </section>
      ) : null}

      {lightbox?.media_url ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
          role="dialog"
          aria-modal="true"
          aria-label={lightbox.title || 'Image preview'}
          onClick={() => setLightbox(null)}
        >
          <button
            type="button"
            className="absolute right-4 top-4 min-h-11 min-w-11 text-2xl text-white"
            aria-label="Close image"
            onClick={() => setLightbox(null)}
          >
            ×
          </button>
          <img
            src={lightbox.media_url}
            alt={lightbox.title || lightbox.caption || 'RealStick gallery image'}
            className="max-h-[85vh] max-w-full rounded-xl object-contain"
            onClick={(event) => event.stopPropagation()}
          />
        </div>
      ) : null}
    </div>
  );
}
