import type { Metadata } from 'next';
import { getSellerContext } from '@/lib/panel';
import { getSellerOverview } from '@/lib/queries';
import { formatNumber, formatPrice } from '@/lib/utils';
import { Card, CardTitle } from '@/components/ui/card';
import { EmptyState, PageHeader, StatCard } from '@/components/ui/states';
import { Table, Td, Th, Truncate } from '@/components/ui/table';
import { BarChart } from '@/components/panel/bar-chart';
import { BarChart3 } from 'lucide-react';

export const dynamic = 'force-dynamic';
export const metadata: Metadata = { title: 'آمار فروش' };

export default async function SellerStatsPage() {
  const { shop } = await getSellerContext();
  const o = await getSellerOverview(shop.id);

  return (
    <div>
      <PageHeader title="آمار فروش" description="فقط سفارش‌های پرداخت‌شده و لغونشده حساب می‌شوند. روزها به وقت تهران‌اند." />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="فروش ۳۰ روز گذشته" value={formatPrice(o.revenue30d)} emphasis />
        <StatCard label="فروش کل" value={formatPrice(o.revenueTotal)} />
        <StatCard label="سفارش پرداخت‌شده" value={formatNumber(o.paidOrders)} hint={`از ${formatNumber(o.totalOrders)} سفارش`} />
        <StatCard label="محصولات" value={formatNumber(o.products)} />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card as="section">
          <CardTitle>فروش ۷ روز گذشته</CardTitle>
          <div className="mt-4"><BarChart data={o.chart} caption="فروش پرداخت‌شده‌ی روزانه در هفت روز گذشته" /></div>
        </Card>
        <section aria-labelledby="top-h">
          <h2 id="top-h" className="mb-3 text-base font-bold">پرفروش‌ترین محصولات</h2>
          {o.topProducts.length > 0 ? (
            <Table caption="پرفروش‌ترین محصولات">
              <thead><tr><Th>محصول</Th><Th>تعداد فروش</Th><Th>درآمد</Th></tr></thead>
              <tbody>
                {o.topProducts.map((t) => (
                  <tr key={t.name}>
                    <Td><Truncate max="max-w-48">{t.name}</Truncate></Td>
                    <Td className="tabular-nums">{formatNumber(t.sold)}</Td>
                    <Td className="tabular-nums">{formatPrice(t.revenue)}</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          ) : (
            <EmptyState icon={BarChart3} title="هنوز فروشی ثبت نشده" description="بعد از اولین سفارش پرداخت‌شده، محصولات پرفروش اینجا نمایش داده می‌شوند." />
          )}
        </section>
      </div>
    </div>
  );
}
