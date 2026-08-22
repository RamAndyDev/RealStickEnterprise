export const DELETE_USER_TITLE = 'Delete User';
export const DELETE_USER_CONFIRM_MESSAGE = 'Are you sure you want to delete this user?';
export const DELETE_USER_SUCCESS = 'User deleted successfully.';
export const DELETE_USER_BLOCKED =
  'This user cannot be deleted because they are referenced by existing business records. Deactivate the user instead.';
export const DELETE_USER_FALLBACK = 'Unable to delete user.';

export function applyDeleteUserResult(
  deleteSucceeded: boolean,
  errorMessage?: string,
): { dialogOpen: boolean; error: string | null } {
  if (deleteSucceeded) {
    return { dialogOpen: false, error: null };
  }
  return {
    dialogOpen: true,
    error: errorMessage || DELETE_USER_FALLBACK,
  };
}
