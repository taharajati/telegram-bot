import Link from 'next/link';
import { Package } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { formatPrice, productImageSrc } from '@/lib/utils';
import type { PublicProduct } from '@/lib/queries';

export function ProductImage({
  product,
  className,
}: {
  product: { id: number; name: string; image_url?: string | null; image_file_id?: string | null };
  className?: string;
}) {
  const src = productImageSrc(product);
  return (
    <div className={`flex items-center justify-center overflow-hidden bg-canvas ${className ?? ''}`}>
      {src ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={src} alt={product.name} loading="lazy" className="h-full w-full object-cover" />
      ) : (
        <Package className="h-8 w-8 text-ink-subtle" aria-label="بدون تصویر" role="img" />
      )}
    </div>
  );
}

export function ProductCard({ product, showShop }: { product: PublicProduct; showShop?: boolean }) {
  const available = product.stock - product.reserved_stock > 0;
  return (
    <Link
      href={`/product/${product.id}`}
      className="group flex h-full flex-col overflow-hidden rounded-md border border-line bg-surface transition-colors hover:border-brand"
    >
      <ProductImage product={product} className="aspect-square rounded-t-md" />
      <div className="flex flex-1 flex-col gap-1 p-4">
        <h3 className="truncate font-bold" title={product.name}>{product.name}</h3>
        <p className="truncate text-xs text-ink-subtle">
          {[product.category_name, showShop ? product.shop_name : null].filter(Boolean).join(' · ') || '\u00a0'}
        </p>
        <div className="mt-auto flex items-center justify-between gap-2 pt-2">
          <span className="font-extrabold tabular-nums text-ink">{formatPrice(product.price)}</span>
          {!available && <Badge tone="danger">ناموجود</Badge>}
        </div>
      </div>
    </Link>
  );
}
