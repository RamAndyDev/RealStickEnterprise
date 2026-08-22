import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';

import {
  ASSIGNMENT_PRICE_UPDATED,
  ASSIGNMENT_STATUS_UPDATED,
  ASSIGNMENT_UPDATED,
  assignmentUpdateSuccessMessage,
} from '../src/features/products/assignmentUpdate.ts';

const root = dirname(fileURLToPath(import.meta.url));
const detailPage = readFileSync(
  join(root, '../src/features/products/ProductDetailPage.tsx'),
  'utf8',
);
const panel = readFileSync(
  join(root, '../src/features/products/FranchiseProductsPanel.tsx'),
  'utf8',
);
const assignDialog = readFileSync(
  join(root, '../src/features/products/AssignProductsDialog.tsx'),
  'utf8',
);
const deleteDialog = readFileSync(
  join(root, '../src/features/products/DeleteProductDialog.tsx'),
  'utf8',
);

describe('assignment update success message', () => {
  it('uses the pricing message when only selling price changed', () => {
    assert.equal(
      assignmentUpdateSuccessMessage({ selling_price: 45 }),
      'Franchise pricing updated.',
    );
    assert.equal(assignmentUpdateSuccessMessage({ selling_price: 45 }), ASSIGNMENT_PRICE_UPDATED);
  });

  it('uses the status message when only assignment active/hidden changed', () => {
    assert.equal(
      assignmentUpdateSuccessMessage({ is_active: false }),
      'Product assignment status updated.',
    );
    assert.equal(
      assignmentUpdateSuccessMessage({ is_active: true }),
      ASSIGNMENT_STATUS_UPDATED,
    );
  });

  it('uses the combined message when price and assignment status both changed', () => {
    assert.equal(
      assignmentUpdateSuccessMessage({ selling_price: 45, is_active: true }),
      'Franchise product assignment updated.',
    );
    assert.equal(
      assignmentUpdateSuccessMessage({ selling_price: 30, is_active: false }),
      ASSIGNMENT_UPDATED,
    );
  });
});

describe('assignment update UI wiring', () => {
  it('keeps Product Detail price edits and status toggles as separate mutations', () => {
    assert.equal(detailPage.includes('assignmentUpdateSuccessMessage(variables)'), true);
    assert.equal(detailPage.includes('is_active: !row.is_active'), true);
    assert.equal(detailPage.includes('selling_price: Number(editPrice)'), true);
    assert.equal(detailPage.includes("? 'Assignment Active' : 'Assignment Hidden'"), true);
  });

  it('keeps Franchise Products Panel assignment behavior unchanged', () => {
    assert.equal(panel.includes('assignmentUpdateSuccessMessage(variables)'), true);
    assert.equal(panel.includes('is_active: !item.is_active'), true);
    assert.equal(panel.includes('selling_price: Number(editPrice)'), true);
    assert.equal(panel.includes("Assignment Active"), true);
    assert.equal(panel.includes("Assignment Hidden"), true);
    assert.equal(panel.includes('Product assignments saved.'), true);
  });

  it('does not change Assign Products dialog or product Delete', () => {
    assert.equal(assignDialog.includes('buildAssignmentSavePlan'), true);
    assert.equal(deleteDialog.includes('DELETE_PRODUCT_TITLE'), true);
    assert.equal(deleteDialog.includes('deleteProduct(productId)'), true);
  });
});
