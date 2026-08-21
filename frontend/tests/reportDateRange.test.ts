import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';

import {
  REPORT_RANGE_ERROR,
  customRangeValidationError,
  reportRequestParams,
  shouldFetchReports,
  validateCustomReportRange,
} from '../src/features/reports/reportDateRange.ts';

const root = dirname(fileURLToPath(import.meta.url));
const reportsPage = readFileSync(join(root, '../src/features/reports/ReportsPage.tsx'), 'utf8');
const reportsApi = readFileSync(join(root, '../src/lib/reportsApi.ts'), 'utf8');
const appSource = readFileSync(join(root, '../src/app/App.tsx'), 'utf8');
const dailySales = readFileSync(join(root, '../src/features/reports/DailySalesPage.tsx'), 'utf8');

describe('custom report date range validation', () => {
  it('requires start and end dates', () => {
    assert.equal(validateCustomReportRange('', '2026-08-10'), REPORT_RANGE_ERROR.startRequired);
    assert.equal(validateCustomReportRange('2026-08-01', ''), REPORT_RANGE_ERROR.endRequired);
    assert.equal(validateCustomReportRange('', ''), REPORT_RANGE_ERROR.startRequired);
  });

  it('rejects a start date after the end date', () => {
    assert.equal(
      validateCustomReportRange('2026-08-10', '2026-08-01'),
      'Start date cannot be after end date.',
    );
    assert.equal(validateCustomReportRange('2026-08-10', '2026-08-01'), REPORT_RANGE_ERROR.startAfterEnd);
  });

  it('accepts a valid range and equal start/end dates', () => {
    assert.equal(validateCustomReportRange('2026-08-01', '2026-08-10'), null);
    assert.equal(validateCustomReportRange('2026-08-10', '2026-08-10'), null);
  });

  it('does not validate custom dates for predefined filters', () => {
    assert.equal(customRangeValidationError('today', '', ''), null);
    assert.equal(customRangeValidationError('7d', '2026-08-10', '2026-08-01'), null);
    assert.equal(customRangeValidationError('30d', '', ''), null);
    assert.equal(customRangeValidationError('custom', '2026-08-10', '2026-08-01'), REPORT_RANGE_ERROR.startAfterEnd);
  });
});

describe('custom report request params', () => {
  it('keeps Today, Last 7 days, and Last 30 days as period-only requests', () => {
    assert.deepEqual(reportRequestParams('today', '2026-08-01', '2026-08-10'), { period: 'today' });
    assert.deepEqual(reportRequestParams('7d', '2026-08-01', '2026-08-10'), { period: '7d' });
    assert.deepEqual(reportRequestParams('30d', '', ''), { period: '30d' });
  });

  it('sends YYYY-MM-DD start_date and end_date for a custom range', () => {
    assert.deepEqual(reportRequestParams('custom', '2026-08-01', '2026-08-10'), {
      period: 'custom',
      start_date: '2026-08-01',
      end_date: '2026-08-10',
    });
    assert.equal(JSON.stringify(reportRequestParams('custom', '2026-08-01', '2026-08-10')).includes('08/10/2026'), false);
  });

  it('does not fetch when the custom range is invalid', () => {
    assert.equal(shouldFetchReports('today', '', ''), true);
    assert.equal(shouldFetchReports('7d', '', ''), true);
    assert.equal(shouldFetchReports('30d', '', ''), true);
    assert.equal(shouldFetchReports('custom', '2026-08-01', '2026-08-10'), true);
    assert.equal(shouldFetchReports('custom', '2026-08-10', '2026-08-10'), true);
    assert.equal(shouldFetchReports('custom', '', '2026-08-10'), false);
    assert.equal(shouldFetchReports('custom', '2026-08-01', ''), false);
    assert.equal(shouldFetchReports('custom', '2026-08-10', '2026-08-01'), false);
  });
});

describe('reports page custom date range UI', () => {
  it('keeps Today, Last 7 days, Last 30 days, and adds Custom Date Range', () => {
    assert.equal(reportsPage.includes('<option value="today">Today</option>'), true);
    assert.equal(reportsPage.includes('<option value="7d">Last 7 days</option>'), true);
    assert.equal(reportsPage.includes('<option value="30d">Last 30 days</option>'), true);
    assert.equal(reportsPage.includes('<option value="custom">Custom Date Range</option>'), true);
  });

  it('shows From/To date inputs when Custom Date Range is selected', () => {
    assert.equal(reportsPage.includes("period === 'custom'"), true);
    assert.equal(reportsPage.includes('label="From"'), true);
    assert.equal(reportsPage.includes('label="To"'), true);
    assert.equal(reportsPage.includes('type="date"'), true);
    assert.equal(reportsPage.includes('aria-label="Start date"'), true);
    assert.equal(reportsPage.includes('aria-label="End date"'), true);
    assert.equal(reportsPage.includes('setCustomFrom'), true);
    assert.equal(reportsPage.includes('setCustomTo'), true);
  });

  it('shows a UI validation message and does not call the API for an invalid range', () => {
    assert.equal(reportsPage.includes('customRangeValidationError'), true);
    assert.equal(reportsPage.includes('shouldFetchReports'), true);
    assert.equal(reportsPage.includes('enabled: canFetch'), true);
    assert.equal(reportsPage.includes('role="alert"'), true);
    assert.equal(reportsPage.includes('{rangeError}'), true);
  });

  it('preserves custom dates while switching predefined and custom filters', () => {
    assert.equal(reportsPage.includes("useState<ReportPeriod>('7d')"), true);
    assert.equal(reportsPage.includes("useState('')"), true);
    assert.equal(reportsPage.includes('setCustomFrom(') && reportsPage.includes('setPeriod('), true);
    assert.equal(reportsPage.includes("setCustomFrom('')"), false);
    assert.equal(reportsPage.includes("setCustomTo('')"), false);
  });

  it('uses existing loading and safe error handling', () => {
    assert.equal(reportsPage.includes('<LoadingBlock label="Loading reports…" />'), true);
    assert.equal(reportsPage.includes("apiErrorMessage(error, 'Unable to load reports.')"), true);
    assert.equal(reportsPage.includes('error.message'), false);
    assert.equal(reportsPage.includes('error.response'), false);
    assert.equal(reportsApi.includes('reportRequestParams'), true);
  });

  it('shares the same Reports page for admin and franchise owner', () => {
    assert.equal(appSource.includes('path="reports" element={<ReportsPage />}'), true);
    assert.equal(appSource.includes("roles={['SYSTEM_ADMIN', 'FRANCHISE_OWNER']}"), true);
    assert.equal(reportsPage.includes('franchise_id'), false);
    assert.equal(reportsApi.includes("api.get<ReportSummary>('/reports/summary'"), true);
  });

  it('does not add Custom Date Range to Daily Sales', () => {
    assert.equal(dailySales.includes('Custom Date Range'), false);
  });
});
