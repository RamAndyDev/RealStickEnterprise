import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';

import {
  DELETE_PRODUCT_BLOCKED,
  DELETE_PRODUCT_CONFIRM_MESSAGE,
  DELETE_PRODUCT_FALLBACK,
  DELETE_PRODUCT_SUCCESS,
  DELETE_PRODUCT_TITLE,
  applyDeleteProductResult,
  productDeleteIsAvailable,
} from '../src/features/products/deleteProduct.ts';

const root = dirname(fileURLToPath(import.meta.url));
const menuPage = readFileSync(join(root, '../src/features/products/MenuPage.tsx'), 'utf8');
const detailPage = readFileSync(
  join(root, '../src/features/products/ProductDetailPage.tsx'),
  'utf8',
);
const dialog = readFileSync(
  join(root, '../src/features/products/DeleteProductDialog.tsx'),
  'utf8',
);
const productsApi = readFileSync(join(root, '../src/lib/productsApi.ts'), 'utf8');

describe('product delete availability', () => {
  it('is available for both active and inactive products', () => {
    assert.equal(productDeleteIsAvailable(true), true);
    assert.equal(productDeleteIsAvailable(false), true);
  });
});

describe('delete product dialog result', () => {
  it('closes the dialog after a successful delete', () => {
    assert.deepEqual(applyDeleteProductResult(true), { dialogOpen: false, error: null });
  });

  it('keeps the dialog open and surfaces the backend error after a failed delete', () => {
    assert.deepEqual(applyDeleteProductResult(false, DELETE_PRODUCT_BLOCKED), {
      dialogOpen: true,
      error: DELETE_PRODUCT_BLOCKED,
    });
    assert.deepEqual(applyDeleteProductResult(false), {
      dialogOpen: true,
      error: DELETE_PRODUCT_FALLBACK,
    });
  });
});

describe('Admin product list delete action', () => {
  it('keeps Edit, Activate/Deactivate, and Delete in the same action group', () => {
    const start = menuPage.lastIndexOf('<ActionGroup>');
    const group = menuPage.slice(start, menuPage.indexOf('</ActionGroup>', start));
    assert.equal(group.includes('Edit'), true);
    assert.equal(group.includes("item.is_active ? 'Active' : 'Hidden'"), true);
    assert.equal(group.includes('Delete'), true);
    assert.equal(group.includes('ActionButton'), true);
  });

  it('does not change Activate/Deactivate into Delete', () => {
    assert.equal(menuPage.includes("updateProduct(id, { is_active })"), true);
    assert.equal(menuPage.includes('toggleMutation'), true);
    assert.equal(menuPage.includes("Item set to Active."), true);
    assert.equal(menuPage.includes("Item set to Hidden."), true);
  });

  it('opens a confirmation dialog instead of deleting immediately', () => {
    assert.equal(menuPage.includes('setDeleteTarget(item)'), true);
    assert.equal(menuPage.includes('DeleteProductDialog'), true);
    assert.equal(menuPage.includes('window.alert'), false);
    assert.equal(menuPage.includes('window.confirm'), false);
    assert.equal(menuPage.includes('alert('), false);
    assert.equal(menuPage.includes('confirm('), false);
  });

  it('refreshes the product list after a successful delete', () => {
    const dialogUsage = menuPage.slice(menuPage.lastIndexOf('<DeleteProductDialog'));
    assert.equal(dialogUsage.includes('DELETE_PRODUCT_SUCCESS'), true);
    assert.equal(dialogUsage.includes('await invalidate()'), true);
  });
});

describe('Delete Product confirmation dialog', () => {
  it('uses the existing Modal with the required copy', () => {
    assert.equal(dialog.includes('title={DELETE_PRODUCT_TITLE}'), true);
    assert.equal(dialog.includes('{DELETE_PRODUCT_CONFIRM_MESSAGE}'), true);
    assert.equal(DELETE_PRODUCT_TITLE, 'Delete Product');
    assert.equal(DELETE_PRODUCT_CONFIRM_MESSAGE, 'Are you sure you want to delete this product?');
    assert.equal(dialog.includes('<Modal'), true);
    assert.equal(dialog.includes('window.confirm'), false);
    assert.equal(dialog.includes('alert('), false);
  });

  it('cancel closes without calling delete', () => {
    assert.equal(dialog.includes('Cancel'), true);
    assert.equal(dialog.includes('onClick={onClose}'), true);
    const cancelBlock = dialog.slice(dialog.indexOf('Cancel') - 120, dialog.indexOf('Cancel') + 20);
    assert.equal(cancelBlock.includes('deleteProduct'), false);
    assert.equal(cancelBlock.includes('mutate'), false);
  });

  it('keeps the dialog open and shows the backend error on failure', () => {
    const successBlock = dialog.slice(dialog.indexOf('onSuccess'), dialog.indexOf('onError'));
    const errorBlock = dialog.slice(dialog.indexOf('onError'), dialog.indexOf('return ('));
    assert.equal(successBlock.includes('onClose()'), true);
    assert.equal(errorBlock.includes('onClose()'), false);
    assert.equal(errorBlock.includes('setError(result.error)'), true);
    assert.equal(dialog.includes('<ErrorBanner message={error} />'), true);
    assert.equal(dialog.includes('DELETE_PRODUCT_FALLBACK'), true);
  });
});

describe('Product detail delete action', () => {
  it('adds Delete next to the existing lifecycle action', () => {
    assert.equal(detailPage.includes('Set Hidden'), true);
    assert.equal(detailPage.includes('Set Active'), true);
    assert.equal(detailPage.includes('DeleteProductDialog'), true);
    assert.equal(detailPage.includes('Delete'), true);
  });

  it('returns to the product list after a successful delete', () => {
    assert.equal(detailPage.includes("navigate('/products', { state: { productDeleted: true } })"), true);
    assert.equal(menuPage.includes('productDeleted'), true);
    assert.equal(menuPage.includes('DELETE_PRODUCT_SUCCESS'), true);
  });
});

describe('product delete API client', () => {
  it('calls the admin product delete endpoint', () => {
    assert.equal(productsApi.includes('export async function deleteProduct'), true);
    assert.equal(productsApi.includes('api.delete(`/admin/products/${id}`)'), true);
  });
});

describe('copy', () => {
  it('uses the required success and blocked messages', () => {
    assert.equal(DELETE_PRODUCT_SUCCESS, 'Product deleted successfully.');
    assert.equal(
      DELETE_PRODUCT_BLOCKED,
      'This product cannot be deleted because it is already used in existing business records. Deactivate it instead.',
    );
  });
});
