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

  it('uses high contrast and retains bold hierarchy for print', () => {
    assert.match(receiptCss, /\.thermal-receipt thead th\s*\{\s*font-weight:\s*700;/);
    assert.match(receiptCss, /\.thermal-receipt \.total td\s*\{[^}]*font-weight:\s*700/s);
    assert.match(receiptCss, /\.thermal-receipt \.footer\s*\{[^}]*color:\s*#111/s);
    assert.match(receiptCss, /-webkit-print-color-adjust:\s*exact/);
    assert.match(receiptCss, /print-color-adjust:\s*exact/);
    assert.match(receiptCss, /\.thermal-receipt hr\s*\{[^}]*border-top:\s*1px dashed #555/s);
    assert.match(receiptCss, /\.thermal-receipt \.brand,\s*\.thermal-receipt \.footer\s*\{\s*color:\s*#000 !important;/);
    assert.match(receiptCss, /\.thermal-receipt hr\s*\{\s*border-top-color:\s*#000;/);
  });

  it('does not introduce printer-density or ESC/POS commands', () => {
    assert.doesNotMatch(receiptCss, /ESC\/POS|GS\s*\(\s*L|density|heat dots/i);
  });
});
