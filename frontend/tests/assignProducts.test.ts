import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import { sellingPriceError } from '../src/types/product.ts';
import {
  UNCATEGORIZED_NAME,
  buildAssignmentSavePlan,
  categorySelectionState,
  draftValidationErrors,
  filterGroupedProducts,
  groupProductsByCategory,
  initialAssignDraft,
  setCategorySelected,
  setProductSelected,
  setProductSellingPrice,
  type AssignProductRow,
  type AssignmentSnapshot,
} from '../src/features/products/assignProducts.ts';

function product(
  overrides: Partial<AssignProductRow> & Pick<AssignProductRow, 'id' | 'name' | 'price'>,
): AssignProductRow {
  return {
    categoryId: 'cat-heritage',
    categoryName: 'Kulfi Heritage',
    categoryOrder: 10,
    ...overrides,
  };
}

describe('groupProductsByCategory', () => {
  it('groups products by category and hides empty categories', () => {
    const groups = groupProductsByCategory([
      product({ id: 'choc', name: 'Chocolate Kulfi', price: 120, categoryOrder: 10 }),
      product({
        id: 'mango-pop',
        name: 'Mango Popsicle',
        price: 80,
        categoryId: 'cat-summer',
        categoryName: 'Summer Specials',
        categoryOrder: 20,
      }),
      product({ id: 'pista', name: 'Pistachio Kulfi', price: 150 }),
    ]);

    assert.deepEqual(
      groups.map((group) => ({
        name: group.name,
        products: group.products.map((item) => item.name),
      })),
      [
        { name: 'Kulfi Heritage', products: ['Chocolate Kulfi', 'Pistachio Kulfi'] },
        { name: 'Summer Specials', products: ['Mango Popsicle'] },
      ],
    );
  });

  it('places uncategorized products last without fabricating empty groups', () => {
    const groups = groupProductsByCategory([
      product({
        id: 'loose',
        name: 'Loose Stick',
        price: 40,
        categoryId: '__uncategorized__',
        categoryName: UNCATEGORIZED_NAME,
        categoryOrder: Number.MAX_SAFE_INTEGER,
      }),
      product({ id: 'choc', name: 'Chocolate Kulfi', price: 120 }),
    ]);

    assert.equal(groups.length, 2);
    assert.equal(groups[0]?.name, 'Kulfi Heritage');
    assert.equal(groups[1]?.name, UNCATEGORIZED_NAME);
  });
});

describe('assignment draft selection', () => {
  const catalog = [
    product({ id: 'a', name: 'Chocolate Kulfi', price: 120 }),
    product({ id: 'b', name: 'Pistachio Kulfi', price: 150 }),
    product({ id: 'c', name: 'Mango Kulfi', price: 130 }),
    product({
      id: 'd',
      name: 'Mango Popsicle',
      price: 80,
      categoryId: 'cat-summer',
      categoryName: 'Summer Specials',
      categoryOrder: 20,
    }),
  ];

  it('pre-selects currently assigned active products', () => {
    const snapshots = new Map<string, AssignmentSnapshot>([
      ['a', { productId: 'a', sellingPrice: 110, isActive: true }],
      ['c', { productId: 'c', sellingPrice: 120, isActive: true }],
      ['b', { productId: 'b', sellingPrice: 90, isActive: false }],
    ]);
    const draft = initialAssignDraft(catalog, snapshots);

    assert.equal(draft.a?.selected, true);
    assert.equal(draft.a?.sellingPrice, '110');
    assert.equal(draft.b?.selected, false);
    assert.equal(draft.c?.selected, true);
    assert.equal(draft.d?.selected, false);
  });

  it('selects and deselects an entire category, including indeterminate state', () => {
    const snapshots = new Map<string, AssignmentSnapshot>([
      ['a', { productId: 'a', sellingPrice: 110, isActive: true }],
    ]);
    let draft = initialAssignDraft(catalog, snapshots);
    const heritageIds = ['a', 'b', 'c'];

    assert.equal(categorySelectionState(heritageIds, draft), 'some');

    draft = setCategorySelected(draft, heritageIds, true);
    assert.equal(categorySelectionState(heritageIds, draft), 'all');
    assert.equal(draft.b?.selected, true);
    assert.equal(draft.c?.selected, true);

    draft = setCategorySelected(draft, heritageIds, false);
    assert.equal(categorySelectionState(heritageIds, draft), 'none');
    assert.equal(draft.a?.selected, false);
  });
});

