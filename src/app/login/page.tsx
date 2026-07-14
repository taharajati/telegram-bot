// ─── Foroshgram Login — clean, focused ───
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Send, Lock, ShieldCheck, User, Store, ArrowLeft } from 'lucide-react';
import toast from 'react-hot-toast';

export default function LoginPage() {
  const router = useRouter();
  const [telegramId, setTelegramId] = useState('');
  const [password, setPassword] = useState('');
  const [needsPassword, setNeedsPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!telegramId.trim()) { setError('شناسه تلگرام را وارد کنید.'); return; }
    setLoading(true);
    setError('');
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId: telegramId, password }),
      });
      const data = await res.json();
      if (data.success) {
        toast.success('خوش آمدید!');
        window.location.href = data.role === 'admin' ? '/admin' : data.role === 'seller' ? '/seller' : '/';
      } else {
        if (data.requirePassword) setNeedsPassword(true);
        setError(data.error || 'خطا در ورود');
      }
    } catch {
      setError('خطا در ارتباط با سرور');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-sm px-4 py-16 md:py-24">
      {/* branding */}
      <div className="mb-10 text-center">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-[var(--radius-xl)] bg-blue-500 text-white shadow-lg shadow-blue-500/15">
          <Send className="h-7 w-7" />
        </div>
        <h1 className="text-2xl font-black">ورود به فروشگرام</h1>
        <p className="mt-2 text-sm text-[var(--text-secondary)]">
          شناسه تلگرام خود را وارد کنید
        </p>
      </div>

      <form onSubmit={handleLogin} className="rounded-[var(--radius-xl)] border border-[var(--border-light)] bg-white p-6 shadow-[var(--shadow-pop)]">
        {error && (
          <div className="mb-4 rounded-[var(--radius)] border border-red-100 bg-red-50 px-4 py-2.5 text-center text-sm text-red-600">
            {error}
          </div>
        )}

        <div className="mb-4">
          <label className="mb-1.5 block text-sm font-semibold">شناسه تلگرام (Telegram ID)</label>
          <input
            type="text" inputMode="numeric"
            value={telegramId} onChange={(e) => setTelegramId(e.target.value)}
            className="w-full rounded-[var(--radius)] border border-[var(--border)] bg-white px-4 py-3 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            placeholder="مثال: 123456789"
            dir="ltr"
          />
        </div>

        {needsPassword && (
          <div className="mb-4 animate-appear">
            <label className="mb-1.5 block text-sm font-semibold">رمز عبور</label>
            <input
              type="password"
              value={password} onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-[var(--radius)] border border-[var(--border)] bg-white px-4 py-3 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              placeholder="••••••••"
              dir="ltr"
            />
            <p className="mt-1.5 text-xs text-[var(--text-tertiary)]">
              رمزت رو فراموش کردی؟ توی ربات <a href="https://t.me/Foroshgrambot" className="text-[var(--primary)] hover:underline">@Foroshgrambot</a> دستور <code className="rounded bg-gray-100 px-1 py-0.5 text-xs">/reset_password</code> رو بزن.
            </p>
          </div>
        )}

        <button
          type="submit" disabled={loading}
          className="flex w-full items-center justify-center gap-2 rounded-[var(--radius-lg)] bg-blue-500 py-3 text-sm font-bold text-white transition-all hover:bg-blue-600 active:scale-[0.97] disabled:opacity-50"
        >
          {loading ? (
            <span className="animate-pulse">در حال بررسی...</span>
          ) : (
            <>
              ورود
              <ArrowLeft className="h-4 w-4" />
            </>
          )}
        </button>

        {/* role legend */}
        <div className="mt-6 space-y-2 border-t border-[var(--border-light)] pt-5 text-xs text-[var(--text-tertiary)]">
          <div className="flex items-center justify-center gap-2">
            <Store className="h-3.5 w-3.5 text-blue-500" />
            فروشنده → پنل فروش (شناسه تلگرام + رمز)
          </div>
          <div className="flex items-center justify-center gap-2">
            <ShieldCheck className="h-3.5 w-3.5 text-blue-500" />
            ادمین → پنل مدیریت (شناسه + رمز)
          </div>
          <div className="flex items-center justify-center gap-2">
            <User className="h-3.5 w-3.5 text-[var(--text-tertiary)]" />
            مشتری → فقط سفارش‌های خود
          </div>
        </div>
      </form>
    </div>
  );
}