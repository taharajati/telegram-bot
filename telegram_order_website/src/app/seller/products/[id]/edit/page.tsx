import type { Metadata } from 'next';
import { PageHeader } from '@/components/ui/states';
import { ProductForm } from '@/components/panel/product-form';

export const metadata: Metadata = { title: 'ویرایش محصول' };

export default async function EditProductPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <div className="max-w-3xl">
      <PageHeader title="ویرایش محصول" />
      <ProductForm productId={id} />
    </div>
  );
}
