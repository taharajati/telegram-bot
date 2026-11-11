// ─── Public Product Page — shared link destination ───
import { notFound } from 'next/navigation';
import { getProductById, getShopById } from '@/lib/db';
import { formatPrice } from '@/lib/utils';
import { ShoppingCart, ExternalLink, ShoppingBag, Store } from 'lucide-react';
import Link from 'next/link';

export const dynamic = 'force-dynamic';

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const product = await getProductById(parseInt(id)).catch(() => null);
  if (!product) return { title: 'محصول یافت نشد' };
  return {
    title: `${product.name} — فروشگرام`,
    description: product.description || `${product.name} - ${formatPrice(product.price)}`,
    openGraph: {
      title: product.name,
      description: product.description || `${formatPrice(product.price)}`,
      type: 'website',
      images: product.image_file_id
        ? [{ url: `/api/product-image/${product.id}`, width: 640, height: 640 }]
        : undefined,
    },
  };
}

export default async function ProductPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const product = await getProductById(parseInt(id)).catch(() => null);
  if (!product) return notFound();

  const shop = await getShopById(product.shop_id).catch(() => null);
  const BOT_USERNAME = 'Foroshgrambot';
  const botLink = `https://t.me/${BOT_USERNAME}?start=product_${product.id}`;
  const imageUrl = product.image_file_id
    ? `/api/product-image/${product.id}`
    : null;

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      {/* breadcrumb */}
      <div className="mb-6 text-xs text-[var(--text-tertiary)]">
        <Link href="/" className="hover:text-blue-500 transition">خانه</Link>
        <span className="mx-1">/</span>
        <span>{shop?.name || 'محصول'}</span>
        <span className="mx-1">/</span>
        <span className="text-[var(--text)]">{product.name}</span>
      </div>

      {/* product card */}
      <div className="rounded-[var(--radius-xl)] border border-[var(--border-light)] bg-white p-6 shadow-[var(--shadow-card)]">
        {/* image */}
        <div className="mb-6 flex h-64 items-center justify-center rounded-[var(--radius-lg)] bg-[var(--bg-muted)]">
          {imageUrl ? (
            <img
              src={imageUrl}
              alt={product.name}
              className="h-full w-full rounded-[var(--radius-lg)] object-contain"
            />
          ) : (
            <ShoppingBag className="h-16 w-16 text-[var(--text-tertiary)]" />
          )}
        </div>

        {/* name & price */}
        <div className="mb-4">
          <h1 className="text-2xl font-black">{product.name}</h1>
          <p className="mt-1 text-3xl font-bold text-blue-600">{formatPrice(product.price)}</p>
        </div>

        {/* description */}
        {product.description && (
          <p className="mb-4 text-sm leading-relaxed text-[var(--text-secondary)]">
            {product.description}
          </p>
        )}

        {/* stock */}
        <div className="mb-6 flex items-center gap-2">
          {product.stock > 0 ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-green-50 px-3 py-1 text-xs font-semibold text-green-700">
              ✅ موجود ({product.stock} عدد)
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-3 py-1 text-xs font-semibold text-red-700">
              ❌ ناموجود
            </span>
          )}
        </div>

        {/* shop info */}
        {shop && (
          <div className="mb-6 flex items-center gap-2 rounded-[var(--radius)] border border-[var(--border-light)] bg-[var(--bg)] p-3 text-sm text-[var(--text-secondary)]">
            <Store className="h-4 w-4 text-blue-500" />
            <span>فروشگاه: <strong>{shop.name}</strong></span>
          </div>
        )}

        {/* CTA */}
        <a
          href={botLink}
          className="flex w-full items-center justify-center gap-2 rounded-[var(--radius-lg)] bg-blue-500 px-6 py-4 font-bold text-white shadow-lg shadow-blue-500/20 transition-all hover:bg-blue-600 hover:shadow-xl hover:shadow-blue-500/25 active:scale-[0.98]"
        >
          <ShoppingCart className="h-5 w-5" />
          خرید از طریق تلگرام
          <ExternalLink className="h-4 w-4" />
        </a>
        <p className="mt-3 text-center text-xs text-[var(--text-tertiary)]">
          با کلیک روی دکمه بالا، مستقیماً وارد بات تلگرام می‌شوید
        </p>
      </div>

      {/* back to home */}
      <div className="mt-6 text-center">
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
