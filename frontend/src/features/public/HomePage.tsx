import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { Button, ErrorBanner, LoadingBlock } from '../../components/ui';
import { PublicPageMeta } from '../../components/layout/PublicLayout';
import { fetchPublicProducts } from '../../lib/publicApi';
import { ProductImage } from '../products/ProductImage';
import { categoryColor } from '../products/categoryColors';
import { BrandHero } from './HeroArt';

export function PublicHomePage() {
  const productsQuery = useQuery({
    queryKey: ['public-products'],
    queryFn: fetchPublicProducts,
  });
  const featured = (productsQuery.data?.items ?? []).slice(0, 4);

  return (
    <>
      <PublicPageMeta title="RealStick™ — Natural Popsicles & Kulfi" />

      <section className="overflow-hidden">
        <div className="mx-auto grid max-w-6xl items-center gap-10 px-4 py-12 sm:px-6 lg:grid-cols-2 lg:py-20">
          <div className="rs-fade-up">
            <p className="text-xs font-semibold uppercase tracking-[.22em] text-[#1A7A4A]">
              Natural Popsicles &amp; Kulfi
            </p>
            <h1 className="mt-3 font-serif text-4xl font-bold leading-tight text-[#0D4F2E] sm:text-5xl lg:text-6xl">
              Real Fruits.
              <br />
              Real Goodness.
            </h1>
            <p className="mt-5 max-w-md text-base leading-relaxed text-[#4A4A46] sm:text-lg">
              Fresh, fruit-forward popsicles and kulfi — made without artificial colours, flavours, or
              preservatives.
            </p>
            <div className="mt-4 flex flex-wrap gap-2 text-[13px] font-semibold text-[#0D4F2E]">
              <span className="rounded-full bg-[#E6F4EC] px-3 py-1">Zero Artificial</span>
              <span className="rounded-full bg-[#FFF4ED] px-3 py-1 text-[#E8621A]">Zero Preservatives</span>
            </div>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/menu">
                <Button className="min-h-11 px-6">Explore Menu</Button>
              </Link>
              <Link to="/contact">
                <Button variant="outline" className="min-h-11 px-6">
                  Contact Us
                </Button>
              </Link>
            </div>
          </div>
          <div className="rs-fade-up rs-fade-up-delay">
            <BrandHero />
          </div>
        </div>
      </section>

      <section className="border-y border-[#E0DDD5] bg-white">
        <div className="mx-auto grid max-w-6xl gap-8 px-4 py-12 sm:px-6 md:grid-cols-3">
          {[
            { title: 'Real fruit', body: 'Each stick starts with fruit you can taste.' },
            { title: 'Clean recipes', body: 'Zero artificial. Zero preservatives.' },
            { title: 'Made to share', body: 'Popsicles and kulfi for everyday moments.' },
          ].map((item) => (
            <article key={item.title} className="text-center md:text-left">
              <h2 className="font-serif text-2xl font-bold text-[#0D4F2E]">{item.title}</h2>
              <p className="mt-2 text-sm leading-relaxed text-[#4A4A46]">{item.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[.18em] text-[#1A7A4A]">The menu</p>
            <h2 className="mt-1 font-serif text-3xl font-bold text-[#0D4F2E]">A taste of RealStick</h2>
          </div>
          <Link to="/menu" className="text-sm font-semibold text-[#1A7A4A] hover:underline">
            View full menu →
          </Link>
        </div>
        {productsQuery.isLoading ? <LoadingBlock label="Loading menu…" /> : null}
        {productsQuery.isError ? (
          <ErrorBanner message="Unable to load featured products right now." />
        ) : null}
        {!productsQuery.isLoading && !productsQuery.isError && !featured.length ? (
          <p className="rounded-2xl bg-white px-6 py-10 text-center text-sm text-[#8A8A84]">
            New flavours are on the way.
          </p>
        ) : null}
        {featured.length ? (
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {featured.map((product) => (
              <Link
                key={product.id}
                to="/menu"
                className="group overflow-hidden rounded-2xl border border-[#E0DDD5] bg-white shadow-[0_8px_30px_rgba(13,79,46,0.04)] transition hover:-translate-y-0.5 hover:shadow-[0_16px_40px_rgba(13,79,46,0.08)]"
              >
                <div
                  className="aspect-[4/3] bg-[#F3F1EB]"
                  style={{ borderBottom: `3px solid ${categoryColor(product.category_name)}` }}
                >
                  <ProductImage
                    src={product.image_url}
                    alt={product.name}
                    size="auto"
                    className="h-full w-full rounded-none object-cover"
                  />
                </div>
                <div className="px-4 py-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[.12em] text-[#8A8A84]">
                    {product.category_name}
                  </p>
                  <h3 className="mt-1 font-serif text-xl font-bold text-[#1A1A18]">{product.name}</h3>
                  {product.description ? (
                    <p className="mt-1 line-clamp-2 text-sm text-[#4A4A46]">{product.description}</p>
                  ) : null}
                </div>
              </Link>
            ))}
          </div>
        ) : null}
      </section>

      <section className="bg-[#0D4F2E] text-white">
        <div className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-6 px-4 py-14 sm:px-6 md:flex-row md:items-center">
          <div>
            <h2 className="font-serif text-3xl font-bold">See RealStick in season</h2>
            <p className="mt-2 max-w-lg text-sm text-white/70">
              Browse the gallery for product moments, or send the team a message.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link to="/gallery">
              <Button variant="onDark" className="min-h-11">
                View Gallery
              </Button>
            </Link>
            <Link to="/contact">
              <Button variant="outline" className="min-h-11 border-white text-white hover:bg-white/10">
                Contact Us
              </Button>
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
