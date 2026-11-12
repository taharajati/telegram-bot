// داشبورد فروشنده — مخاطب: صاحب فروشگاه؛ اولویت: «امروز چه کاری منتظر من است؟»
import type { Metadata } from 'next';
import Link from 'next/link';
import { AlertCircle, ShoppingCart } from 'lucide-react';
import { getSellerContext } from '@/lib/panel';
import { getOrdersPage, getSellerOverview, getShopSubscription } from '@/lib/queries';
import { formatDate, formatNumber, formatPrice } from '@/lib/utils';
import { Card, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { EmptyState, PageHeader, StatCard } from '@/components/ui/states';
import { BarChart } from '@/components/panel/bar-chart';
import { OrdersTable } from '@/components/panel/orders';
import { buttonStyles } from '@/components/ui/button';

export const dynamic = 'force-dynamic';
export const metadata: Metadata = { title: 'داشبورد فروشنده' };

export default async function SellerDashboardPage() {
  const { shop } = await getSellerContext();
  const [o, recent, sub] = await Promise.all([
    getSellerOverview(shop.id),
    getOrdersPage({ shopId: shop.id, pageSize: 5 }),
    getShopSubscription(shop.id).catch(() => null),
  ]);

  const subActive = sub && sub.approval_status === 'approved' && new Date(sub.end_date) > new Date();

  return (
    <div>
      <PageHeader title="داشبورد" description={`فروشگاه «${shop.name}» — فروش فقط از سفارش‌های پرداخت‌شده و لغونشده حساب می‌شود.`} />

      {(o.awaitingReview > 0 || o.lowStock > 0) && (
        <div className="mb-6 space-y-2" role="region" aria-label="کارهای منتظر اقدام">
          {o.awaitingReview > 0 && (
            <Link href="/seller/orders?status=pending_payment" className="flex items-center gap-3 rounded-md border border-warning bg-warning-soft p-4 text-sm font-semibold text-warning">
              <AlertCircle className="h-5 w-5 shrink-0" aria-hidden="true" />
              {formatNumber(o.awaitingReview)} رسید پرداخت منتظر بررسی توست. تأیید یا رد از ربات انجام می‌شود.
            </Link>
          )}
          {o.lowStock > 0 && (
            <Link href="/seller/products" className="flex items-center gap-3 rounded-md border border-line bg-surface p-4 text-sm font-semibold text-ink">
              <AlertCircle className="h-5 w-5 shrink-0 text-warning" aria-hidden="true" />
              موجودی {formatNumber(o.lowStock)} محصول فعال کمتر از ۵ عدد است.
            </Link>
          )}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="فروش امروز" value={formatPrice(o.revenueToday)} emphasis />
        <StatCard label="فروش ۷ روز گذشته" value={formatPrice(o.revenue7d)} />
        <StatCard label="سفارش آماده‌ی ارسال" value={formatNumber(o.toShip)} hint="پرداخت‌شده یا تأییدشده" />
        <StatCard label="در انتظار پرداخت" value={formatNumber(o.awaitingPayment)} />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[2fr_1fr]">
        <Card as="section">
          <CardTitle>فروش ۷ روز گذشته</CardTitle>
          <div className="mt-4"><BarChart data={o.chart} caption="فروش پرداخت‌شده‌ی روزانه در هفت روز گذشته" /></div>
        </Card>

        <Card as="section">
          <CardTitle>اشتراک فروشگاه</CardTitle>
          {sub ? (
            <div className="mt-3 space-y-2 text-sm">
              <Badge tone={subActive ? 'success' : sub.approval_status === 'pending' ? 'warning' : 'danger'}>
                {subActive ? 'فعال' : sub.approval_status === 'pending' ? 'در انتظار تأیید ادمین' : 'منقضی یا ردشده'}
              </Badge>
              <p className="text-ink-muted">
                {sub.is_trial ? 'دوره‌ی آزمایشی' : `پلن ${sub.plan_name ?? '—'}`}
                {' · '}پایان: <span className="tabular-nums">{formatDate(sub.end_date)}</span>
              </p>
              {!subActive && <p className="text-xs text-ink-subtle">برای تمدید، در ربات از بخش اشتراک اقدام کن.</p>}
            </div>
          ) : (
            <p className="mt-3 text-sm text-ink-muted">اشتراکی برای این فروشگاه ثبت نشده است.</p>
          )}
        </Card>
      </div>

      <section className="mt-8" aria-labelledby="recent-h">
        <div className="mb-3 flex items-center justify-between">
          <h2 id="recent-h" className="text-lg font-bold">آخرین سفارش‌ها</h2>
          <Link href="/seller/orders" className="text-sm font-semibold text-brand underline-offset-4 hover:underline">همه‌ی سفارش‌ها</Link>
        </div>
        {recent.rows.length > 0 ? (
          <OrdersTable orders={recent.rows} basePath="/seller/orders" caption="آخرین سفارش‌های فروشگاه" />
        ) : (
          <EmptyState
            icon={ShoppingCart}
            title="هنوز سفارشی ثبت نشده"
            description="لینک فروشگاه را در کانال یا بیو بگذار؛ سفارش‌ها همین‌جا و در ربات نمایش داده می‌شوند."
            action={<Link href={`/shop/${shop.id}`} className={buttonStyles({ variant: 'secondary' })}>مشاهده‌ی صفحه‌ی فروشگاه</Link>}
          />
        )}
      </section>
    </div>
  );
}
