import type { Metadata } from 'next';
import Link from 'next/link';
import { Package } from 'lucide-react';
import { getAllProducts, getAllShops } from '@/lib/db';
import { formatNumber, formatPrice } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { buttonStyles } from '@/components/ui/button';
import { Select } from '@/components/ui/field';
import { EmptyState, PageHeader } from '@/components/ui/states';
import { Table, Td, Th, Truncate } from '@/components/ui/table';

export const dynamic = 'force-dynamic';
export const metadata: Metadata = { title: 'محصولات' };

export default async function AdminProductsPage({
  searchParams,
}: {
  searchParams: Promise<{ shop_id?: string }>;
}) {
  const { shop_id } = await searchParams;
  const shopId = shop_id && /^\d+$/.test(shop_id) ? parseInt(shop_id, 10) : null;
  const [products, shops] = await Promise.all([getAllProducts(), getAllShops()]);
  const shopMap = new Map(shops.map((s) => [s.id, s.name]));
  const filtered = shopId ? products.filter((p) => p.shop_id === shopId) : products;

  return (
    <div>
      <PageHeader title="محصولات" description={`${formatNumber(filtered.length)} محصول${shopId ? ' در فروشگاه انتخاب‌شده' : ' در همه‌ی فروشگاه‌ها'}`} />

      <form method="GET" className="mb-4 flex flex-wrap items-end gap-2">
        <div className="min-w-56">
          <label htmlFor="shop_id" className="mb-1 block text-sm font-semibold">فروشگاه</label>
          <Select id="shop_id" name="shop_id" defaultValue={shopId ? String(shopId) : ''}>
            <option value="">همه‌ی فروشگاه‌ها</option>
            {shops.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </Select>
        </div>
        <button type="submit" className={buttonStyles({ variant: 'secondary' })}>اعمال فیلتر</button>
      </form>

      {filtered.length > 0 ? (
        <Table caption="محصولات پلتفرم">
          <thead>
            <tr><Th>نام</Th><Th>فروشگاه</Th><Th>قیمت</Th><Th>موجودی قابل‌فروش</Th><Th>وضعیت</Th><Th><span className="sr-only">عملیات</span></Th></tr>
          </thead>
          <tbody>
            {filtered.map((p) => (
              <tr key={p.id} className="hover:bg-canvas">
                <Td className="font-semibold"><Truncate max="max-w-56">{p.name}</Truncate></Td>
                <Td className="text-ink-muted"><Truncate max="max-w-40">{shopMap.get(p.shop_id) || `#${p.shop_id}`}</Truncate></Td>
                <Td className="tabular-nums">{formatPrice(p.price)}</Td>
                <Td className="tabular-nums">{formatNumber(p.stock - p.reserved_stock)}</Td>
                <Td><Badge tone={p.is_active ? 'success' : 'danger'}>{p.is_active ? 'فعال' : 'غیرفعال'}</Badge></Td>
                <Td>
                  <Link href={`/product/${p.id}`} className="font-semibold text-brand underline-offset-4 hover:underline">
                    مشاهده<span className="sr-only"> {p.name}</span>
                  </Link>
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      ) : (
        <EmptyState icon={Package} title="محصولی پیدا نشد" description={shopId ? 'این فروشگاه هنوز محصولی ندارد یا فیلتر دیگری را امتحان کن.' : 'هنوز محصولی در پلتفرم ثبت نشده است.'} />
      )}
    </div>
  );
}
