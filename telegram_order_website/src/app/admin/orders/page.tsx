import type { Metadata } from 'next';
import { ShoppingCart } from 'lucide-react';
import { parsePage } from '@/lib/panel';
import { getOrdersPage } from '@/lib/queries';
import { formatNumber, ORDER_STATUSES } from '@/lib/utils';
import { EmptyState, PageHeader } from '@/components/ui/states';
import { OrdersTable, Pagination, StatusFilter } from '@/components/panel/orders';

export const dynamic = 'force-dynamic';
export const metadata: Metadata = { title: 'سفارش‌ها' };

export default async function AdminOrdersPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string; page?: string }>;
}) {
  const sp = await searchParams;
  const status = ORDER_STATUSES.find((s) => s === sp.status);
  const data = await getOrdersPage({ status, page: parsePage(sp.page) });

  return (
    <div>
      <PageHeader title="سفارش‌ها" description={`${formatNumber(data.total)} سفارش در همه‌ی فروشگاه‌ها`} />
      <StatusFilter basePath="/admin/orders" current={status} />
      {data.rows.length > 0 ? (
        <>
          <OrdersTable orders={data.rows} basePath="/admin/orders" caption="فهرست سفارش‌های پلتفرم" />
          <Pagination basePath="/admin/orders" page={data.page} pageCount={data.pageCount} params={{ status }} />
        </>
      ) : (
        <EmptyState icon={ShoppingCart} title={status ? 'سفارشی با این وضعیت نیست' : 'هنوز سفارشی ثبت نشده'} description={status ? 'فیلتر دیگری را انتخاب کن.' : undefined} />
      )}
    </div>
  );
}
