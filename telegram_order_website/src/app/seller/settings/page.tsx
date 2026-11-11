// ─── Seller Settings — change password & shop info ───
'use client';

import { useState, useEffect } from 'react';
import { Lock, KeyRound, Store } from 'lucide-react';
import toast from 'react-hot-toast';
import Card from '@/components/shared/Card';

interface ShopInfo {
  name?: string;
  username?: string;
}

export default function SellerSettingsPage() {
  const [shop, setShop] = useState<ShopInfo | null>(null);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch('/api/seller/shop-info')
      .then(r => r.json())
      .then(d => setShop(d))
      .catch(() => {});
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentPassword || !newPassword) {
      toast.error('همه فیلدها را پر کنید');
      return;
    }
    if (newPassword.length < 6) {
      toast.error('رمز جدید باید حداقل ۶ کاراکتر باشد');
      return;
    }
    if (newPassword !== confirmPassword) {
      toast.error('تکرار رمز جدید مطابقت ندارد');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch('/api/auth/change-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ currentPassword, newPassword }),
      });
      const data = await res.json();
      if (data.success) {
        toast.success('رمز عبور با موفقیت تغییر کرد ✅');
        setCurrentPassword('');
        setNewPassword('');
        setConfirmPassword('');
      } else {
        toast.error(data.error || 'خطا در تغییر رمز');
      }
    } catch {
      toast.error('خطا در ارتباط با سرور');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-black">تنظیمات</h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">
          {shop?.name ? `فروشگاه: ${shop.name}` : 'مدیریت تنظیمات فروشگاه شما'}
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-6">
          <div className="mb-5 flex items-center gap-2">
            <KeyRound className="h-5 w-5 text-[var(--primary)]" />
            <h2 className="font-bold">تغییر رمز عبور</h2>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-sm font-semibold">رمز فعلی</label>
              <div className="relative">
                <Lock className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-tertiary)]" />
                <input
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  className="w-full rounded-[var(--radius)] border border-[var(--border)] bg-white py-3 pr-10 pl-4 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                  placeholder="••••••••"
                  dir="ltr"
                  autoComplete="current-password"
                />
              </div>
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-semibold">رمز جدید</label>
              <div className="relative">
                <KeyRound className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-tertiary)]" />
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full rounded-[var(--radius)] border border-[var(--border)] bg-white py-3 pr-10 pl-4 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                  placeholder="حداقل ۶ کاراکتر"
                  dir="ltr"
                  autoComplete="new-password"
                />
              </div>
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-semibold">تکرار رمز جدید</label>
              <div className="relative">
                <KeyRound className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-tertiary)]" />
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full rounded-[var(--radius)] border border-[var(--border)] bg-white py-3 pr-10 pl-4 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                  placeholder="تکرار رمز جدید"
                  dir="ltr"
                  autoComplete="new-password"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="flex w-full items-center justify-center gap-2 rounded-[var(--radius-lg)] bg-blue-500 py-3 text-sm font-bold text-white transition-all hover:bg-blue-600 active:scale-[0.97] disabled:opacity-50"
            >
              {loading ? (
                <span className="animate-pulse">در حال ذخیره...</span>
              ) : (
                <>
                  تغییر رمز
                  <Lock className="h-4 w-4" />
                </>
              )}
            </button>
          </form>
        </Card>

        <Card className="p-6">
          <div className="mb-5 flex items-center gap-2">
            <Store className="h-5 w-5 text-[var(--primary)]" />
            <h2 className="font-bold">اطلاعات ورود</h2>
          </div>
          <div className="space-y-3 text-sm text-[var(--text-secondary)]">
            <div className="rounded-[var(--radius)] bg-gray-50 p-4">
              <p className="mb-1 text-xs font-semibold text-[var(--text-tertiary)]">نام کاربری ورود به سایت</p>
              <code className="text-base font-bold text-[var(--text)]" dir="ltr">
                {shop?.username || '—'}
              </code>
            </div>
            <p className="text-xs leading-relaxed">
              💡 نام کاربری شما همان شناسه تلگرام‌تان است. با آن و رمز عبور می‌توانید از طریق سایت وارد پنل شوید.
            </p>
            <p className="text-xs leading-relaxed">
              🔑 اگر رمز را فراموش کردید، از ربات با دستور <code className="rounded bg-gray-100 px-1.5 py-0.5 font-mono text-xs" dir="ltr">/reset_password</code> رمز موقت دریافت کنید.
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
}