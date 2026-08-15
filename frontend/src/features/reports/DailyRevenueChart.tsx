import { formatINR } from '../../types/pos';
import { formatChartDate, type DailyRevenuePoint } from '../../types/reports';

export function DailyRevenueChart({ items }: { items: DailyRevenuePoint[] }) {
  const max = Math.max(...items.map((item) => item.revenue), 1);

  return (
    <div className="rounded-[10px] border border-[#E0DDD5] bg-white p-3.5">
      <div className="mb-3 text-[13px] font-semibold text-[#1A1A18]">Daily Revenue</div>
      {items.length === 0 ? (
        <p className="text-xs text-[#8A8A84]">No data</p>
      ) : (
        <div className="flex h-[90px] items-end gap-1.5">
          {items.map((item) => (
            <div key={item.date} className="flex flex-1 flex-col items-center gap-0.5">
              <div className="text-[9px] font-semibold text-[#1A7A4A]">
                {item.revenue > 0 ? formatINR(item.revenue) : ''}
              </div>
              <div
                className={`w-full rounded-t-[3px] ${item.revenue > 0 ? 'bg-[#1A7A4A]' : 'bg-[#E6F4EC]'}`}
                style={{ height: `${Math.max(3, (item.revenue / max) * 72)}px` }}
              />
              <div className="text-center text-[8px] text-[#8A8A84]">{formatChartDate(item.date)}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
