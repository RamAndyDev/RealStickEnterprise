/** Official RealStick brand mark for the public hero. Not a generated product photograph. */
export function BrandHero() {
  return (
    <div className="relative mx-auto w-full max-w-[520px]">
      <img
        src="/brand/realstick-brand.svg"
        alt="RealStick — Real Fruits. Real Goodness."
        width={800}
        height={800}
        className="h-auto w-full object-contain"
        decoding="async"
        fetchPriority="high"
      />
    </div>
  );
}

/** Decorative fruit-popsicle composition kept for non-hero uses. */
export function HeroArt() {
  return <BrandHero />;
}
