import type { Metadata } from 'next';
import Link from 'next/link';
import { Store } from 'lucide-react';
import { getAdminShops } from '@/lib/queries';
import { formatDate, formatNumber } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { EmptyState, PageHeader } from '@/components/ui/states';
import { Table, Td, Th, Truncate } from '@/components/ui/table';

export const dynamic = 'force-dynamic';
export const metadata: Metadata = { title: 'فروشگاه‌ها' };

export default async function AdminShopsPage() {
  const shops = await getAdminShops();
  const now = new Date();

  return (
    <div>
      <PageHeader title="فروشگاه‌ها" description={`${formatNumber(shops.length)} فروشگاه ثبت‌شده`} />
      {shops.length > 0 ? (
        <Table caption="فروشگاه‌های پلتفرم">
          <thead>
            <tr><Th>فروشگاه</Th><Th>مالک</Th><Th>محصولات</Th><Th>سفارش‌ها</Th><Th>اشتراک</Th><Th>وضعیت</Th><Th>تاریخ ثبت</Th></tr>
          </thead>
          <tbody>
            {shops.map((s) => {
              const subLive = s.sub_end && new Date(s.sub_end) > now;
              return (
                <tr key={s.id} className="hover:bg-canvas">
                  <Td className="font-semibold">
                    <Link href={`/shop/${s.id}`} className="underline-offset-4 hover:underline">
                      <Truncate max="max-w-48">{s.name}</Truncate>
                    </Link>
                  </Td>
                  <Td className="text-ink-muted" dir="ltr">{s.owner_username ? <bdi>@{s.owner_username}</bdi> : '—'}</Td>
                  <Td className="tabular-nums">{formatNumber(s.product_count)}</Td>
                  <Td className="tabular-nums">{formatNumber(s.order_count)}</Td>
                  <Td className="whitespace-nowrap tabular-nums">
                    {s.sub_end ? (
                      <>
                        <Badge tone={subLive ? 'success' : 'danger'}>{subLive ? (s.sub_trial ? 'آزمایشی' : 'فعال') : 'منقضی'}</Badge>
                        <span className="ms-2 text-xs text-ink-subtle">{formatDate(s.sub_end)}</span>
                      </>
                    ) : '—'}
                  </Td>
                  <Td>
                    <Badge tone={s.status === 'draft' ? 'warning' : s.is_active ? 'success' : 'danger'}>
                      {s.status === 'draft' ? 'پیش‌نویس' : s.is_active ? 'فعال' : 'غیرفعال'}
                    </Badge>
                  </Td>
                  <Td className="whitespace-nowrap text-ink-muted tabular-nums">{formatDate(s.created_at)}</Td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      ) : (
        <EmptyState icon={Store} title="هنوز فروشگاهی ثبت نشده" description="فروشگاه‌ها از ربات تلگرام و با دعوت‌نامه ساخته می‌شوند." />
      )}
    </div>
  );
}
