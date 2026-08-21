import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';

import { REPORT_RANGE_ERROR, reportRequestParams, shouldFetchReports } from '../src/features/reports/reportDateRange.ts';
import {
  REPORT_EXPORT_ERROR,
  REPORT_EXPORT_SUCCESS,
  filenameFromContentDisposition,
  salesReportDownloadName,
  toReportExportError,
} from '../src/features/reports/reportExport.ts';

const root = dirname(fileURLToPath(import.meta.url));
const reportsPage = readFileSync(join(root, '../src/features/reports/ReportsPage.tsx'), 'utf8');
const reportsApi = readFileSync(join(root, '../src/lib/reportsApi.ts'), 'utf8');
const reportExport = readFileSync(join(root, '../src/features/reports/reportExport.ts'), 'utf8');
const reportDateRange = readFileSync(join(root, '../src/features/reports/reportDateRange.ts'), 'utf8');
const dailySales = readFileSync(join(root, '../src/features/reports/DailySalesPage.tsx'), 'utf8');

function axiosLikeError(options: {
  status?: number;
  statusText?: string;
  detail?: unknown;
  message?: string;
  blobDetail?: string;
}) {
  const error = new Error(
    options.message ??
      (options.status != null ? `Request failed with status code ${options.status}` : 'Error'),
  );
  let data: unknown = options.detail !== undefined ? { detail: options.detail } : {};
  if (options.blobDetail != null) {
    data = new Blob([JSON.stringify({ detail: options.blobDetail })], { type: 'application/json' });
  }
  const response =
    options.status == null
      ? undefined
      : {
          status: options.status,
          statusText: options.statusText,
          data,
        };
  Object.assign(error, {
    isAxiosError: true,
    response,
  });
  return error;
}

describe('Generate Report button', () => {
  it('is present on the Reports page', () => {
    assert.equal(reportsPage.includes('Generate Report'), true);
    assert.equal(reportsPage.includes("generating ? 'Generating...' : 'Generate Report'"), true);
  });

  it('uses the currently selected filter and custom range', () => {
    assert.equal(reportsPage.includes('exportSalesReport(period, customFrom, customTo)'), true);
    assert.equal(reportsApi.includes("api.get<Blob>('/reports/export'"), true);
    assert.equal(reportsApi.includes('reportRequestParams(period, startDate, endDate)'), true);
    assert.equal(reportsApi.includes("responseType: 'blob'"), true);
    assert.equal(reportsPage.includes('franchise_id'), false);
    assert.deepEqual(reportRequestParams('today', '2026-08-01', '2026-08-10'), { period: 'today' });
    assert.deepEqual(reportRequestParams('custom', '2026-08-01', '2026-08-10'), {
      period: 'custom',
      start_date: '2026-08-01',
      end_date: '2026-08-10',
    });
  });

  it('prevents generation when the custom range is invalid', () => {
    assert.equal(shouldFetchReports('today', '', ''), true);
    assert.equal(shouldFetchReports('7d', '', ''), true);
    assert.equal(shouldFetchReports('30d', '', ''), true);
    assert.equal(shouldFetchReports('custom', '2026-08-01', '2026-08-10'), true);
    assert.equal(shouldFetchReports('custom', '', '2026-08-10'), false);
    assert.equal(shouldFetchReports('custom', '2026-08-01', ''), false);
    assert.equal(shouldFetchReports('custom', '2026-08-10', '2026-08-01'), false);
    assert.equal(reportsPage.includes('shouldFetchReports'), true);
    assert.equal(reportsPage.includes('const canGenerate = canFetch'), true);
    assert.equal(reportsPage.includes('disabled={!canGenerate || generating}'), true);
    assert.equal(reportsPage.includes('if (!canGenerate || generating) return'), true);
    assert.equal(reportsPage.includes('customRangeValidationError'), true);
  });

  it('shows a loading state and blocks multiple clicks', () => {
    assert.equal(reportsPage.includes("generating ? 'Generating...' : 'Generate Report'"), true);
    assert.equal(reportsPage.includes('setGenerating(true)'), true);
    assert.equal(reportsPage.includes('setGenerating(false)'), true);
    assert.equal(reportsPage.includes('disabled={!canGenerate || generating}'), true);
    assert.equal(reportsPage.includes('if (!canGenerate || generating) return'), true);
  });

  it('triggers a download and success message on success', () => {
    assert.equal(reportsPage.includes('setExportSuccess(REPORT_EXPORT_SUCCESS)'), true);
    assert.equal(REPORT_EXPORT_SUCCESS, 'Report generated successfully.');
    assert.equal(reportsPage.includes('<SuccessBanner message={exportSuccess} />'), true);
    assert.equal(reportsApi.includes('triggerBrowserDownload(response.data, filename)'), true);
    assert.equal(reportExport.includes('URL.createObjectURL'), true);
    assert.equal(reportExport.includes('link.download = filename'), true);
    assert.equal(reportExport.includes('link.click()'), true);
  });

  it('shows a safe user-friendly error on failure', async () => {
    assert.equal(reportsPage.includes('toReportExportError'), true);
    assert.equal(reportsPage.includes('<ErrorBanner message={exportError} />'), true);
    assert.equal(
      await toReportExportError(
        axiosLikeError({
          status: 401,
          statusText: 'Unauthorized',
          message: 'Request failed with status code 401',
        }),
      ),
      REPORT_EXPORT_ERROR,
    );
    assert.equal(
      await toReportExportError(
        axiosLikeError({
          status: 500,
          message: 'Request failed with status code 500',
          detail: 'SELECT * FROM orders',
        }),
      ),
      REPORT_EXPORT_ERROR,
    );
    const network = await toReportExportError(new Error('Network Error'));
    assert.equal(network, REPORT_EXPORT_ERROR);
    assert.equal(network.includes('401'), false);
    assert.equal(network.toLowerCase().includes('unauthorized'), false);
    assert.equal(network.includes('status code'), false);
    assert.equal(
      await toReportExportError(
        axiosLikeError({ status: 422, detail: REPORT_RANGE_ERROR.startAfterEnd }),
      ),
      REPORT_RANGE_ERROR.startAfterEnd,
    );
    assert.equal(
      await toReportExportError(
        axiosLikeError({ status: 422, blobDetail: REPORT_RANGE_ERROR.startRequired }),
      ),
      REPORT_RANGE_ERROR.startRequired,
    );
  });
});

