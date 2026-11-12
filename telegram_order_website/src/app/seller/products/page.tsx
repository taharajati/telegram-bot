import type { Metadata } from 'next';
import Link from 'next/link';
import { Package, Plus } from 'lucide-react';
import { getCategoriesByShop, getProductsByShop } from '@/lib/db';
import { getSellerContext } from '@/lib/panel';
import { formatNumber, formatPrice } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { buttonStyles } from '@/components/ui/button';
import { EmptyState, PageHeader } from '@/components/ui/states';
import { Table, Td, Th, Truncate } from '@/components/ui/table';

export const dynamic = 'force-dynamic';
export const metadata: Metadata = { title: 'محصولات' };

export default async function SellerProductsPage() {
  const { shop } = await getSellerContext();
  const [products, cats] = await Promise.all([getProductsByShop(shop.id), getCategoriesByShop(shop.id)]);
  const catMap = new Map(cats.map((c) => [c.id, c.name]));

  const add = (
    <Link href="/seller/products/new" className={buttonStyles()}>
      <Plus className="h-4 w-4" aria-hidden="true" /> افزودن محصول
    </Link>
  );

  return (
    <div>
      <PageHeader title="محصولات" description={`${formatNumber(products.length)} محصول در فروشگاه`} actions={products.length > 0 ? add : undefined} />
      {products.length > 0 ? (
        <Table caption="محصولات فروشگاه">
          <thead>
            <tr>
              <Th>نام</Th><Th>قیمت</Th><Th>دسته</Th><Th>موجودی قابل‌فروش</Th><Th>وضعیت</Th><Th><span className="sr-only">عملیات</span></Th>
            </tr>
          </thead>
          <tbody>
            {products.map((p) => {
              const available = p.stock - p.reserved_stock;
              return (
                <tr key={p.id} className="hover:bg-canvas">
                  <Td className="font-semibold"><Truncate max="max-w-56">{p.name}</Truncate></Td>
                  <Td className="tabular-nums">{formatPrice(p.price)}</Td>
                  <Td className="text-ink-muted">{catMap.get(p.category_id) || '—'}</Td>
                  <Td className="tabular-nums">
                    {formatNumber(available)}
                    {available < 5 && p.is_active && <span className="ms-2"><Badge tone="warning">کم</Badge></span>}
                  </Td>
                  <Td>
                    <form action="/api/seller/toggle-product" method="POST">
                      <input type="hidden" name="product_id" value={p.id} />
                      <button
                        type="submit"
                        className="inline-flex min-h-9 items-center rounded-sm border border-line-strong px-3 text-xs font-semibold hover:bg-canvas"
                        title={p.is_active ? 'برای غیرفعال‌کردن کلیک کن' : 'برای فعال‌کردن کلیک کن'}
                      >
                        {p.is_active ? 'فعال' : 'غیرفعال'}
                      </button>
                    </form>
                  </Td>
                  <Td>
                    <Link href={`/seller/products/${p.id}/edit`} className="font-semibold text-brand underline-offset-4 hover:underline">
                      ویرایش<span className="sr-only"> {p.name}</span>
                    </Link>
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      ) : (
        <EmptyState
          icon={Package}
          title="هنوز محصولی اضافه نکرده‌ای"
          description="با افزودن محصول، فروشگاه در ربات و وب‌سایت قابل سفارش می‌شود."
          action={add}
        />
      )}
    </div>
  );
}
