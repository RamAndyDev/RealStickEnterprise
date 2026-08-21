import type { ReportPeriod } from '../../types/reports';

export const REPORT_EXPORT_SUCCESS = 'Report generated successfully.';
export const REPORT_EXPORT_ERROR = 'Unable to generate report.';

const SAFE_DETAILS = new Set([
  'Start date is required.',
  'End date is required.',
  'Start date cannot be after end date.',
]);

export function salesReportDownloadName(
  period: ReportPeriod,
  startDate = '',
  endDate = '',
): string {
  if (period === 'today') return 'sales-report-today.pdf';
  if (period === '7d') return 'sales-report-last-7-days.pdf';
  if (period === '30d') return 'sales-report-last-30-days.pdf';
  if (period === 'custom' && startDate && endDate) {
    return `sales-report-${startDate}-to-${endDate}.pdf`;
  }
  return 'sales-report.pdf';
}

export function filenameFromContentDisposition(header: string | undefined | null): string | null {
  if (!header) return null;
  const utf = /filename\*=UTF-8''([^;]+)/i.exec(header);
  if (utf?.[1]) {
    try {
      return decodeURIComponent(utf[1].trim().replace(/^["']|["']$/g, ''));
    } catch {
      return utf[1].trim();
    }
  }
  const quoted = /filename="([^"]+)"/i.exec(header);
  if (quoted?.[1]) return quoted[1];
  const plain = /filename=([^;]+)/i.exec(header);
  return plain?.[1]?.trim().replace(/^["']|["']$/g, '') ?? null;
}

export function triggerBrowserDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.rel = 'noopener';
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (value && typeof value === 'object') return value as Record<string, unknown>;
  return null;
}

function responseData(error: unknown): unknown {
  const response = asRecord(error)?.response;
  if (!response || typeof response !== 'object') return undefined;
  return (response as { data?: unknown }).data;
}

function detailFromJson(data: unknown): string | null {
  const record = asRecord(data);
  const detail = record?.detail;
  return typeof detail === 'string' ? detail : null;
}

export async function toReportExportError(error: unknown): Promise<string> {
  const data = responseData(error);
  let detail = detailFromJson(data);
  if (!detail && typeof Blob !== 'undefined' && data instanceof Blob) {
    try {
      detail = detailFromJson(JSON.parse(await data.text()));
    } catch {
      detail = null;
    }
  }
  if (detail && SAFE_DETAILS.has(detail)) return detail;
  return REPORT_EXPORT_ERROR;
}
