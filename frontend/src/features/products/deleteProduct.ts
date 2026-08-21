export const DELETE_PRODUCT_TITLE = 'Delete Product';
export const DELETE_PRODUCT_CONFIRM_MESSAGE = 'Are you sure you want to delete this product?';
export const DELETE_PRODUCT_SUCCESS = 'Product deleted successfully.';
export const DELETE_PRODUCT_BLOCKED =
  'This product cannot be deleted because it is already used in existing business records. Deactivate it instead.';
export const DELETE_PRODUCT_FALLBACK = 'Unable to delete product.';

export function productDeleteIsAvailable(_isActive: boolean): boolean {
  return true;
}

export function applyDeleteProductResult(
  deleteSucceeded: boolean,
  errorMessage?: string,
): { dialogOpen: boolean; error: string | null } {
  if (deleteSucceeded) {
    return { dialogOpen: false, error: null };
  }
  return {
    dialogOpen: true,
    error: errorMessage || DELETE_PRODUCT_FALLBACK,
  };
}
