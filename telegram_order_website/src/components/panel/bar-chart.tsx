import { formatNumber, formatPrice, formatShortDate } from '@/lib/utils';

/** نمودار ستونی هفت‌روزه؛ جدول مخفی برای صفحه‌خوان. ارتفاع‌ها داده‌محورند. */
export function BarChart({ data, caption }: { data: { day: string; revenue: number; orders: number }[]; caption: string }) {
  const max = Math.max(...data.map((d) => d.revenue), 0);
  const empty = max === 0;

  return (
    <figure>
      <div aria-hidden="true" className="flex h-48 items-end gap-2 border-b border-line-strong pb-px">
        {data.map((d) => {
          const h = empty ? 0 : Math.max(4, Math.round((d.revenue / max) * 100));
          return (
            <div key={d.day} className="flex h-full flex-1 flex-col items-center justify-end gap-1">
              <span className="text-[11px] tabular-nums text-ink-subtle">{d.revenue > 0 ? formatNumber(d.revenue) : ''}</span>
              <div className="w-full max-w-10 rounded-t-sm bg-brand" style={{ height: `${h}%` }} title={`${formatShortDate(d.day)}: ${formatPrice(d.revenue)}`} />
            </div>
          );
        })}
      </div>
      <div aria-hidden="true" className="mt-2 flex gap-2">
        {data.map((d) => (
          <span key={d.day} className="flex-1 text-center text-xs text-ink-subtle">{formatShortDate(d.day)}</span>
        ))}
      </div>
      {empty && <p className="mt-3 text-sm text-ink-muted">در این بازه هنوز فروش پرداخت‌شده‌ای ثبت نشده است.</p>}
      <figcaption className="sr-only">{caption}</figcaption>
      <table className="sr-only">
        <caption>{caption}</caption>
        <thead><tr><th>روز</th><th>فروش</th><th>تعداد سفارش</th></tr></thead>
        <tbody>
          {data.map((d) => (
            <tr key={d.day}><td>{formatShortDate(d.day)}</td><td>{formatPrice(d.revenue)}</td><td>{formatNumber(d.orders)}</td></tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
