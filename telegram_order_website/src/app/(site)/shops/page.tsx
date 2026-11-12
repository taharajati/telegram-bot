import type { Metadata } from 'next';
import Link from 'next/link';
import { Search, Store } from 'lucide-react';
import { getPublicProducts, getPublicShops } from '@/lib/queries';
import { formatNumber, normalizeDigits } from '@/lib/utils';
import { buttonStyles } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/states';
import { Input } from '@/components/ui/field';
import { ProductCard } from '@/components/site/product-card';

export const dynamic = 'force-dynamic';
export const metadata: Metadata = {
  title: 'فروشگاه‌ها و محصولات',
  description: 'فروشگاه‌های فعال فروشگرام را ببین و محصول‌ها را جست‌وجو کن.',
};

export default async function ShopsPage({ searchParams }: { searchParams: Promise<{ q?: string }> }) {
  const { q: rawQ } = await searchParams;
  const q = rawQ ? normalizeDigits(rawQ).trim().slice(0, 80) : '';

  const [shops, products] = await Promise.all([
    getPublicShops({ q: q || undefined, limit: 48 }).catch(() => []),
    q ? getPublicProducts({ q, limit: 24 }).catch(() => []) : Promise.resolve([]),
  ]);

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="text-2xl font-extrabold">فروشگاه‌ها و محصولات</h1>
      <p className="mt-1 text-sm text-ink-muted">نام فروشگاه یا محصول را جست‌وجو کن.</p>

      <form action="/shops" method="GET" role="search" className="mt-6 flex max-w-xl gap-2">
        <div className="flex-1">
          <label htmlFor="q" className="sr-only">جست‌وجو</label>
          <Input id="q" name="q" type="search" defaultValue={q} placeholder="مثلاً: کیف چرم" maxLength={80} />
        </div>
        <button type="submit" className={buttonStyles({})}>
          <Search className="h-4 w-4" aria-hidden="true" />
          جست‌وجو
        </button>
      </form>

      {q && (
        <section className="mt-10" aria-labelledby="products-h">
          <h2 id="products-h" className="mb-4 text-lg font-bold">
            محصول‌ها برای «<bdi>{q}</bdi>» ({formatNumber(products.length)})
          </h2>
          {products.length > 0 ? (
            <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {products.map((p) => (
                <li key={p.id}><ProductCard product={p} showShop /></li>
              ))}
            </ul>
          ) : (
            <EmptyState title="محصولی پیدا نشد" description="عبارت کوتاه‌تر یا نام دیگری را امتحان کن." />
          )}
        </section>
      )}

      <section className="mt-10" aria-labelledby="shops-h">
        <h2 id="shops-h" className="mb-4 text-lg font-bold">
          فروشگاه‌ها ({formatNumber(shops.length)})
        </h2>
        {shops.length > 0 ? (
          <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {shops.map((s) => (
              <li key={s.id}>
                <Link href={`/shop/${s.id}`} className="block h-full rounded-md border border-line bg-surface p-4 transition-colors hover:border-brand">
                  <div className="flex items-start gap-3">
                    <Store className="mt-1 h-5 w-5 shrink-0 text-brand" aria-hidden="true" />
                    <div className="min-w-0">
                      <h3 className="truncate font-bold" title={s.name}>{s.name}</h3>
                      <p className="mt-1 line-clamp-2 text-sm text-ink-muted">{s.description || 'بدون توضیحات'}</p>
                      <p className="mt-2 text-xs text-ink-subtle">{formatNumber(s.product_count)} محصول فعال</p>
                    </div>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState
            icon={Store}
            title={q ? 'فروشگاهی با این نام پیدا نشد' : 'هنوز فروشگاه فعالی ثبت نشده'}
            description={q ? 'نام دیگری را امتحان کن.' : 'اولین فروشگاه را در ربات تلگرام بساز.'}
          />
        )}
      </section>
    </div>
  );
}
