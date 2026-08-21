import { RealStickLogo } from '../../components/branding/RealStickLogo';

/** Official RealStick brand mark for the public hero. Not a generated product photograph. */
export function BrandHero() {
  return (
    <div className="relative mx-auto w-full max-w-[360px] sm:max-w-[420px]">
      <RealStickLogo className="h-auto w-full" />
    </div>
  );
}

/** Official RealStick brand mark for the public hero. */
export function HeroArt() {
  return <BrandHero />;
}
