// ─── Public Shop Page — dedicated storefront ───
import { notFound } from 'next/navigation';
import { getShopById, getProductsByShop } from '@/lib/db';
import { formatPrice } from '@/lib/utils';
import { Store, ShoppingBag, ExternalLink, ArrowRight } from 'lucide-react';
import Link from 'next/link';

export const dynamic = 'force-dynamic';

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const shop = await getShopById(parseInt(id)).catch(() => null);
  if (!shop) return { title: 'فروشگاه یافت نشد' };
  return {
    title: `${shop.name} — فروشگرام`,
    description: shop.description || `فروشگاه ${shop.name} در فروشگرام`,
    openGraph: {
      title: shop.name,
      description: shop.description || `فروشگاه ${shop.name}`,
      type: 'website',
    },
  };
}

export default async function ShopPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const shopId = parseInt(id);
  const shop = await getShopById(shopId).catch(() => null);
  if (!shop || !shop.is_active) return notFound();

  const products = await getProductsByShop(shopId).catch(() => []);
  const BOT_USERNAME = 'Foroshgrambot';
  const botLink = `https://t.me/${BOT_USERNAME}?start=shop_${shopId}`;

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      {/* breadcrumb */}
      <div className="mb-6 flex items-center gap-1 text-xs text-[var(--text-tertiary)]">
        <Link href="/" className="hover:text-blue-500 transition">خانه</Link>
        <span>/</span>
        <span className="text-[var(--text)]">{shop.name}</span>
      </div>

      {/* shop header */}
      <div className="mb-10 rounded-[var(--radius-xl)] border border-[var(--border-light)] bg-white p-8 shadow-[var(--shadow-card)]">
        <div className="flex items-start gap-5">
          <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-[var(--radius-lg)] bg-blue-500 text-3xl font-black text-white shadow-lg shadow-blue-500/20">
            {shop.name.charAt(0)}
          </div>
          <div className="min-w-0 flex-1">
            <h1 className="text-3xl font-black md:text-4xl">{shop.name}</h1>
            {shop.description && (
              <p className="mt-3 text-sm leading-relaxed text-[var(--text-secondary)] whitespace-pre-line">
                {shop.description}
              </p>
            )}
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <a
                href={botLink}
                className="inline-flex items-center gap-2 rounded-[var(--radius-lg)] bg-blue-500 px-5 py-2.5 text-sm font-bold text-white shadow-lg shadow-blue-500/20 transition-all hover:bg-blue-600 hover:shadow-xl active:scale-[0.97]"
              >
                <Store className="h-4 w-4" />
                مشاهده در تلگرام
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
              <span className="text-xs text-[var(--text-tertiary)]">
                {products.length} محصول فعال
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* products grid */}
      {products.length > 0 ? (
        <>
          <div className="mb-6 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.15em] text-[var(--text-tertiary)]">
            <span className="h-px w-6 bg-[var(--border)]" />
            محصولات فروشگاه
          </div>
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {products.map((p) => (
              <Link
                key={p.id}
                href={`/product/${p.id}`}
                className="group rounded-[var(--radius-xl)] border border-[var(--border-light)] bg-white p-5 shadow-[var(--shadow-card)] transition-all hover:shadow-[var(--shadow-pop)] hover:-translate-y-0.5"
              >
                <div className="mb-4 flex h-40 items-center justify-center rounded-[var(--radius)] bg-[var(--bg-muted)] overflow-hidden">
                  {p.image_file_id ? (
                    <img
                      src={`/api/product-image/${p.id}`}
                      alt={p.name}
                      className="h-full w-full object-cover transition-transform group-hover:scale-105"
                    />
                  ) : (
                    <ShoppingBag className="h-10 w-10 text-[var(--text-tertiary)]" />
                  )}
                </div>
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <h3 className="truncate font-bold group-hover:text-blue-600 transition-colors">{p.name}</h3>
                    {p.category_name && (
                      <p className="text-xs text-[var(--text-tertiary)]">{p.category_name}</p>
                    )}
                  </div>
                  <span className="shrink-0 font-bold text-blue-600">{formatPrice(p.price)}</span>
                </div>
              </Link>
            ))}
          </div>
        </>
      ) : (
        <div className="rounded-[var(--radius-xl)] border border-dashed border-[var(--border)] bg-[var(--bg)] py-16 text-center">
          <ShoppingBag className="mx-auto mb-3 h-12 w-12 text-[var(--text-tertiary)]" />
          <p className="text-sm text-[var(--text-secondary)]">این فروشگاه هنوز محصولی اضافه نکرده است.</p>
          <a
            href={botLink}
            className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-blue-500 hover:underline"
          >
            ارتباط با فروشنده در تلگرام
            <ArrowRight className="h-3.5 w-3.5" />
          </a>
        </div>
      )}

      {/* back */}
      <div className="mt-10 text-center">
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm text-blue-500 hover:underline"
        >
          ← بازگشت به صفحه اصلی
        </Link>
      </div>
    </div>
  );
}
