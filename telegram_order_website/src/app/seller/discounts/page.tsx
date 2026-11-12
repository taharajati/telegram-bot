import type { Metadata } from 'next';
import { Ticket } from 'lucide-react';
import { getSellerContext } from '@/lib/panel';
import { getDiscountCodesByShop } from '@/lib/queries';
import { formatDate, formatNumber, formatPrice } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { EmptyState, PageHeader } from '@/components/ui/states';
import { Table, Td, Th } from '@/components/ui/table';

export const dynamic = 'force-dynamic';
export const metadata: Metadata = { title: 'کدهای تخفیف' };

export default async function SellerDiscountsPage() {
  const { shop } = await getSellerContext();
  const codes = await getDiscountCodesByShop(shop.id);
  const now = new Date();

  return (
    <div>
      <PageHeader title="کدهای تخفیف" description="فهرست کدهای فروشگاه. ساخت و ویرایش کد از ربات تلگرام انجام می‌شود." />
      {codes.length > 0 ? (
        <Table caption="کدهای تخفیف فروشگاه">
          <thead>
            <tr><Th>کد</Th><Th>مقدار</Th><Th>حداقل سفارش</Th><Th>استفاده</Th><Th>انقضا</Th><Th>وضعیت</Th></tr>
          </thead>
          <tbody>
            {codes.map((c) => {
              const expired = c.expires_at ? new Date(c.expires_at) < now : false;
              const used = c.max_uses > 0 && c.used_count >= c.max_uses;
              const live = c.is_active && !expired && !used;
              return (
                <tr key={c.id}>
                  <Td className="font-mono font-semibold" dir="ltr"><bdi>{c.code}</bdi></Td>
                  <Td className="tabular-nums">
                    {c.discount_type === 'percent' ? `${formatNumber(Number(c.discount_value))}٪` : formatPrice(c.discount_value)}
                  </Td>
                  <Td className="tabular-nums">{Number(c.min_order_amount) > 0 ? formatPrice(c.min_order_amount) : '—'}</Td>
                  <Td className="tabular-nums">{formatNumber(c.used_count)}{c.max_uses > 0 ? ` از ${formatNumber(c.max_uses)}` : ''}</Td>
                  <Td className="tabular-nums">{c.expires_at ? formatDate(c.expires_at) : 'بدون انقضا'}</Td>
                  <Td>
                    <Badge tone={live ? 'success' : 'neutral'}>
                      {live ? 'فعال' : expired ? 'منقضی' : used ? 'تمام‌شده' : 'غیرفعال'}
                    </Badge>
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      ) : (
        <EmptyState icon={Ticket} title="هنوز کد تخفیفی نساخته‌ای" description="کد تخفیف را از بخش مدیریت فروشگاه در ربات بساز؛ بعد از ساخت اینجا نمایش داده می‌شود." />
      )}
    </div>
  );
}
