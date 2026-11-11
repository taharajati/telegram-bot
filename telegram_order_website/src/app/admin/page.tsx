// ─── Admin Dashboard — clean, data-dense, stat cards + orders table ───
import Link from 'next/link';
import { LayoutDashboard, Store, Package, ShoppingCart, Users, ArrowLeft } from 'lucide-react';
import { getStats, getAllOrders } from '@/lib/db';
import { formatPrice, toJalali, getStatusLabel } from '@/lib/utils';
import Card from '@/components/shared/Card';

export const dynamic = 'force-dynamic';

export default async function AdminDashboardPage() {
  const stats = await getStats();
  const allOrders = await getAllOrders();
  const orders = allOrders.slice(0, 10);

  const statCards = [
    { icon: Store, value: stats.totalShops, sub: `فروشگاه (${stats.activeShops} فعال)`, color: 'text-[var(--primary)]' },
    { icon: Package, value: stats.totalProducts, sub: 'محصولات', color: 'text-blue-500' },
    { icon: ShoppingCart, value: stats.totalOrders, sub: 'کل سفارش‌ها', color: 'text-[var(--success)]' },
    { icon: ShoppingCart, value: stats.pendingOrders, sub: 'در انتظار بررسی', color: 'text-amber-500' },
    { icon: ShoppingCart, value: stats.paidOrders, sub: 'پرداخت شده', color: 'text-[var(--success)]' },
    { icon: Users, value: stats.totalUsers, sub: 'کاربران', color: 'text-[var(--secondary)]' },
  ];

  return (
    <div>
      {/* header */}
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-black">داشبورد</h1>
        <span className="text-xs text-[var(--text-tertiary)]">پنل مدیریت</span>
      </div>

      {/* stat cards */}
      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {statCards.map((s, i) => (
          <Card key={i}>
            <div className="flex items-center gap-3">
              <s.icon className={`h-7 w-7 ${s.color}`} />
              <div className="min-w-0">
                <p className="truncate text-2xl font-black">{s.value}</p>
                <p className="truncate text-xs text-[var(--text-tertiary)]">{s.sub}</p>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* recent orders */}
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-bold">آخرین سفارش‌ها</h2>
        <Link
          href="/admin/orders"
          className="inline-flex items-center gap-1 text-sm font-semibold text-[var(--primary)] transition hover:gap-1.5"
        >
          مشاهده همه
          <ArrowLeft className="h-3.5 w-3.5" />
        </Link>
      </div>

      {orders.length > 0 ? (
        <div className="overflow-x-auto rounded-[var(--radius-xl)] border border-[var(--border-light)] bg-white shadow-[var(--shadow-card)]">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border-light)]">
                <th className="px-4 py-3 text-right font-semibold text-[var(--text-tertiary)]">کد</th>
                <th className="px-4 py-3 text-right font-semibold text-[var(--text-tertiary)]">مبلغ</th>
                <th className="px-4 py-3 text-right font-semibold text-[var(--text-tertiary)]">وضعیت</th>
                <th className="px-4 py-3 text-right font-semibold text-[var(--text-tertiary)]">گیرنده</th>
                <th className="px-4 py-3 text-right font-semibold text-[var(--text-tertiary)]">تاریخ</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {orders.map(order => (
                <tr key={order.id} className="border-b border-[var(--border-light)]/50 transition hover:bg-[var(--bg-muted)]">
                  <td className="px-4 py-3 font-mono text-xs font-semibold">#{order.tracking_code}</td>
                  <td className="px-4 py-3 font-bold text-[var(--primary)]">{formatPrice(order.total_price)}</td>
                  <td className="px-4 py-3">
                    <span className="inline-flex rounded-full border border-current px-2.5 py-0.5 text-xs font-medium text-[var(--text-secondary)]">
                      {getStatusLabel(order.status)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-[var(--text-secondary)]">{order.receiver_name || '—'}</td>
                  <td className="px-4 py-3 text-[var(--text-tertiary)]">{toJalali(order.created_at)}</td>
                  <td className="px-4 py-3">
                    <Link
                      href={`/admin/orders/${order.id}`}
                      className="text-sm font-semibold text-[var(--primary)] transition hover:underline"
                    >
                      جزئیات
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <Card>
          <p className="py-8 text-center text-[var(--text-tertiary)]">هیچ سفارشی ثبت نشده است.</p>
        </Card>
      )}
    </div>
  );
}
