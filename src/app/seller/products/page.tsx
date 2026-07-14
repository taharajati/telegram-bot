// ─── Seller: Products ───
import { Package } from 'lucide-react';
import { getShopOwner, getProductsByShop, getCategoriesByShop } from '@/lib/db';
import { requireSeller } from '@/lib/auth';
import { redirect } from 'next/navigation';
import { formatPrice } from '@/lib/utils';
import Card from '@/components/shared/Card';

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
      <h1 className="mb-6 text-2xl font-black">محصولات من</h1>

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
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <Card>
          <div className="py-12 text-center">
            <Package className="mx-auto mb-3 h-10 w-10 text-[var(--text-tertiary)]" />
            <p className="text-[var(--text-tertiary)]">هیچ محصولی ثبت نشده. از طریق ربات تلگرام محصول اضافه کنید.</p>
          </div>
        </Card>
      )}
    </div>
  );
}
