// ─── Admin: Order Detail ───
import { notFound } from 'next/navigation';
import Link from 'next/link';
import { ArrowRight, ShoppingCart } from 'lucide-react';
import { getOrderById, getOrderItems } from '@/lib/db';
import { formatPrice, toJalali, getStatusLabel } from '@/lib/utils';

export const dynamic = 'force-dynamic';

export default async function AdminOrderDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const order = await getOrderById(parseInt(id));
  if (!order) notFound();

  const items = await getOrderItems(order.id);
  const history = JSON.parse(order.status_history || '[]');
  const orderStatuses = ['pending_payment', 'pending', 'paid', 'confirmed', 'shipped', 'delivered', 'cancelled', 'refunded'];

  return (
    <div>
      <Link
        href="/admin/orders"
        className="mb-4 inline-flex items-center gap-1 text-sm font-semibold text-[var(--primary)] hover:underline"
      >
        <ArrowRight className="h-4 w-4" />
        بازگشت به سفارش‌ها
      </Link>

      <h1 className="mb-6 text-2xl font-black">سفارش #{order.tracking_code}</h1>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Details */}
        <div className="rounded-[var(--radius-xl)] border border-[var(--border-light)] bg-white p-6 shadow-[var(--shadow-card)]">
          <h2 className="mb-4 text-lg font-bold">اطلاعات سفارش</h2>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between border-b border-[var(--border-light)] pb-2">
              <span className="text-[var(--text-tertiary)]">وضعیت</span>
              <span className="inline-flex rounded-full border border-current px-2.5 py-0.5 text-xs font-medium text-[var(--text-secondary)]">
                {getStatusLabel(order.status)}
              </span>
            </div>
            <div className="flex justify-between border-b border-[var(--border-light)] pb-2">
              <span className="text-[var(--text-tertiary)]">مبلغ کل</span>
              <span className="font-bold text-[var(--primary)]">{formatPrice(order.total_price)}</span>
            </div>
            <div className="flex justify-between border-b border-[var(--border-light)] pb-2">
              <span className="text-[var(--text-tertiary)]">روش پرداخت</span>
              <span>{order.payment_method === 'online' ? '💳 آنلاین' : '🚚 درب منزل'}</span>
            </div>
            <div className="flex justify-between border-b border-[var(--border-light)] pb-2">
              <span className="text-[var(--text-tertiary)]">وضعیت پرداخت</span>
              <span className={order.payment_status === 'paid' ? 'text-[var(--success)]' : 'text-amber-500'}>
                {order.payment_status === 'paid' ? 'پرداخت شده' : 'در انتظار پرداخت'}
              </span>
            </div>
            {order.payment_ref && (
              <div className="flex justify-between border-b border-[var(--border-light)] pb-2">
                <span className="text-[var(--text-tertiary)]">شماره پیگیری</span>
                <span className="text-[var(--success)]">{order.payment_ref}</span>
              </div>
            )}
            <div className="flex justify-between border-b border-[var(--border-light)] pb-2">
              <span className="text-[var(--text-tertiary)]">گیرنده</span>
              <span>{order.receiver_name || '—'}</span>
            </div>
            <div className="flex justify-between border-b border-[var(--border-light)] pb-2">
              <span className="text-[var(--text-tertiary)]">شماره تماس</span>
              <span dir="ltr">{order.phone}</span>
            </div>
            <div className="flex justify-between border-b border-[var(--border-light)] pb-2">
              <span className="text-[var(--text-tertiary)]">آدرس</span>
              <span className="max-w-[250px] text-left">{order.shipping_address}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[var(--text-tertiary)]">تاریخ ثبت</span>
              <span>{toJalali(order.created_at)}</span>
            </div>
          </div>

          {/* Items */}
          <h3 className="mb-3 mt-6 text-sm font-semibold text-[var(--text-tertiary)]">اقلام سفارش</h3>
          <div className="space-y-2">
            {items.map((item) => (
              <div key={item.id} className="flex justify-between rounded-[var(--radius)] bg-[var(--bg-muted)] px-3 py-2 text-sm">
                <span className="text-[var(--text-secondary)]">{item.product_name} × {item.quantity}</span>
                <span className="font-bold text-[var(--primary)]">{formatPrice(item.unit_price * item.quantity)}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Status Controls */}
        <div className="rounded-[var(--radius-xl)] border border-[var(--border-light)] bg-white p-6 shadow-[var(--shadow-card)]">
          <h2 className="mb-4 text-lg font-bold">تغییر وضعیت</h2>

          <form action={`/api/admin/orders/${order.id}/status`} method="POST" className="space-y-3">
            <select
              name="status"
              className="w-full rounded-[var(--radius)] border border-[var(--border)] bg-white px-4 py-3 text-sm outline-none transition focus:border-[var(--primary)]"
              defaultValue={order.status}
            >
              {orderStatuses.map((s) => (
                <option key={s} value={s}>{getStatusLabel(s)}</option>
              ))}
            </select>
            <button
              type="submit"
              className="w-full rounded-[var(--radius-lg)] bg-[var(--primary)] py-3 font-semibold text-white transition-all hover:bg-[var(--primary-dark)] active:scale-[0.97]"
            >
              بروزرسانی وضعیت
            </button>
          </form>

          {/* History */}
          {history.length > 0 && (
            <div className="mt-6">
              <h3 className="mb-3 text-sm font-semibold text-[var(--text-tertiary)]">تاریخچه وضعیت</h3>
              <div className="space-y-2">
                {history.map((entry: any, idx: number) => (
                  <div key={idx} className="flex items-center gap-2 text-xs text-[var(--text-tertiary)]">
                    <span className="h-1.5 w-1.5 rounded-full bg-[var(--primary)]" />
                    <span>{new Date(entry.at).toLocaleString('fa-IR')}</span>
                    <span className="text-[var(--border)]">—</span>
                    <span>{entry.status}</span>
                    <span className="text-[var(--text-tertiary)]">({entry.by})</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}