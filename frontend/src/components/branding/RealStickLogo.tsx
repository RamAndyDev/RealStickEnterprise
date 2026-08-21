import { REALSTICK_LOGO_ALT, REALSTICK_LOGO_SRC } from './brand';

type RealStickLogoProps = {
  className?: string;
  alt?: string;
};

export function RealStickLogo({
  className = 'h-10 w-auto',
  alt = REALSTICK_LOGO_ALT,
}: RealStickLogoProps) {
  return (
    <img
      src={REALSTICK_LOGO_SRC}
      alt={alt}
      className={`object-contain ${className}`.trim()}
      decoding="async"
    />
  );
}