describe('search filtering', () => {
  it('hides categories with no matches and keeps selections', () => {
    const catalog = [
      product({ id: 'choc', name: 'Chocolate Kulfi', price: 120 }),
      product({
        id: 'mango-pop',
        name: 'Mango Popsicle',
        price: 80,
        categoryId: 'cat-summer',
        categoryName: 'Summer Specials',
        categoryOrder: 20,
      }),
    ];
    const groups = groupProductsByCategory(catalog);
    let draft = initialAssignDraft(catalog, new Map());
    draft = setProductSelected(draft, 'choc', true);
    draft = setProductSellingPrice(draft, 'choc', '110');

    const byName = filterGroupedProducts(groups, 'pistachio');
    assert.equal(byName.length, 0);

    const byCategory = filterGroupedProducts(groups, 'summer');
    assert.equal(byCategory.length, 1);
    assert.equal(byCategory[0]?.name, 'Summer Specials');

    const restored = filterGroupedProducts(groups, '');
    assert.equal(restored.length, 2);
    assert.equal(draft.choc?.selected, true);
    assert.equal(draft.choc?.sellingPrice, '110');
  });
});

describe('selling price validation', () => {
  it('allows selling prices below, equal to, and above the master price', () => {
    assert.equal(sellingPriceError('50'), null);
    assert.equal(sellingPriceError('80'), null);
    assert.equal(sellingPriceError('99'), null);
    assert.equal(sellingPriceError('100'), null);
    assert.equal(sellingPriceError('120'), null);
    assert.equal(sellingPriceError('150'), null);
  });

  it('rejects empty, invalid format, zero, and negative selling prices', () => {
    assert.equal(sellingPriceError(''), 'Franchise selling price is required.');
    assert.equal(sellingPriceError('0'), 'Selling price must be greater than 0.');
    assert.equal(sellingPriceError('-1'), 'Enter a valid price with up to 2 decimal places.');
    assert.equal(sellingPriceError('12.345'), 'Enter a valid price with up to 2 decimal places.');
  });

  it('blocks save only for selected products with invalid selling prices', () => {
    const catalog = [
      product({ id: 'a', name: 'Chocolate Kulfi', price: 120 }),
      product({ id: 'b', name: 'Pistachio Kulfi', price: 150 }),
      product({ id: 'c', name: 'Mango Kulfi', price: 100 }),
    ];
    const draft = {
      a: { selected: true, sellingPrice: '120' },
      b: { selected: true, sellingPrice: '180' },
      c: { selected: true, sellingPrice: '0' },
    };
    const errors = draftValidationErrors(catalog, draft, sellingPriceError);
    assert.equal(errors.a, undefined);
    assert.equal(errors.b, undefined);
    assert.equal(errors.c, 'Selling price must be greater than 0.');
  });
});

describe('assignment save plan', () => {
  const catalog = [
    product({ id: 'a', name: 'Chocolate Kulfi', price: 120 }),
    product({ id: 'b', name: 'Pistachio Kulfi', price: 150 }),
    product({ id: 'c', name: 'Mango Kulfi', price: 130 }),
    product({
      id: 'd',
      name: 'Strawberry Popsicle',
      price: 90,
      categoryId: 'cat-summer',
      categoryName: 'Summer Specials',
      categoryOrder: 20,
    }),
  ];

  it('creates, keeps, updates, and unassigns without duplicate creates', () => {
    const snapshots = new Map<string, AssignmentSnapshot>([
      ['a', { productId: 'a', sellingPrice: 110, isActive: true }],
      ['b', { productId: 'b', sellingPrice: 140, isActive: true }],
      ['c', { productId: 'c', sellingPrice: 120, isActive: true }],
    ]);
    const draft = {
      a: { selected: true, sellingPrice: '110' },
      b: { selected: false, sellingPrice: '140' },
      c: { selected: true, sellingPrice: '115' },
      d: { selected: true, sellingPrice: '85' },
    };

    const plan = buildAssignmentSavePlan(catalog, draft, snapshots);
    assert.deepEqual(plan, [
      { type: 'deactivate', productId: 'b' },
      { type: 'updatePrice', productId: 'c', sellingPrice: 115 },
      { type: 'create', productId: 'd', sellingPrice: 85 },
    ]);
    assert.equal(plan.filter((action) => action.productId === 'a').length, 0);
    assert.equal(plan.filter((action) => action.type === 'create' && action.productId === 'c').length, 0);
  });

  it('reactivates an existing inactive assignment instead of creating a duplicate', () => {
    const snapshots = new Map<string, AssignmentSnapshot>([
      ['b', { productId: 'b', sellingPrice: 140, isActive: false }],
    ]);
    const draft = {
      a: { selected: false, sellingPrice: '' },
      b: { selected: true, sellingPrice: '140' },
      c: { selected: false, sellingPrice: '' },
      d: { selected: false, sellingPrice: '' },
    };

    assert.deepEqual(buildAssignmentSavePlan(catalog, draft, snapshots), [
      { type: 'activate', productId: 'b' },
    ]);
  });
});
