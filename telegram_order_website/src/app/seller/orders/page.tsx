import type { Metadata } from 'next';
import { ShoppingCart } from 'lucide-react';
import { getSellerContext, parsePage } from '@/lib/panel';
import { getOrdersPage } from '@/lib/queries';
import { formatNumber, ORDER_STATUSES } from '@/lib/utils';
import { EmptyState, PageHeader } from '@/components/ui/states';
import { OrdersTable, Pagination, StatusFilter } from '@/components/panel/orders';

export const dynamic = 'force-dynamic';
export const metadata: Metadata = { title: 'سفارش‌ها' };

export default async function SellerOrdersPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string; page?: string }>;
}) {
  const sp = await searchParams;
  const { shop } = await getSellerContext();
  const status = ORDER_STATUSES.find((s) => s === sp.status);
  const data = await getOrdersPage({ shopId: shop.id, status, page: parsePage(sp.page) });

  return (
    <div>
      <PageHeader title="سفارش‌ها" description={`${formatNumber(data.total)} سفارش${status ? ' با این وضعیت' : ''}`} />
      <StatusFilter basePath="/seller/orders" current={status} />
      {data.rows.length > 0 ? (
        <>
          <OrdersTable orders={data.rows} basePath="/seller/orders" caption="فهرست سفارش‌های فروشگاه" />
          <Pagination basePath="/seller/orders" page={data.page} pageCount={data.pageCount} params={{ status }} />
        </>
      ) : (
        <EmptyState
          icon={ShoppingCart}
          title={status ? 'سفارشی با این وضعیت نیست' : 'هنوز سفارشی ثبت نشده'}
          description={status ? 'فیلتر دیگری را انتخاب کن.' : 'وقتی مشتری از ربات سفارش بدهد، اینجا نمایش داده می‌شود.'}
        />
      )}
    </div>
  );
}
