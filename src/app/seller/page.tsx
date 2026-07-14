// ─── Seller Dashboard ───
import { Package, ShoppingCart, Store } from 'lucide-react';
import { getShopOwner, getShopById, getShopStats, getOrdersByShop } from '@/lib/db';
import { requireSeller } from '@/lib/auth';
import { redirect } from 'next/navigation';
import { formatPrice, toJalali, getStatusLabel } from '@/lib/utils';
import Card from '@/components/shared/Card';
import Link from 'next/link';

export const dynamic = 'force-dynamic';

export default async function SellerDashboardPage() {
  const session = await requireSeller().catch(() => redirect('/login'));
  const owner = await getShopOwner(session.userId);
  if (!owner) redirect('/login');

  const shop = await getShopById(owner.shop_id);
  const stats = await getShopStats(owner.shop_id);
  const orders = (await getOrdersByShop(owner.shop_id)).slice(0, 10);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-black">داشبورد فروشنده</h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">فروشگاه: {shop?.name || '—'}</p>
      </div>

      <div className="mb-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <Card>
          <div className="flex items-center gap-3">
            <Package className="h-7 w-7 text-blue-500" />
            <div>
              <p className="text-2xl font-black">{stats.totalProducts}</p>
              <p className="text-xs text-[var(--text-tertiary)]">محصولات</p>
            </div>
          </div>
        </Card>
        <Card>
          <div className="flex items-center gap-3">
            <ShoppingCart className="h-7 w-7 text-[var(--success)]" />
            <div>
              <p className="text-2xl font-black">{stats.totalOrders}</p>
              <p className="text-xs text-[var(--text-tertiary)]">کل سفارش‌ها</p>
            </div>
          </div>
        </Card>
        <Card>
          <div className="flex items-center gap-3">
            <ShoppingCart className="h-7 w-7 text-amber-500" />
            <div>
              <p className="text-2xl font-black">{stats.pendingOrders}</p>
              <p className="text-xs text-[var(--text-tertiary)]">در انتظار بررسی</p>
            </div>
          </div>
        </Card>
        <Card>
          <div className="flex items-center gap-3">
            <ShoppingCart className="h-7 w-7 text-[var(--success)]" />
            <div>
              <p className="text-2xl font-black">{stats.paidOrders}</p>
              <p className="text-xs text-[var(--text-tertiary)]">پرداخت شده</p>
            </div>
          </div>
        </Card>
        <Card>
          <div className="flex items-center gap-3">
            <ShoppingCart className="h-7 w-7 text-[var(--primary)]" />
            <div>
              <p className="text-2xl font-black text-[var(--primary)]">{formatPrice(stats.totalRevenue)}</p>
              <p className="text-xs text-[var(--text-tertiary)]">مجموع فروش</p>
            </div>
          </div>
        </Card>
      </div>

      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-bold">آخرین سفارش‌ها</h2>
        <Link href="/seller/orders" className="inline-flex items-center gap-1 text-sm font-semibold text-[var(--primary)] hover:underline">
          مشاهده همه
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
              {orders.map((order: any) => (
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
                    <Link href={`/seller/orders/${order.id}`} className="text-sm font-semibold text-[var(--primary)] hover:underline">جزئیات</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <Card><p className="py-8 text-center text-[var(--text-tertiary)]">هیچ سفارشی ثبت نشده است.</p></Card>
      )}
    </div>
  );
}
