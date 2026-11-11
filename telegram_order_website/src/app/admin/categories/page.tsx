// ─── Admin: Categories ───
import { Tags } from 'lucide-react';
import { getAllShops, getCategoriesByShop } from '@/lib/db';
import Card from '@/components/shared/Card';

export const dynamic = 'force-dynamic';

export default async function AdminCategoriesPage() {
  const shops = await getAllShops();
  const allCategories = await Promise.all(
    shops.map(async (shop) => ({ shop, categories: await getCategoriesByShop(shop.id) }))
  );

  return (
    <div>
      <h1 className="mb-6 text-2xl font-black">دسته‌بندی‌ها</h1>
      <div className="grid gap-4 lg:grid-cols-2">
        {allCategories
          .filter((s) => s.categories.length > 0)
          .map(({ shop, categories }) => (
            <div key={shop.id} className="rounded-[var(--radius-xl)] border border-[var(--border-light)] bg-white p-5 shadow-[var(--shadow-card)]">
              <h2 className="mb-3 font-bold">{shop.name}</h2>
              {categories.map((cat) => (
                <div key={cat.id} className="flex items-center justify-between border-b border-[var(--border-light)]/50 py-2 last:border-0">
                  <span className="text-sm font-medium">{cat.name}</span>
                  <span className="text-xs text-[var(--text-tertiary)]">{cat.description || '—'}</span>
                </div>
              ))}
            </div>
          ))}
      </div>
    </div>
  );
}