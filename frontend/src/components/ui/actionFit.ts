export const ACTION_FITS = ['sm', 'md', 'status', 'lg', 'xl', 'icon'] as const;
export type ActionFit = (typeof ACTION_FITS)[number];

/**
 * Stable action-control dimensions.
 * Pair toggling labels (Activate ↔ Deactivate) on the same `fit` so width does not jump.
 */
export const ACTION_FIT_CLASS: Record<ActionFit, string> = {
  sm: 'h-8 min-w-[4.75rem] shrink-0 px-3 py-0 text-[13px] leading-none whitespace-nowrap',
  md: 'h-8 min-w-[6.25rem] shrink-0 px-3 py-0 text-[13px] leading-none whitespace-nowrap',
  status: 'h-8 min-w-[7.5rem] shrink-0 px-3 py-0 text-[13px] leading-none whitespace-nowrap',
  lg: 'h-8 min-w-[8.75rem] shrink-0 px-3 py-0 text-[13px] leading-none whitespace-nowrap',
  xl: 'h-8 min-w-[11rem] shrink-0 px-3 py-0 text-[13px] leading-none whitespace-nowrap',
  icon: 'h-8 w-8 min-w-8 shrink-0 p-0 text-[13px] leading-none',
};

/** Horizontal cluster; wraps on small screens, unconstrained from md up. */
export const ACTION_GROUP_CLASS =
  'flex max-w-[16.5rem] flex-wrap items-center gap-1.5 md:max-w-none';

export const ACTION_GROUP_ALIGN: Record<'start' | 'end', string> = {
  start: 'justify-start',
  end: 'justify-end',
};

export const ACTIONS_TH_CLASS = 'px-4 py-3 text-left font-semibold whitespace-nowrap';
export const ACTIONS_TD_CLASS = 'px-4 py-3 text-left align-middle';

export const ACTION_SELECT_CLASS =
  'h-8 min-w-[6.5rem] shrink-0 rounded-lg border border-[#E0DDD5] bg-white px-2 text-[13px] font-semibold text-[#1A1A18] outline-none focus:border-[#1A7A4A]';
