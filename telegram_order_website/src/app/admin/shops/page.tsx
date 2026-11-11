// ─── Admin: Shops ───
import Link from 'next/link';
import { Store } from 'lucide-react';
import { getAllShops } from '@/lib/db';
import { toJalali } from '@/lib/utils';
import Card from '@/components/shared/Card';

export const dynamic = 'force-dynamic';

export default async function AdminShopsPage() {
  const shops = await getAllShops();

  return (
    <div>
      <h1 className="mb-6 text-2xl font-black">فروشگاه‌ها</h1>

      {shops.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {shops.map((shop: any) => (
            <Card key={shop.id}>
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="font-bold">{shop.name}</h3>
                  {shop.description && (
                    <p className="mt-1 text-sm text-[var(--text-tertiary)] line-clamp-2">{shop.description}</p>
                  )}
                  <div className="mt-2 flex items-center gap-2 text-xs text-[var(--text-tertiary)]">
                    <span>شناسه: {shop.id}</span>
                    <span>·</span>
                    <span>{toJalali(shop.created_at)}</span>
                  </div>
                </div>
                <span className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${
                  shop.is_active ? 'bg-[var(--success)]/10 text-[var(--success)]' : 'bg-[var(--danger)]/10 text-[var(--danger)]'
                }`}>
                  <span className={`h-1.5 w-1.5 rounded-full ${shop.is_active ? 'bg-[var(--success)]' : 'bg-[var(--danger)]'}`} />
                  {shop.is_active ? 'فعال' : 'غیرفعال'}
                </span>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <Card><p className="py-8 text-center text-[var(--text-tertiary)]">هیچ فروشگاهی یافت نشد.</p></Card>
      )}
    </div>
  );
}
