// ─── Seller: Orders ───
import Link from 'next/link';
import { ShoppingCart } from 'lucide-react';
import { getShopOwner, getOrdersByShop } from '@/lib/db';
import { requireSeller } from '@/lib/auth';
import { redirect } from 'next/navigation';
import { formatPrice, toJalali, getStatusLabel } from '@/lib/utils';

export const dynamic = 'force-dynamic';

export default async function SellerOrdersPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string }>;
}) {
  const { status } = await searchParams;
  const session = await requireSeller().catch(() => redirect('/login'));
  const owner = await getShopOwner(session.userId);
  if (!owner) redirect('/login');

  let orders = await getOrdersByShop(owner.shop_id);
  if (status) orders = orders.filter((o) => o.status === status);

  const statuses = ['pending_payment', 'pending', 'paid', 'confirmed', 'shipped', 'delivered', 'cancelled', 'refunded'];

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-black">سفارش‌ها</h1>
        <div className="flex flex-wrap gap-1.5">
          <Link
            href="/seller/orders"
            className={`rounded-[var(--radius)] px-3 py-1.5 text-xs font-medium transition ${
              !status ? 'bg-[var(--primary)] text-white' : 'border border-[var(--border-light)] bg-white text-[var(--text-secondary)] hover:border-[var(--primary)]'
            }`}
          >
            همه
          </Link>
          {statuses.map((s) => (
            <Link
              key={s}
              href={`/seller/orders?status=${s}`}
              className={`rounded-[var(--radius)] px-3 py-1.5 text-xs font-medium transition ${
                status === s ? 'bg-[var(--primary)] text-white' : 'border border-[var(--border-light)] bg-white text-[var(--text-secondary)] hover:border-[var(--primary)]'
              }`}
            >
              {getStatusLabel(s)}
            </Link>
          ))}
        </div>
      </div>

      <div className="overflow-x-auto rounded-[var(--radius-xl)] border border-[var(--border-light)] bg-white shadow-[var(--shadow-card)]">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--border-light)]">
              <th className="px-4 py-3 text-right font-semibold text-[var(--text-tertiary)]">کد</th>
              <th className="px-4 py-3 text-right font-semibold text-[var(--text-tertiary)]">مبلغ</th>
              <th className="px-4 py-3 text-right font-semibold text-[var(--text-tertiary)]">وضعیت</th>
              <th className="px-4 py-3 text-right font-semibold text-[var(--text-tertiary)]">پرداخت</th>
              <th className="px-4 py-3 text-right font-semibold text-[var(--text-tertiary)]">گیرنده</th>
              <th className="px-4 py-3 text-right font-semibold text-[var(--text-tertiary)]">تاریخ</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {orders.map((order) => (
              <tr key={order.id} className="border-b border-[var(--border-light)]/50 transition hover:bg-[var(--bg-muted)]">
                <td className="px-4 py-3 font-mono text-xs font-semibold">#{order.tracking_code}</td>
                <td className="px-4 py-3 font-bold text-[var(--primary)]">{formatPrice(order.total_price)}</td>
                <td className="px-4 py-3">
                  <span className="inline-flex rounded-full border border-current px-2.5 py-0.5 text-xs font-medium text-[var(--text-secondary)]">
                    {getStatusLabel(order.status)}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className={`text-xs font-medium ${order.payment_status === 'paid' ? 'text-[var(--success)]' : 'text-amber-500'}`}>
                    {order.payment_status === 'paid' ? 'پرداخت شده' : 'در انتظار'}
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
    </div>
  );
}