export const DELETE_FRANCHISE_TITLE = 'Delete Franchise';
export const DELETE_FRANCHISE_CONFIRM_MESSAGE = 'Are you sure you want to delete this franchise?';
export const DELETE_FRANCHISE_SUCCESS = 'Franchise deleted successfully.';
export const DELETE_FRANCHISE_BLOCKED =
  'This franchise cannot be deleted because it is already used in existing business records. Deactivate it instead.';
export const DELETE_FRANCHISE_FALLBACK = 'Unable to delete franchise.';

export function applyDeleteFranchiseResult(
  deleteSucceeded: boolean,
  errorMessage?: string,
): { dialogOpen: boolean; error: string | null } {
  if (deleteSucceeded) {
    return { dialogOpen: false, error: null };
  }
  return {
    dialogOpen: true,
    error: errorMessage || DELETE_FRANCHISE_FALLBACK,
  };
}
