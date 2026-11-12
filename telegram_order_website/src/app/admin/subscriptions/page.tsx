import type { Metadata } from 'next';
import { CreditCard } from 'lucide-react';
import { getAdminSubscriptions } from '@/lib/queries';
import { formatDate, formatPrice } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { EmptyState, PageHeader } from '@/components/ui/states';
import { Table, Td, Th, Truncate } from '@/components/ui/table';

export const dynamic = 'force-dynamic';
export const metadata: Metadata = { title: 'اشتراک‌ها' };

const LABEL: Record<string, string> = { approved: 'تأییدشده', pending: 'در انتظار تأیید', rejected: 'ردشده' };

export default async function AdminSubscriptionsPage() {
  const subs = await getAdminSubscriptions();
  return (
    <div>
      <PageHeader title="اشتراک‌ها" description="آخرین اشتراک هر فروشگاه، با اولویت موارد در انتظار تأیید. تأیید و رد از ربات انجام می‌شود." />
      {subs.length > 0 ? (
        <Table caption="اشتراک‌های فروشگاه‌ها">
          <thead>
            <tr><Th>فروشگاه</Th><Th>پلن</Th><Th>مبلغ</Th><Th>شروع</Th><Th>پایان</Th><Th>وضعیت</Th></tr>
          </thead>
          <tbody>
            {subs.map((s) => (
              <tr key={s.id}>
                <Td className="font-semibold"><Truncate max="max-w-48">{s.shop_name}</Truncate></Td>
                <Td>{s.is_trial ? 'دوره‌ی آزمایشی' : s.plan_name ?? '—'}</Td>
                <Td className="tabular-nums">{s.price != null && !s.is_trial ? formatPrice(s.price) : '—'}</Td>
                <Td className="whitespace-nowrap tabular-nums">{formatDate(s.start_date)}</Td>
                <Td className="whitespace-nowrap tabular-nums">{formatDate(s.end_date)}</Td>
                <Td>
                  <Badge tone={s.approval_status === 'approved' ? 'success' : s.approval_status === 'pending' ? 'warning' : 'danger'}>
                    {LABEL[s.approval_status] ?? s.approval_status}
                  </Badge>
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      ) : (
        <EmptyState icon={CreditCard} title="هنوز اشتراکی ثبت نشده" description="با ثبت اولین فروشگاه یا خرید پلن، اشتراک‌ها اینجا نمایش داده می‌شوند." />
      )}
    </div>
  );
}
