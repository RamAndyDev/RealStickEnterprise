import type { ReportPeriod } from '../../types/reports';

export const REPORT_RANGE_ERROR = {
  startRequired: 'Start date is required.',
  endRequired: 'End date is required.',
  startAfterEnd: 'Start date cannot be after end date.',
} as const;

export type ReportRequestParams = {
  period: ReportPeriod;
  start_date?: string;
  end_date?: string;
};

export function validateCustomReportRange(startDate: string, endDate: string): string | null {
  if (!startDate) return REPORT_RANGE_ERROR.startRequired;
  if (!endDate) return REPORT_RANGE_ERROR.endRequired;
  if (startDate > endDate) return REPORT_RANGE_ERROR.startAfterEnd;
  return null;
}

export function customRangeValidationError(
  period: ReportPeriod,
  startDate: string,
  endDate: string,
): string | null {
  if (period !== 'custom') return null;
  return validateCustomReportRange(startDate, endDate);
}

export function shouldFetchReports(period: ReportPeriod, startDate: string, endDate: string): boolean {
  return customRangeValidationError(period, startDate, endDate) === null;
}

export function reportRequestParams(
  period: ReportPeriod,
  startDate: string,
  endDate: string,
): ReportRequestParams {
  if (period !== 'custom') {
    return { period };
  }
  return { period: 'custom', start_date: startDate, end_date: endDate };
}
