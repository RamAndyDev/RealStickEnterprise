import { Link } from 'react-router-dom';

import { PublicPageMeta } from '../../components/layout/PublicLayout';
import { Button } from '../../components/ui';

export function AboutPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:py-16">
      <PublicPageMeta title="About | RealStick" />
      <p className="text-xs font-semibold uppercase tracking-[.18em] text-[#1A7A4A]">Our story</p>
      <h1 className="mt-2 font-serif text-4xl font-bold text-[#0D4F2E]">About RealStick</h1>
      <p className="mt-4 text-lg leading-relaxed text-[#4A4A46]">
        RealStick makes natural popsicles and kulfi. The brand is built around a simple idea:
        real fruit, made well.
      </p>

      <section className="mt-10 rounded-3xl bg-white px-6 py-8 shadow-[0_8px_30px_rgba(13,79,46,0.05)]">
        <h2 className="font-serif text-2xl font-bold text-[#0D4F2E]">Real Fruits. Real Goodness.</h2>
        <p className="mt-3 leading-relaxed text-[#4A4A46]">
          We keep the recipes clean: zero artificial colours, flavours, or preservatives. The
          popsicles and kulfi should taste like the fruit they come from.
        </p>
      </section>

      <section className="mt-6 grid gap-4 sm:grid-cols-3">
        {[
          { title: 'Natural popsicles', body: 'Fruit-forward sticks for warm days and everyday treats.' },
          { title: 'Kulfi', body: 'Heritage kulfi flavours, kept simple and honest.' },
          { title: 'Zero artificial', body: 'Zero Artificial · Zero Preservatives' },
        ].map((card) => (
          <article key={card.title} className="rounded-2xl border border-[#E0DDD5] bg-white px-5 py-6">
            <h2 className="font-serif text-xl font-bold text-[#1A1A18]">{card.title}</h2>
            <p className="mt-2 text-sm leading-relaxed text-[#4A4A46]">{card.body}</p>
          </article>
        ))}
      </section>

      <p className="mt-10 text-sm text-[#8A8A84]">
        Additional brand story, locations, and team notes can be added here as they are confirmed.
      </p>

      <div className="mt-8">
        <Link to="/contact">
          <Button className="min-h-11">Talk to the RealStick team</Button>
        </Link>
      </div>
    </div>
  );
}
