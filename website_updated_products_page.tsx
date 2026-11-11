// ─── Seller: Products ───
import { Package, Plus } from 'lucide-react';
import { getShopOwner, getProductsByShop, getCategoriesByShop } from '@/lib/db';
import { requireSeller } from '@/lib/auth';
import { redirect } from 'next/navigation';
import { formatPrice } from '@/lib/utils';
import Card from '@/components/shared/Card';
import Link from 'next/link';

export const dynamic = 'force-dynamic';

export default async function SellerProductsPage() {
  const session = await requireSeller().catch(() => redirect('/login'));
  const owner = await getShopOwner(session.userId);
  if (!owner) redirect('/login');

  const products = await getProductsByShop(owner.shop_id);
  const cats = await getCategoriesByShop(owner.shop_id);
  const catMap = new Map(cats.map((c) => [c.id, c.name]));

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-black">محصولات من</h1>
        <Link
          href="/seller/products/new"
          className="flex items-center gap-2 rounded-[var(--radius)] bg-[var(--primary)] px-4 py-2.5 font-bold text-white transition hover:bg-[var(--primary-dark)]"
        >
          <Plus size={20} />
          افزودن محصول
        </Link>
      </div>

      {products.length > 0 ? (
        <div className="overflow-x-auto rounded-[var(--radius-xl)] border border-[var(--border-light)] bg-white shadow-[var(--shadow-card)]">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border-light)]">
                <th className="px-4 py-3 text-right font-semibold text-[var(--text-tertiary)]">نام</th>
                <th className="px-4 py-3 text-right font-semibold text-[var(--text-tertiary)]">قیمت</th>
                <th className="px-4 py-3 text-right font-semibold text-[var(--text-tertiary)]">دسته</th>
                <th className="px-4 py-3 text-right font-semibold text-[var(--text-tertiary)]">موجودی</th>
                <th className="px-4 py-3 text-right font-semibold text-[var(--text-tertiary)]">فعال</th>
                <th className="px-4 py-3 text-right font-semibold text-[var(--text-tertiary)]">عملیات</th>
              </tr>
            </thead>
            <tbody>
              {products.map((product) => (
                <tr key={product.id} className="border-b border-[var(--border-light)]/50 transition hover:bg-[var(--bg-muted)]">
                  <td className="px-4 py-3 font-semibold">{product.name}</td>
                  <td className="px-4 py-3 font-bold text-[var(--primary)]">{formatPrice(product.price)}</td>
                  <td className="px-4 py-3 text-[var(--text-secondary)]">{catMap.get(product.category_id) || '—'}</td>
                  <td className="px-4 py-3 text-[var(--text-secondary)]">{product.stock - product.reserved_stock}</td>
                  <td className="px-4 py-3">
                    <form action="/api/seller/toggle-product" method="POST">
                      <input type="hidden" name="product_id" value={product.id} />
                      <button type="submit" className={`rounded-[var(--radius)] px-2.5 py-1 text-xs font-semibold transition ${
                        product.is_active
                          ? 'bg-[var(--success)]/10 text-[var(--success)] hover:bg-[var(--success)]/20'
                          : 'bg-[var(--danger)]/10 text-[var(--danger)] hover:bg-[var(--danger)]/20'
                      }`}>
                        {product.is_active ? 'فعال' : 'غیرفعال'}
                      </button>
                    </form>
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      href={`/seller/products/${product.id}/edit`}
                      className="text-[var(--primary)] hover:underline text-sm font-semibold"
                    >
                      ویرایش
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <Card>
          <div className="py-12 text-center">
            <Package className="mx-auto mb-3 h-10 w-10 text-[var(--text-tertiary)]" />
            <p className="text-[var(--text-tertiary)] mb-4">هیچ محصولی ثبت نشده.</p>
            <Link
              href="/seller/products/new"
              className="inline-flex items-center gap-2 rounded-[var(--radius)] bg-[var(--primary)] px-6 py-3 font-bold text-white transition hover:bg-[var(--primary-dark)]"
            >
              <Plus size={20} />
              اولین محصول خود را اضافه کنید
            </Link>
          </div>
        </Card>
      )}
    </div>
  );
}
