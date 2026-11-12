'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import toast from 'react-hot-toast';
import { Loader2, Upload, X } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Field, Input, Select, Textarea } from '@/components/ui/field';
import { buttonStyles } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/states';
import { normalizeDigits } from '@/lib/utils';

interface Category { id: number; name: string }
interface FormState {
  name: string;
  description: string;
  price: string;
  stock: string;
  category_id: string;
  images: string[];
}

const EMPTY: FormState = { name: '', description: '', price: '', stock: '', category_id: '', images: [] };

export function ProductForm({ productId }: { productId?: string }) {
  const router = useRouter();
  const editing = Boolean(productId);
  const [form, setForm] = useState<FormState>(EMPTY);
  const [categories, setCategories] = useState<Category[]>([]);
  const [ready, setReady] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(0);
  const [errors, setErrors] = useState<Partial<Record<keyof FormState, string>>>({});

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const catsRes = await fetch('/api/seller/categories');
        if (!catsRes.ok) throw new Error('categories');
        const cats = await catsRes.json();
        if (cancelled) return;
        setCategories(Array.isArray(cats) ? cats : []);
        if (productId) {
          const res = await fetch(`/api/seller/products/${productId}`);
          if (!res.ok) throw new Error('product');
          const p = await res.json();
          if (cancelled) return;
          setForm({
            name: p.name || '',
            description: p.description || '',
            price: p.price?.toString() || '',
            stock: p.stock?.toString() || '',
            category_id: p.category_id?.toString() || '',
            images: p.images || [],
          });
        }
        setReady(true);
      } catch {
        if (!cancelled) setLoadError('اطلاعات فرم بارگذاری نشد. اتصال را بررسی کن و دوباره تلاش کن.');
      }
    })();
    return () => { cancelled = true; };
  }, [productId]);

  const set = (key: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? []);
    e.target.value = '';
    for (const file of files) {
      setUploading((n) => n + 1);
      try {
        const fd = new FormData();
        fd.append('file', file);
        const res = await fetch('/api/seller/products/upload', { method: 'POST', body: fd });
        const data = await res.json().catch(() => ({}));
        if (data.success) setForm((f) => ({ ...f, images: [...f.images, data.url] }));
        else toast.error(data.message || data.error || `بارگذاری «${file.name}» انجام نشد. فرمت JPG، PNG یا WebP و حجم کمتر از ۵ مگابایت مجاز است.`);
      } catch {
        toast.error(`بارگذاری «${file.name}» انجام نشد. اتصال را بررسی کن.`);
      } finally {
        setUploading((n) => n - 1);
      }
    }
  }

  function validate() {
    const next: typeof errors = {};
    if (!form.name.trim()) next.name = 'نام محصول را وارد کن.';
    const price = parseFloat(normalizeDigits(form.price));
    if (!Number.isFinite(price) || price < 0) next.price = 'قیمت را به تومان و به‌صورت عدد وارد کن.';
    const stock = parseInt(normalizeDigits(form.stock));
    if (!Number.isInteger(stock) || stock < 0) next.stock = 'موجودی را به‌صورت عدد صحیح وارد کن.';
    if (!form.category_id) next.category_id = 'یک دسته‌بندی انتخاب کن.';
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;
    setSaving(true);
    try {
      const res = await fetch(editing ? `/api/seller/products/${productId}` : '/api/seller/products', {
        method: editing ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...form,
          price: parseFloat(normalizeDigits(form.price)),
          stock: parseInt(normalizeDigits(form.stock)),
          category_id: parseInt(form.category_id),
        }),
      });
      if (res.ok) {
        toast.success(editing ? 'تغییرات ذخیره شد.' : 'محصول اضافه شد.');
        router.push('/seller/products');
        router.refresh();
      } else {
        const err = await res.json().catch(() => ({}));
        toast.error(err.message || err.error || 'ذخیره انجام نشد. ورودی‌ها را بررسی کن و دوباره تلاش کن.');
      }
    } catch {
      toast.error('ارتباط با سرور برقرار نشد. اتصال را بررسی کن و دوباره تلاش کن.');
    } finally {
      setSaving(false);
    }
  }

  if (loadError) {
    return (
      <Card>
        <p role="alert" className="text-sm font-medium text-danger">{loadError}</p>
        <button type="button" onClick={() => window.location.reload()} className={buttonStyles({ variant: 'secondary', className: 'mt-3' })}>
          تلاش دوباره
        </button>
      </Card>
    );
  }

  if (!ready) {
    return (
      <Card className="space-y-4">
        <Skeleton className="h-11 w-full" />
        <Skeleton className="h-24 w-full" />
        <div className="grid gap-4 sm:grid-cols-2"><Skeleton className="h-11" /><Skeleton className="h-11" /></div>
        <Skeleton className="h-11 w-full" />
      </Card>
    );
  }

  const invalid = (k: keyof FormState) => (errors[k] ? true : undefined);

  return (
    <Card>
      <form onSubmit={onSubmit} noValidate className="space-y-5">
        <Field id="name" label="نام محصول" required error={errors.name}>
          <Input id="name" value={form.name} onChange={set('name')} aria-invalid={invalid('name')} aria-describedby={errors.name ? 'name-error' : undefined} placeholder="مثلاً: کفش ورزشی مردانه" />
        </Field>

        <Field id="description" label="توضیحات" hint="ویژگی‌ها، سایز و شرایط نگهداری را بنویس.">
          <Textarea id="description" rows={4} value={form.description} onChange={set('description')} aria-describedby="description-hint" />
        </Field>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field id="price" label="قیمت (تومان)" required error={errors.price}>
            <Input id="price" dir="ltr" inputMode="numeric" value={form.price} onChange={set('price')} aria-invalid={invalid('price')} aria-describedby={errors.price ? 'price-error' : undefined} />
          </Field>
          <Field id="stock" label="موجودی انبار (عدد)" required error={errors.stock}>
            <Input id="stock" dir="ltr" inputMode="numeric" value={form.stock} onChange={set('stock')} aria-invalid={invalid('stock')} aria-describedby={errors.stock ? 'stock-error' : undefined} />
          </Field>
        </div>

        <Field id="category_id" label="دسته‌بندی" required error={errors.category_id}>
          <Select id="category_id" value={form.category_id} onChange={set('category_id')} aria-invalid={invalid('category_id')} aria-describedby={errors.category_id ? 'category_id-error' : undefined}>
            <option value="">انتخاب دسته‌بندی</option>
            {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </Select>
          {categories.length === 0 && (
            <p className="text-xs text-ink-subtle">دسته‌بندی‌ها از ربات تلگرام ساخته می‌شوند. ابتدا یک دسته در ربات بساز.</p>
          )}
        </Field>

        <fieldset>
          <legend className="mb-2 text-sm font-semibold">تصاویر محصول</legend>
          <ul className="grid grid-cols-3 gap-3 sm:grid-cols-4">
            {form.images.map((src, i) => (
              <li key={src + i} className="relative aspect-square overflow-hidden rounded-sm border border-line">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={src} alt={`تصویر ${i + 1} محصول`} className="h-full w-full object-cover" />
                <button
                  type="button"
                  aria-label={`حذف تصویر ${i + 1}`}
                  onClick={() => setForm((f) => ({ ...f, images: f.images.filter((_, j) => j !== i) }))}
                  className="absolute end-1 top-1 inline-flex h-8 w-8 items-center justify-center rounded-sm bg-surface text-danger border border-line-strong"
                >
                  <X className="h-4 w-4" aria-hidden="true" />
                </button>
              </li>
            ))}
            {uploading > 0 && (
              <li className="flex aspect-square items-center justify-center rounded-sm border border-dashed border-brand" role="status" aria-label="در حال بارگذاری تصویر">
                <Loader2 className="h-6 w-6 text-brand motion-safe:animate-spin" aria-hidden="true" />
              </li>
            )}
            <li>
              <label className="flex aspect-square cursor-pointer flex-col items-center justify-center gap-1 rounded-sm border border-dashed border-line-strong text-xs text-ink-muted hover:bg-canvas focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-brand">
                <Upload className="h-5 w-5" aria-hidden="true" />
                افزودن تصویر
                <input type="file" accept="image/*" multiple onChange={onUpload} className="sr-only" />
              </label>
            </li>
          </ul>
          <p className="mt-2 text-xs text-ink-subtle">فرمت‌های JPG، PNG و WebP؛ حداکثر ۵ مگابایت برای هر تصویر.</p>
        </fieldset>

        <div className="flex flex-wrap items-center gap-3 border-t border-line pt-5">
          <button type="submit" disabled={saving || uploading > 0} className={buttonStyles()}>
            {saving && <Loader2 className="h-4 w-4 motion-safe:animate-spin" aria-hidden="true" />}
            {editing ? 'ذخیره‌ی تغییرات' : 'افزودن محصول'}
          </button>
          <Link href="/seller/products" className={buttonStyles({ variant: 'ghost' })}>انصراف</Link>
          {uploading > 0 && <span className="text-xs text-ink-subtle">تا پایان بارگذاری تصویر منتظر بمان.</span>}
        </div>
      </form>
    </Card>
  );
}
