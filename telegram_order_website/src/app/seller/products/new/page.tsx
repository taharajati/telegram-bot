import type { Metadata } from 'next';
import { PageHeader } from '@/components/ui/states';
import { ProductForm } from '@/components/panel/product-form';

export const metadata: Metadata = { title: 'افزودن محصول' };

export default function NewProductPage() {
  return (
    <div className="max-w-3xl">
      <PageHeader title="افزودن محصول" description="محصول بعد از ذخیره در فروشگاه و ربات نمایش داده می‌شود." />
      <ProductForm />
    </div>
  );
}
