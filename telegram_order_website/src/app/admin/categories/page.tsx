import type { Metadata } from 'next';
import { FolderTree } from 'lucide-react';
import { getAllShops, getCategoriesByShop } from '@/lib/db';
import { Card, CardTitle } from '@/components/ui/card';
import { EmptyState, PageHeader } from '@/components/ui/states';

export const dynamic = 'force-dynamic';
export const metadata: Metadata = { title: 'دسته‌بندی‌ها' };

export default async function AdminCategoriesPage() {
  const shops = await getAllShops();
  const groups = (await Promise.all(shops.map(async (shop) => ({ shop, categories: await getCategoriesByShop(shop.id) }))))
    .filter((g) => g.categories.length > 0);

  return (
    <div>
      <PageHeader title="دسته‌بندی‌ها" description="دسته‌بندی‌ها به تفکیک فروشگاه. ساخت و ویرایش از ربات انجام می‌شود." />
      {groups.length > 0 ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {groups.map(({ shop, categories }) => (
            <Card key={shop.id} as="section">
              <CardTitle>{shop.name}</CardTitle>
              <ul className="mt-2">
                {categories.map((c) => (
                  <li key={c.id} className="flex items-center justify-between gap-4 border-b border-line py-2 text-sm last:border-b-0">
                    <span className="font-medium">{c.name}</span>
                    <span className="truncate text-xs text-ink-subtle">{c.description || '—'}</span>
                  </li>
                ))}
              </ul>
            </Card>
          ))}
        </div>
      ) : (
        <EmptyState icon={FolderTree} title="هنوز دسته‌بندی‌ای ساخته نشده" description="با ساخت اولین دسته در ربات، اینجا نمایش داده می‌شود." />
      )}
    </div>
  );
}
