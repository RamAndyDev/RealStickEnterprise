import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { PublicPageMeta } from '../../components/layout/PublicLayout';
import { EmptyState, ErrorBanner, LoadingBlock } from '../../components/ui';
import { fetchPublicCategories, fetchPublicProducts } from '../../lib/publicApi';
import { apiErrorMessage } from '../franchises/status';
import { ProductImage } from '../products/ProductImage';
import { categoryColor } from '../products/categoryColors';

export function PublicMenuPage() {
  const [category, setCategory] = useState('All');
  const categoriesQuery = useQuery({
    queryKey: ['public-categories'],
    queryFn: fetchPublicCategories,
  });
  const productsQuery = useQuery({
    queryKey: ['public-products'],
    queryFn: fetchPublicProducts,
  });

  const chips = useMemo(() => {
    const names = (categoriesQuery.data?.items ?? []).map((row) => row.name);
    return ['All', ...names];
  }, [categoriesQuery.data]);

  const visible = useMemo(() => {
    const items = productsQuery.data?.items ?? [];
    if (category === 'All') return items;
    return items.filter((item) => item.category_name === category);
  }, [productsQuery.data, category]);

  const loading = categoriesQuery.isLoading || productsQuery.isLoading;
  const error = categoriesQuery.error || productsQuery.error;

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:py-14">
      <PublicPageMeta title="Menu | RealStick" />
      <p className="text-xs font-semibold uppercase tracking-[.18em] text-[#1A7A4A]">Catalogue</p>
      <h1 className="mt-2 font-serif text-4xl font-bold text-[#0D4F2E]">The Menu</h1>
      <p className="mt-3 max-w-2xl text-[#4A4A46]">
        Natural popsicles and kulfi, grouped by collection. Prices are available at RealStick outlets.
      </p>

      {loading ? <div className="mt-8"><LoadingBlock label="Loading menu…" /></div> : null}
      {error ? (
        <div className="mt-8">
          <ErrorBanner message={apiErrorMessage(error, 'Unable to load the public menu.')} />
        </div>
      ) : null}

      {!loading && !error ? (
        <>
          <div className="mt-8 flex flex-wrap gap-2" role="tablist" aria-label="Product categories">
            {chips.map((chip) => {
              const selected = category === chip;
              const color = chip === 'All' ? '#0D4F2E' : categoryColor(chip);
              return (
                <button
                  key={chip}
                  type="button"
                  role="tab"
                  aria-selected={selected}
                  onClick={() => setCategory(chip)}
                  className="min-h-11 rounded-full px-4 text-sm font-semibold transition"
                  style={{
                    background: selected ? color : 'transparent',
                    color: selected ? '#fff' : '#4A4A46',
                    border: selected ? 'none' : '1px solid #E0DDD5',
                  }}
                >
                  {chip}
                </button>
              );
            })}
          </div>

          {!visible.length ? (
            <div className="mt-10">
              <EmptyState title="Menu coming soon" hint="Active flavours will appear here." />
            </div>
          ) : (
            <div className="mt-8 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {visible.map((product) => {
                const color = categoryColor(product.category_name);
                return (
                  <article
                    key={product.id}
                    className="overflow-hidden rounded-2xl border border-[#E0DDD5] bg-white shadow-[0_8px_30px_rgba(13,79,46,0.04)] transition hover:-translate-y-0.5 hover:shadow-[0_16px_40px_rgba(13,79,46,0.08)]"
                  >
                    <div className="aspect-[4/3] bg-[#F3F1EB]">
                      <ProductImage
                        src={product.image_url}
                        alt={product.name}
                        size="auto"
                        className="h-full w-full rounded-none object-cover"
                      />
                    </div>
                    <div className="border-t-2 px-4 py-4" style={{ borderColor: color }}>
                      <p className="text-[11px] font-semibold uppercase tracking-[.12em] text-[#8A8A84]">
                        {product.category_name}
                      </p>
                      <h2 className="mt-1 font-serif text-xl font-bold text-[#1A1A18]">{product.name}</h2>
                      {product.description ? (
                        <p className="mt-1 text-sm leading-relaxed text-[#4A4A46]">{product.description}</p>
                      ) : null}
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </>
      ) : null}
    </div>
  );
}
