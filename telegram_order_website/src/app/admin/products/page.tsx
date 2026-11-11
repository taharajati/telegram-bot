// ─── Admin: Products ───
import Link from 'next/link';
import { Package } from 'lucide-react';
import { getAllProducts, getAllShops } from '@/lib/db';
import { formatPrice, toJalali } from '@/lib/utils';

export const dynamic = 'force-dynamic';

export default async function AdminProductsPage({
  searchParams,
}: {
  searchParams: Promise<{ shop_id?: string }>;
}) {
  const { shop_id } = await searchParams;
  const [products, shops] = await Promise.all([getAllProducts(), getAllShops()]);
  const filtered = shop_id ? products.filter((p) => p.shop_id === parseInt(shop_id)) : products;

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-black">محصولات</h1>
        <div className="flex flex-wrap gap-1.5">
          <Link
            href="/admin/products"
            className={`rounded-[var(--radius)] px-3 py-1.5 text-xs font-medium transition ${
              !shop_id ? 'bg-[var(--primary)] text-white' : 'border border-[var(--border-light)] bg-white text-[var(--text-secondary)] hover:border-[var(--primary)]'
            }`}
          >
            همه
          </Link>
          {shops.slice(0, 10).map((shop) => (
            <Link
              key={shop.id}
              href={`/admin/products?shop_id=${shop.id}`}
              className={`rounded-[var(--radius)] px-3 py-1.5 text-xs font-medium transition ${
                shop_id === String(shop.id) ? 'bg-[var(--primary)] text-white' : 'border border-[var(--border-light)] bg-white text-[var(--text-secondary)] hover:border-[var(--primary)]'
              }`}
            >
              {shop.name}
            </Link>
          ))}
        </div>
      </div>

      <div className="overflow-x-auto rounded-[var(--radius-xl)] border border-[var(--border-light)] bg-white shadow-[var(--shadow-card)]">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--border-light)]">
              <th className="px-4 py-3 text-right font-semibold text-[var(--text-tertiary)]">#</th>
              <th className="px-4 py-3 text-right font-semibold text-[var(--text-tertiary)]">نام</th>
              <th className="px-4 py-3 text-right font-semibold text-[var(--text-tertiary)]">قیمت</th>
              <th className="px-4 py-3 text-right font-semibold text-[var(--text-tertiary)]">موجودی</th>
              <th className="px-4 py-3 text-right font-semibold text-[var(--text-tertiary)]">فروشگاه</th>
              <th className="px-4 py-3 text-right font-semibold text-[var(--text-tertiary)]">فعال</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((product) => (
              <tr key={product.id} className="border-b border-[var(--border-light)]/50 transition hover:bg-[var(--bg-muted)]">
                <td className="px-4 py-3 text-[var(--text-tertiary)]">{product.id}</td>
                <td className="px-4 py-3 font-semibold">{product.name}</td>
                <td className="px-4 py-3 font-bold text-[var(--primary)]">{formatPrice(product.price)}</td>
                <td className="px-4 py-3 text-[var(--text-secondary)]">{product.stock - product.reserved_stock}</td>
                <td className="px-4 py-3 text-[var(--text-tertiary)]">{product.shop_id}</td>
                <td className="px-4 py-3">
                  <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-semibold ${
                    product.is_active
                      ? 'border-[var(--success)]/30 bg-[var(--success)]/10 text-[var(--success)]'
                      : 'border-[var(--danger)]/30 bg-[var(--danger)]/10 text-[var(--danger)]'
                  }`}>
                    {product.is_active ? 'فعال' : 'غیرفعال'}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <Link href={`/product/${product.id}`} className="text-sm font-semibold text-[var(--primary)] hover:underline">مشاهده</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
