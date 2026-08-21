export const UNCATEGORIZED_ID = '__uncategorized__';
export const UNCATEGORIZED_NAME = 'Uncategorized';

export type AssignProductRow = {
  id: string;
  name: string;
  price: number;
  categoryId: string;
  categoryName: string;
  categoryOrder: number;
};

export type AssignmentSnapshot = {
  productId: string;
  sellingPrice: number;
  isActive: boolean;
};

export type AssignDraftItem = {
  selected: boolean;
  sellingPrice: string;
};

export type AssignDraft = Record<string, AssignDraftItem>;

export type CategoryProductGroup = {
  id: string;
  name: string;
  displayOrder: number;
  products: AssignProductRow[];
};

export type CategorySelectionState = 'none' | 'some' | 'all';

export type AssignmentSaveAction =
  | { type: 'create'; productId: string; sellingPrice: number }
  | { type: 'activate'; productId: string; sellingPrice?: number }
  | { type: 'updatePrice'; productId: string; sellingPrice: number }
  | { type: 'deactivate'; productId: string };

export function initialAssignDraft(
  products: AssignProductRow[],
  snapshots: Map<string, AssignmentSnapshot>,
): AssignDraft {
  const draft: AssignDraft = {};
  for (const product of products) {
    const snapshot = snapshots.get(product.id);
    draft[product.id] = {
      selected: snapshot?.isActive === true,
      sellingPrice: snapshot != null ? formatSellingPriceInput(snapshot.sellingPrice) : '',
    };
  }
  return draft;
}

export function formatSellingPriceInput(value: number): string {
  if (Number.isInteger(value)) return String(value);
  return value.toFixed(2).replace(/\.?0+$/, '');
}

export function groupProductsByCategory(products: AssignProductRow[]): CategoryProductGroup[] {
  const groups = new Map<string, CategoryProductGroup>();
  for (const product of products) {
    const existing = groups.get(product.categoryId);
    if (existing) {
      existing.products.push(product);
      continue;
    }
    groups.set(product.categoryId, {
      id: product.categoryId,
      name: product.categoryName,
      displayOrder: product.categoryOrder,
      products: [product],
    });
  }

  return [...groups.values()]
    .map((group) => ({
      ...group,
      products: [...group.products].sort((a, b) => a.name.localeCompare(b.name)),
    }))
    .sort((a, b) => {
      if (a.id === UNCATEGORIZED_ID) return 1;
      if (b.id === UNCATEGORIZED_ID) return -1;
      return a.displayOrder - b.displayOrder || a.name.localeCompare(b.name);
    });
}

export function filterGroupedProducts(
  groups: CategoryProductGroup[],
  query: string,
): CategoryProductGroup[] {
  const needle = query.trim().toLowerCase();
  if (!needle) return groups;

  return groups
    .map((group) => {
      const categoryMatches = group.name.toLowerCase().includes(needle);
      const products = categoryMatches
        ? group.products
        : group.products.filter((product) => product.name.toLowerCase().includes(needle));
      return { ...group, products };
    })
    .filter((group) => group.products.length > 0);
}

export function categorySelectionState(
  productIds: string[],
  draft: AssignDraft,
): CategorySelectionState {
  if (!productIds.length) return 'none';
  const selectedCount = productIds.filter((id) => draft[id]?.selected).length;
  if (selectedCount === 0) return 'none';
  if (selectedCount === productIds.length) return 'all';
  return 'some';
}

export function setCategorySelected(
  draft: AssignDraft,
  productIds: string[],
  selected: boolean,
): AssignDraft {
  const next = { ...draft };
  for (const id of productIds) {
    const current = next[id] ?? { selected: false, sellingPrice: '' };
    next[id] = { ...current, selected };
  }
  return next;
}

export function setProductSelected(
  draft: AssignDraft,
  productId: string,
  selected: boolean,
): AssignDraft {
  const current = draft[productId] ?? { selected: false, sellingPrice: '' };
  return {
    ...draft,
    [productId]: { ...current, selected },
  };
}

export function setProductSellingPrice(
  draft: AssignDraft,
  productId: string,
  sellingPrice: string,
): AssignDraft {
  const current = draft[productId] ?? { selected: false, sellingPrice: '' };
  return {
    ...draft,
    [productId]: { ...current, sellingPrice },
  };
}

export function draftValidationErrors(
  products: AssignProductRow[],
  draft: AssignDraft,
  validatePrice: (value: string, masterPrice: number | null | undefined) => string | null,
): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const product of products) {
    if (!draft[product.id]?.selected) continue;
    const message = validatePrice(draft[product.id]?.sellingPrice ?? '', product.price);
    if (message) errors[product.id] = message;
  }
  return errors;
}

export function pricesEqual(left: number, right: number): boolean {
  return Math.round(left * 100) === Math.round(right * 100);
}

export function buildAssignmentSavePlan(
  products: AssignProductRow[],
  draft: AssignDraft,
  snapshots: Map<string, AssignmentSnapshot>,
): AssignmentSaveAction[] {
  const actions: AssignmentSaveAction[] = [];
  const seen = new Set<string>();

  for (const product of products) {
    if (seen.has(product.id)) continue;
    seen.add(product.id);

    const item = draft[product.id] ?? { selected: false, sellingPrice: '' };
    const snapshot = snapshots.get(product.id);
    const nextPrice = Number(item.sellingPrice);

    if (item.selected) {
      if (!snapshot) {
        actions.push({ type: 'create', productId: product.id, sellingPrice: nextPrice });
        continue;
      }
      if (!snapshot.isActive) {
        actions.push(
          pricesEqual(nextPrice, snapshot.sellingPrice)
            ? { type: 'activate', productId: product.id }
            : { type: 'activate', productId: product.id, sellingPrice: nextPrice },
        );
        continue;
      }
      if (!pricesEqual(nextPrice, snapshot.sellingPrice)) {
        actions.push({ type: 'updatePrice', productId: product.id, sellingPrice: nextPrice });
      }
      continue;
    }

    if (snapshot?.isActive) {
      actions.push({ type: 'deactivate', productId: product.id });
    }
  }

  return actions;
}
