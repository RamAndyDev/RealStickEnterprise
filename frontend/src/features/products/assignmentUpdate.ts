export const ASSIGNMENT_PRICE_UPDATED = 'Franchise pricing updated.';
export const ASSIGNMENT_STATUS_UPDATED = 'Product assignment status updated.';
export const ASSIGNMENT_UPDATED = 'Franchise product assignment updated.';

export type AssignmentUpdateFields = {
  selling_price?: number;
  is_active?: boolean;
};

export function assignmentUpdateSuccessMessage(update: AssignmentUpdateFields): string {
  const priceChanged = update.selling_price !== undefined;
  const statusChanged = update.is_active !== undefined;
  if (priceChanged && statusChanged) {
    return ASSIGNMENT_UPDATED;
  }
  if (statusChanged) {
    return ASSIGNMENT_STATUS_UPDATED;
  }
  return ASSIGNMENT_PRICE_UPDATED;
}
