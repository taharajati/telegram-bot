import type { Metadata } from 'next';
import { KeyRound } from 'lucide-react';
import { getAllClaimCodes, getAllShops } from '@/lib/db';
import { formatDate } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { buttonStyles } from '@/components/ui/button';
import { Card, CardTitle } from '@/components/ui/card';
import { Select } from '@/components/ui/field';
import { EmptyState, PageHeader } from '@/components/ui/states';
import { Table, Td, Th } from '@/components/ui/table';

export const dynamic = 'force-dynamic';
export const metadata: Metadata = { title: 'کدهای دعوت' };

export default async function AdminClaimCodesPage() {
  const [codes, shops] = await Promise.all([getAllClaimCodes(), getAllShops()]);
  const shopMap = new Map(shops.map((s) => [s.id, s.name]));

  return (
    <div>
      <PageHeader title="کدهای دعوت" description="هر کد یک‌بار مصرف است و مالک فروشگاه با آن حساب خود را به فروشگاه وصل می‌کند." />

      <Card as="section" className="mb-6 max-w-md">
        <CardTitle>ساخت کد جدید</CardTitle>
        <form action="/api/admin/create-claim-code" method="POST" className="mt-3 space-y-3">
          <label htmlFor="shop_id" className="block text-sm font-semibold">فروشگاه</label>
          <Select id="shop_id" name="shop_id" required defaultValue="">
            <option value="" disabled>انتخاب فروشگاه</option>
            {shops.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </Select>
          <button type="submit" className={buttonStyles()}>ساخت کد دعوت</button>
        </form>
      </Card>

      {codes.length > 0 ? (
        <Table caption="کدهای دعوت">
          <thead>
            <tr><Th>کد</Th><Th>فروشگاه</Th><Th>وضعیت</Th><Th>استفاده‌کننده</Th><Th>انقضا</Th><Th>تاریخ ساخت</Th></tr>
          </thead>
          <tbody>
            {codes.map((c) => (
              <tr key={c.id}>
                <Td className="font-mono text-xs font-semibold" dir="ltr"><bdi>{c.code}</bdi></Td>
                <Td className="text-ink-muted">{shopMap.get(c.shop_id) || `#${c.shop_id}`}</Td>
                <Td><Badge tone={c.is_used ? 'neutral' : 'success'}>{c.is_used ? 'استفاده‌شده' : 'آماده‌ی استفاده'}</Badge></Td>
                <Td className="text-ink-muted tabular-nums" dir="ltr"><bdi>{c.used_by || '—'}</bdi></Td>
                <Td className="whitespace-nowrap tabular-nums">{formatDate(c.expires_at)}</Td>
                <Td className="whitespace-nowrap tabular-nums">{formatDate(c.created_at)}</Td>
              </tr>
            ))}
          </tbody>
        </Table>
      ) : (
        <EmptyState icon={KeyRound} title="هنوز کد دعوتی ساخته نشده" description="برای وصل‌کردن مالک به یک فروشگاه، از فرم بالا یک کد بساز." />
      )}
    </div>
  );
}
