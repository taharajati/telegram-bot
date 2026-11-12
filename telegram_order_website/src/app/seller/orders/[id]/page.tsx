import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { ArrowRight } from 'lucide-react';
import { getSellerContext } from '@/lib/panel';
import { getOrderById, getOrderItems } from '@/lib/db';
import { getOrderHistoryEntries } from '@/lib/queries';
import { OrderDetailView } from '@/components/panel/orders';

export const dynamic = 'force-dynamic';
export const metadata: Metadata = { title: 'جزئیات سفارش' };

export default async function SellerOrderDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const orderId = parseInt(id);
  if (!Number.isInteger(orderId)) notFound();
  const { shop } = await getSellerContext();

  const order = await getOrderById(orderId);
  if (!order || order.shop_id !== shop.id) notFound();

  const [items, history] = await Promise.all([
    getOrderItems(order.id),
    getOrderHistoryEntries(order.id, order.status_history),
  ]);

  return (
    <div>
      <Link href="/seller/orders" className="mb-3 inline-flex items-center gap-1 text-sm font-semibold text-brand underline-offset-4 hover:underline">
        <ArrowRight className="h-4 w-4" aria-hidden="true" />
        بازگشت به سفارش‌ها
      </Link>
      <h1 className="mb-6 text-2xl font-extrabold">
        سفارش <bdi dir="ltr" className="font-mono">{order.tracking_code}</bdi>
      </h1>
      <OrderDetailView order={order} items={items} history={history} statusAction={`/api/seller/orders/${order.id}/status`} />
    </div>
  );
}
