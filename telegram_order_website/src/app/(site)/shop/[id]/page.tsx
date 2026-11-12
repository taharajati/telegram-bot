import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import Link from 'next/link';
import { ArrowRight, ExternalLink, Package, Phone } from 'lucide-react';
import { getCategoriesByShop } from '@/lib/db';
import { getPublicProducts, getPublicShop } from '@/lib/queries';
import { botUrl, formatNumber, normalizeDigits } from '@/lib/utils';
import { buttonStyles } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/states';
import { Input } from '@/components/ui/field';
import { ProductCard } from '@/components/site/product-card';

export const dynamic = 'force-dynamic';

type Props = {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ cat?: string; q?: string }>;
};

export async function generateMetadata({ params }: Pick<Props, 'params'>): Promise<Metadata> {
  const { id } = await params;
  const shop = await getPublicShop(parseInt(id)).catch(() => null);
  if (!shop) return { title: 'فروشگاه پیدا نشد' };
  return {
    title: shop.name,
    description: shop.description || `فروشگاه ${shop.name} در فروشگرام`,
    openGraph: { title: shop.name, description: shop.description || `فروشگاه ${shop.name}`, type: 'website' },
  };
}

export default async function ShopPage({ params, searchParams }: Props) {
  const { id } = await params;
  const { cat, q: rawQ } = await searchParams;
  const shopId = parseInt(id);
  if (!Number.isInteger(shopId)) notFound();

  const shop = await getPublicShop(shopId).catch(() => null);
  if (!shop) notFound();

  const q = rawQ ? normalizeDigits(rawQ).trim().slice(0, 80) : '';
  const catId = cat && /^\d+$/.test(cat) ? parseInt(cat) : undefined;

  const [products, categories] = await Promise.all([
    getPublicProducts({ shopId, categoryId: catId, q: q || undefined, limit: 60 }).catch(() => []),
    getCategoriesByShop(shopId).catch(() => []),
  ]);

  const href = (params: { cat?: number }) => {
    const sp = new URLSearchParams();
    if (params.cat) sp.set('cat', String(params.cat));
    if (q) sp.set('q', q);
    const s = sp.toString();
    return `/shop/${shopId}${s ? `?${s}` : ''}`;
  };

  const chip = (active: boolean) =>
    `inline-flex min-h-9 items-center rounded-sm border px-3 text-sm font-medium transition-colors ${
      active ? 'border-brand bg-brand-soft text-brand-strong' : 'border-line-strong bg-surface text-ink-muted hover:text-ink'
    }`;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <nav aria-label="مسیر صفحه" className="mb-4 text-sm text-ink-subtle">
        <Link href="/shops" className="inline-flex items-center gap-1 hover:text-brand">
          <ArrowRight className="h-4 w-4" aria-hidden="true" />
          همه‌ی فروشگاه‌ها
        </Link>
      </nav>

      <header className="rounded-md border border-line bg-surface p-6">
        <h1 className="text-2xl font-extrabold md:text-3xl">{shop.name}</h1>
        {shop.description && (
          <p className="mt-2 max-w-prose whitespace-pre-line text-sm text-ink-muted">{shop.description}</p>
        )}
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <a href={botUrl(`shop_${shopId}`)} target="_blank" rel="noopener noreferrer" className={buttonStyles({})}>
            خرید در تلگرام
            <ExternalLink className="h-4 w-4" aria-hidden="true" />
          </a>
          {shop.phone && (
            <a href={`tel:${shop.phone}`} className={buttonStyles({ variant: 'secondary' })}>
              <Phone className="h-4 w-4" aria-hidden="true" />
              <bdi dir="ltr">{shop.phone}</bdi>
            </a>
          )}
          {shop.channel_link && /^https?:\/\//.test(shop.channel_link) && (
            <a href={shop.channel_link} target="_blank" rel="noopener noreferrer" className={buttonStyles({ variant: 'ghost' })}>
              کانال تلگرام
            </a>
          )}
        </div>
      </header>

      <section className="mt-8" aria-labelledby="products-h">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 id="products-h" className="text-lg font-bold">محصول‌ها ({formatNumber(products.length)})</h2>
          <form action={`/shop/${shopId}`} method="GET" role="search" className="flex gap-2">
            {catId && <input type="hidden" name="cat" value={catId} />}
            <label htmlFor="q" className="sr-only">جست‌وجو در این فروشگاه</label>
            <Input id="q" name="q" type="search" defaultValue={q} placeholder="جست‌وجو در این فروشگاه" maxLength={80} className="w-56" />
            <button type="submit" className={buttonStyles({ variant: 'secondary' })}>جست‌وجو</button>
          </form>
        </div>

        {categories.length > 0 && (
          <div className="mb-5 flex flex-wrap gap-2" role="group" aria-label="فیلتر دسته‌بندی">
            <Link href={href({})} className={chip(!catId)} aria-current={!catId ? 'true' : undefined}>همه</Link>
            {categories.map((c: { id: number; name: string }) => (
              <Link key={c.id} href={href({ cat: c.id })} className={chip(catId === c.id)} aria-current={catId === c.id ? 'true' : undefined}>
                {c.name}
              </Link>
            ))}
          </div>
        )}

        {products.length > 0 ? (
          <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {products.map((p) => (
              <li key={p.id}><ProductCard product={p} /></li>
            ))}
          </ul>
        ) : (
          <EmptyState
            icon={Package}
            title={q || catId ? 'محصولی با این فیلتر پیدا نشد' : 'این فروشگاه هنوز محصولی ندارد'}
            description={q || catId ? 'فیلتر را بردار یا عبارت دیگری را امتحان کن.' : 'برای سؤال درباره‌ی محصول‌ها از ربات به فروشنده پیام بده.'}
            action={
              q || catId ? (
                <Link href={`/shop/${shopId}`} className={buttonStyles({ variant: 'secondary' })}>برداشتن فیلتر</Link>
              ) : (
                <a href={botUrl(`shop_${shopId}`)} target="_blank" rel="noopener noreferrer" className={buttonStyles({ variant: 'secondary' })}>
                  باز کردن در تلگرام
                </a>
              )
            }
          />
        )}
      </section>
    </div>
  );
}