describe('export filename helpers', () => {
  it('matches backend download names for each filter', () => {
    assert.equal(salesReportDownloadName('today'), 'sales-report-today.pdf');
    assert.equal(salesReportDownloadName('7d'), 'sales-report-last-7-days.pdf');
    assert.equal(salesReportDownloadName('30d'), 'sales-report-last-30-days.pdf');
    assert.equal(
      salesReportDownloadName('custom', '2026-08-01', '2026-08-10'),
      'sales-report-2026-08-01-to-2026-08-10.pdf',
    );
  });

  it('reads filename from Content-Disposition', () => {
    assert.equal(
      filenameFromContentDisposition('attachment; filename="sales-report-today.pdf"'),
      'sales-report-today.pdf',
    );
    assert.equal(filenameFromContentDisposition(undefined), null);
  });
});

describe('Observation #13 date filtering remains unchanged', () => {
  it('keeps Today, Last 7 days, Last 30 days, and Custom Date Range', () => {
    assert.equal(reportsPage.includes('<option value="today">Today</option>'), true);
    assert.equal(reportsPage.includes('<option value="7d">Last 7 days</option>'), true);
    assert.equal(reportsPage.includes('<option value="30d">Last 30 days</option>'), true);
    assert.equal(reportsPage.includes('<option value="custom">Custom Date Range</option>'), true);
    assert.equal(reportsPage.includes('label="From"'), true);
    assert.equal(reportsPage.includes('label="To"'), true);
    assert.equal(reportDateRange.includes("period: 'custom', start_date: startDate, end_date: endDate"), true);
    assert.equal(dailySales.includes('Custom Date Range'), false);
    assert.equal(reportsPage.includes('Excel'), false);
    assert.equal(reportsPage.toLowerCase().includes('xlsx'), false);
  });
});
