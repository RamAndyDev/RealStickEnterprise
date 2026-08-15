/** Accent colors for known RealStick menus; unknown names fall back to brand green. */
export const CATEGORY_COLORS: Record<string, string> = {
  'Zest Collection': '#D97706',
  'Garden Collection': '#EC4899',
  'Harvest Collection': '#7C3AED',
  'The Reserve': '#1A7A4A',
  'Kulfi Heritage': '#E8621A',
};

export const DEFAULT_CATEGORY_COLOR = '#1A7A4A';

const FALLBACK_PALETTE = ['#0F766E', '#B45309', '#BE185D', '#4338CA', '#15803D', '#C2410C'];

export function categoryColor(name: string | null | undefined): string {
  if (!name) return DEFAULT_CATEGORY_COLOR;
  if (CATEGORY_COLORS[name]) return CATEGORY_COLORS[name];
  let hash = 0;
  for (let i = 0; i < name.length; i += 1) hash = (hash + name.charCodeAt(i) * (i + 1)) % 997;
  return FALLBACK_PALETTE[hash % FALLBACK_PALETTE.length];
}
