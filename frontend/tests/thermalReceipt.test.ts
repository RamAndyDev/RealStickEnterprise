import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';

const root = dirname(fileURLToPath(import.meta.url));
const receiptCss = readFileSync(
  join(root, '../src/features/pos/thermal-receipt.css'),
  'utf8',
);
const receiptPage = readFileSync(
  join(root, '../src/features/pos/ThermalReceiptPage.tsx'),
  'utf8',
);

describe('thermal receipt print readability', () => {
  it('preserves the 80mm browser-print layout', () => {
    assert.match(receiptCss, /@page\s*\{\s*size:\s*80mm auto;/);
    assert.match(receiptCss, /\.thermal-receipt\s*\{[^}]*width:\s*80mm/s);
    assert.match(receiptPage, /window\.print\(\)/);
    assert.match(receiptPage, /Bill No:/);
    assert.match(receiptPage, /GRAND TOTAL/);
    assert.match(receiptPage, /Payment Status/);
  });

  it('uses a high-contrast sans-serif type hierarchy', () => {
    assert.match(receiptCss, /font-family:\s*Arial, Helvetica, sans-serif/);
    assert.match(receiptCss, /\.thermal-receipt \.brand\s*\{[^}]*font-size:\s*22px;[^}]*font-weight:\s*800/s);
    assert.match(receiptCss, /\.thermal-receipt thead th\s*\{\s*font-weight:\s*800;/);
    assert.match(receiptCss, /\.thermal-receipt \.total td\s*\{[^}]*font-weight:\s*800;[^}]*font-size:\s*18px/s);
    assert.match(receiptCss, /\.thermal-receipt \.footer\s*\{[^}]*font-size:\s*11px;[^}]*color:\s*#000/s);
    assert.match(receiptCss, /-webkit-print-color-adjust:\s*exact/);
    assert.match(receiptCss, /print-color-adjust:\s*exact/);
    assert.match(receiptCss, /\.thermal-receipt hr\s*\{[^}]*border-top:\s*1px dashed #000/s);
    assert.match(receiptCss, /\.thermal-receipt \.total td\s*\{[^}]*border-top:\s*2px solid #000/s);
    assert.match(receiptCss, /\.thermal-receipt,\s*\.thermal-receipt \*\s*\{\s*color:\s*#000 !important;/);
  });

  it('keeps long item names in a bounded, wrapping table column', () => {
    assert.match(receiptPage, /<table className="items-table">/);
    assert.match(receiptPage, /<td className="item-name">\{item\.product_name_snapshot\}<\/td>/);
    assert.match(receiptCss, /\.thermal-receipt \.items-table th:first-child,\s*\.thermal-receipt \.items-table \.item-name\s*\{[^}]*width:\s*44%;[^}]*overflow-wrap:\s*anywhere/s);
    assert.match(receiptCss, /\.thermal-receipt \.items-table \.qty\s*\{[^}]*text-align:\s*center/s);
    assert.match(receiptCss, /\.thermal-receipt \.num\s*\{[^}]*text-align:\s*right;[^}]*white-space:\s*nowrap/s);
    assert.match(receiptCss, /\.thermal-receipt table\s*\{[^}]*width:\s*100%;[^}]*table-layout:\s*fixed/s);
    assert.match(receiptCss, /\.thermal-receipt\s*\{[^}]*width:\s*80mm;[^}]*max-width:\s*80mm/s);
  });

  it('does not introduce printer-density or ESC/POS commands', () => {
    assert.doesNotMatch(receiptCss, /ESC\/POS|GS\s*\(\s*L|density|heat dots/i);
  });
});
