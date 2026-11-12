// داشبورد ادمین — مخاطب: مدیر پلتفرم؛ اولویت: وضعیت کلی و موارد منتظر اقدام
import type { Metadata } from 'next';
import Link from 'next/link';
import { AlertCircle } from 'lucide-react';
import { getStats } from '@/lib/db';
import { getAdminOverview, getOrdersPage } from '@/lib/queries';
import { formatNumber, formatPrice } from '@/lib/utils';
import { PageHeader, StatCard } from '@/components/ui/states';
import { OrdersTable } from '@/components/panel/orders';

export const dynamic = 'force-dynamic';
export const metadata: Metadata = { title: 'داشبورد ادمین' };

export default async function AdminDashboardPage() {
  const [stats, overview, recent] = await Promise.all([
    getStats(),
    getAdminOverview(),
    getOrdersPage({ pageSize: 8 }),
  ]);

  return (
    <div>
      <PageHeader title="داشبورد" description="نمای کلی پلتفرم؛ فروش فقط از سفارش‌های پرداخت‌شده و لغونشده حساب می‌شود." />

      {(overview.awaitingReview > 0 || overview.draftShops > 0) && (
        <div className="mb-6 space-y-2" role="region" aria-label="موارد منتظر اقدام">
          {overview.awaitingReview > 0 && (
            <Link href="/admin/orders?status=pending_payment" className="flex items-center gap-3 rounded-md border border-warning bg-warning-soft p-4 text-sm font-semibold text-warning">
              <AlertCircle className="h-5 w-5 shrink-0" aria-hidden="true" />
              {formatNumber(overview.awaitingReview)} رسید پرداخت در پلتفرم منتظر بررسی است.
            </Link>
          )}
          {overview.draftShops > 0 && (
            <Link href="/admin/shops" className="flex items-center gap-3 rounded-md border border-line bg-surface p-4 text-sm font-semibold">
              <AlertCircle className="h-5 w-5 shrink-0 text-warning" aria-hidden="true" />
              {formatNumber(overview.draftShops)} فروشگاه هنوز در وضعیت پیش‌نویس است.
            </Link>
          )}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="فروش کل پلتفرم" value={formatPrice(overview.revenueTotal)} emphasis />
        <StatCard label="فروشگاه فعال" value={formatNumber(Number(stats.activeShops))} hint={`از ${formatNumber(Number(stats.totalShops))} فروشگاه`} />
        <StatCard label="سفارش پرداخت‌شده" value={formatNumber(Number(stats.paidOrders))} hint={`از ${formatNumber(Number(stats.totalOrders))} سفارش`} />
        <StatCard label="کاربران" value={formatNumber(Number(stats.totalUsers))} hint={`${formatNumber(Number(stats.totalProducts))} محصول ثبت‌شده`} />
      </div>

      <section className="mt-8" aria-labelledby="recent-h">
        <div className="mb-3 flex items-center justify-between">
          <h2 id="recent-h" className="text-lg font-bold">آخرین سفارش‌ها</h2>
          <Link href="/admin/orders" className="text-sm font-semibold text-brand underline-offset-4 hover:underline">همه‌ی سفارش‌ها</Link>
        </div>
        {recent.rows.length > 0 ? (
          <OrdersTable orders={recent.rows} basePath="/admin/orders" caption="آخرین سفارش‌های پلتفرم" />
        ) : (
          <p className="rounded-md border border-dashed border-line-strong bg-surface p-6 text-center text-sm text-ink-muted">هنوز سفارشی در پلتفرم ثبت نشده است.</p>
        )}
      </section>
    </div>
  );
}
