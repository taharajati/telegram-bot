"use client";

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Upload, X, Loader2, Save } from 'lucide-react';
import Card from '@/components/shared/Card';

export default function EditProductPage() {
  const router = useRouter();
  const params = useParams();
  const productId = params.id as string;
  
  const [loading, setLoading] = useState(false);
  const [uploadingImages, setUploadingImages] = useState<number[]>([]);
  const [categories, setCategories] = useState<{id: number, name: string}[]>([]);
  const [product, setProduct] = useState<any>(null);
  
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    price: '',
    stock: '',
    category_id: '',
    images: [] as string[],
  });

  // Load product and categories
  useEffect(() => {
    const loadData = async () => {
      // Load categories
      const catsRes = await fetch('/api/seller/categories');
      const catsData = await catsRes.json();
      setCategories(catsData);

      // Load product
      const prodRes = await fetch(`/api/seller/products/${productId}`);
      const prodData = await prodRes.json();
      if (prodData) {
        setProduct(prodData);
        setFormData({
          name: prodData.name || '',
          description: prodData.description || '',
          price: prodData.price?.toString() || '',
          stock: prodData.stock?.toString() || '',
          category_id: prodData.category_id?.toString() || '',
          images: prodData.images || [],
        });
      }
    };
    loadData();
  }, [productId]);

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const uploadIndex = formData.images.length + i;
      setUploadingImages(prev => [...prev, uploadIndex]);

      const formDataUpload = new FormData();
      formDataUpload.append('file', file);

      try {
        const res = await fetch('/api/seller/products/upload', {
          method: 'POST',
          body: formDataUpload,
        });
        const data = await res.json();
        
        if (data.success) {
          setFormData(prev => ({
            ...prev,
            images: [...prev.images, data.url],
          }));
        }
      } catch (error) {
        console.error('Upload failed:', error);
      } finally {
        setUploadingImages(prev => prev.filter(idx => idx !== uploadIndex));
      }
    }
  };

  const removeImage = (index: number) => {
    setFormData(prev => ({
      ...prev,
      images: prev.images.filter((_, i) => i !== index),
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const res = await fetch(`/api/seller/products/${productId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...formData,
          price: parseFloat(formData.price),
          stock: parseInt(formData.stock),
          category_id: parseInt(formData.category_id),
        }),
      });

      if (res.ok) {
        router.push('/seller/products');
      } else {
        const error = await res.json();
        alert('خطا: ' + (error.message || 'مشکلی رخ داد'));
      }
    } catch (error) {
      alert('خطا در ارتباط با سرور');
    } finally {
      setLoading(false);
    }
  };

  if (!product) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="animate-spin text-[var(--primary)]" size={40} />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-black">ویرایش محصول</h1>
        <button
          onClick={() => router.back()}
          className="rounded-[var(--radius)] px-4 py-2 text-sm font-semibold text-[var(--text-secondary)] hover:bg-[var(--bg-muted)]"
        >
          بازگشت
        </button>
      </div>

      <Card>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="mb-2 block text-sm font-semibold">نام محصول *</label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({...formData, name: e.target.value})}
              className="w-full rounded-[var(--radius)] border border-[var(--border-light)] px-4 py-2.5 focus:border-[var(--primary)] focus:outline-none"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-semibold">توضیحات</label>
            <textarea
              rows={4}
              value={formData.description}
              onChange={(e) => setFormData({...formData, description: e.target.value})}
              className="w-full rounded-[var(--radius)] border border-[var(--border-light)] px-4 py-2.5 focus:border-[var(--primary)] focus:outline-none resize-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-2 block text-sm font-semibold">قیمت (تومان) *</label>
              <input
                type="number"
                required
                min="0"
                value={formData.price}
                onChange={(e) => setFormData({...formData, price: e.target.value})}
                className="w-full rounded-[var(--radius)] border border-[var(--border-light)] px-4 py-2.5 focus:border-[var(--primary)] focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-semibold">موجودی انبار *</label>
              <input
                type="number"
                required
                min="0"
                value={formData.stock}
                onChange={(e) => setFormData({...formData, stock: e.target.value})}
                className="w-full rounded-[var(--radius)] border border-[var(--border-light)] px-4 py-2.5 focus:border-[var(--primary)] focus:outline-none"
              />
            </div>
          </div>

          <div>
            <label className="mb-2 block text-sm font-semibold">دسته‌بندی *</label>
            <select
              required
              value={formData.category_id}
              onChange={(e) => setFormData({...formData, category_id: e.target.value})}
              className="w-full rounded-[var(--radius)] border border-[var(--border-light)] px-4 py-2.5 focus:border-[var(--primary)] focus:outline-none"
            >
              <option value="">انتخاب دسته‌بندی</option>
              {categories.map(cat => (
                <option key={cat.id} value={cat.id}>{cat.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-2 block text-sm font-semibold">تصاویر محصول</label>
            <div className="grid grid-cols-4 gap-4 mb-4">
              {formData.images.map((img, idx) => (
                <div key={idx} className="relative aspect-square rounded-[var(--radius)] overflow-hidden border border-[var(--border-light)]">
                  <img src={img} alt="Product" className="w-full h-full object-cover" />
                  <button
                    type="button"
                    onClick={() => removeImage(idx)}
                    className="absolute top-1 right-1 bg-red-500 text-white rounded-full p-1 hover:bg-red-600"
                  >
                    <X size={16} />
                  </button>
                </div>
              ))}
              {uploadingImages.map(idx => (
                <div key={idx} className="aspect-square rounded-[var(--radius)] border-2 border-dashed border-[var(--primary)] flex items-center justify-center">
                  <Loader2 className="animate-spin text-[var(--primary)]" size={24} />
                </div>
              ))}
              <label className="aspect-square rounded-[var(--radius)] border-2 border-dashed border-[var(--border-light)] flex flex-col items-center justify-center cursor-pointer hover:border-[var(--primary)] hover:bg-[var(--bg-muted)] transition">
                <Upload size={24} className="text-[var(--text-tertiary)] mb-2" />
                <span className="text-xs text-[var(--text-tertiary)]">آپلود عکس</span>
                <input
                  type="file"
                  accept="image/*"
                  multiple
                  onChange={handleImageUpload}
                  className="hidden"
                />
              </label>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-[var(--radius)] bg-[var(--primary)] py-3 font-bold text-white transition hover:bg-[var(--primary-dark)] disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="animate-spin" size={20} />
                در حال ذخیره...
              </>
            ) : (
              <>
                <Save size={20} />
                ذخیره تغییرات
              </>
            )}
          </button>
        </form>
      </Card>
    </div>
  );
}
