import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import Link from 'next/link';
import { ArrowRight, ExternalLink, Store } from 'lucide-react';
import { getPublicProduct, getPublicShop } from '@/lib/queries';
import { botUrl, formatNumber, formatPrice, productImageSrc } from '@/lib/utils';
import { buttonStyles } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ProductImage } from '@/components/site/product-card';

export const dynamic = 'force-dynamic';

type Props = { params: Promise<{ id: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const product = await getPublicProduct(parseInt(id)).catch(() => null);
  if (!product) return { title: 'محصول پیدا نشد' };
  const image = productImageSrc(product);
  return {
    title: product.name,
    description: product.description || `${product.name} — ${formatPrice(product.price)}`,
    openGraph: {
      title: product.name,
      description: product.description || formatPrice(product.price),
      type: 'website',
      images: image ? [{ url: image, width: 640, height: 640 }] : undefined,
    },
  };
}

export default async function ProductPage({ params }: Props) {
  const { id } = await params;
  const productId = parseInt(id);
  if (!Number.isInteger(productId)) notFound();

  const product = await getPublicProduct(productId).catch(() => null);
  if (!product) notFound();
  const shop = await getPublicShop(product.shop_id).catch(() => null);

  const available = product.stock - product.reserved_stock;

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <nav aria-label="مسیر صفحه" className="mb-4 text-sm text-ink-subtle">
        <Link href={shop ? `/shop/${shop.id}` : '/shops'} className="inline-flex items-center gap-1 hover:text-brand">
          <ArrowRight className="h-4 w-4" aria-hidden="true" />
          {shop ? shop.name : 'فروشگاه‌ها'}
        </Link>
      </nav>

      <article className="grid gap-8 rounded-md border border-line bg-surface p-5 md:grid-cols-2 md:p-8">
        <ProductImage product={product} className="aspect-square rounded-md border border-line" />

        <div className="flex flex-col">
          {product.category_name && <p className="text-sm text-ink-subtle">{product.category_name}</p>}
          <h1 className="mt-1 text-2xl font-extrabold">{product.name}</h1>
          <p className="mt-3 text-3xl font-extrabold tabular-nums text-brand">{formatPrice(product.price)}</p>

          <div className="mt-3">
            {available > 0 ? (
              <Badge tone="success">موجود ({formatNumber(available)} عدد)</Badge>
            ) : (
              <Badge tone="danger">ناموجود</Badge>
            )}
          </div>

          {product.description && (
            <p className="mt-5 max-w-prose whitespace-pre-line text-sm text-ink-muted">{product.description}</p>
          )}

          {shop && (
            <p className="mt-5 flex items-center gap-2 text-sm text-ink-muted">
              <Store className="h-4 w-4 text-brand" aria-hidden="true" />
              فروشگاه: <Link href={`/shop/${shop.id}`} className="font-semibold text-ink hover:text-brand">{shop.name}</Link>
            </p>
          )}

          <div className="mt-auto pt-8">
            <a href={botUrl(`product_${product.id}`)} target="_blank" rel="noopener noreferrer" className={buttonStyles({ size: 'lg', className: 'w-full' })}>
              {available > 0 ? 'خرید در تلگرام' : 'مشاهده در تلگرام'}
              <ExternalLink className="h-4 w-4" aria-hidden="true" />
            </a>
            <p className="mt-2 text-center text-xs text-ink-subtle">
              {available > 0
                ? 'سفارش و پرداخت کارت‌به‌کارت داخل ربات انجام می‌شود.'
                : 'در ربات می‌توانی «خبرم کن» را بزنی تا با موجود شدن پیام بگیری.'}
            </p>
          </div>
        </div>
      </article>
    </div>
  );
}
