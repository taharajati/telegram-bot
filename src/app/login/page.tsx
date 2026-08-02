// ─── Foroshgram Login — username + password ───
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Lock, User, ArrowLeft, Store, ShieldCheck, Bot } from 'lucide-react';
import toast from 'react-hot-toast';
import Link from 'next/link';

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setError('نام کاربری و رمز عبور را وارد کنید.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username.trim(), password }),
      });
      const data = await res.json();
      if (data.success) {
        toast.success('خوش آمدید!');
        if (data.role === 'admin') {
          window.location.href = '/admin';
        } else if (data.role === 'seller') {
          window.location.href = '/seller';
        } else {
          window.location.href = '/';
        }
      } else {
        setError(data.error || 'نام کاربری یا رمز عبور اشتباه است');
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
          <Bot className="h-7 w-7" />
        </div>
        <h1 className="text-2xl font-black">ورود به فروشگرام</h1>
        <p className="mt-2 text-sm text-[var(--text-secondary)]">
          نام کاربری و رمز عبور خود را وارد کنید
        </p>
      </div>

      <form onSubmit={handleLogin} className="rounded-[var(--radius-xl)] border border-[var(--border-light)] bg-white p-6 shadow-[var(--shadow-pop)]">
        {error && (
          <div className="mb-4 rounded-[var(--radius)] border border-red-100 bg-red-50 px-4 py-2.5 text-center text-sm text-red-600">
            {error}
          </div>
        )}

        <div className="mb-4">
          <label className="mb-1.5 block text-sm font-semibold">نام کاربری</label>
          <div className="relative">
            <User className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-tertiary)]" />
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full rounded-[var(--radius)] border border-[var(--border)] bg-white py-3 pr-10 pl-4 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              placeholder="مثال: my_shop"
              dir="ltr"
              autoComplete="username"
            />
          </div>
        </div>

        <div className="mb-6">
          <label className="mb-1.5 block text-sm font-semibold">رمز عبور</label>
          <div className="relative">
            <Lock className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-tertiary)]" />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-[var(--radius)] border border-[var(--border)] bg-white py-3 pr-10 pl-4 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              placeholder="••••••••"
              dir="ltr"
              autoComplete="current-password"
            />
          </div>
          <p className="mt-2 text-xs text-[var(--text-tertiary)] leading-relaxed">
            💡 نام کاربری و رمز عبور خود را از بخش
            <span className="mx-1 inline-flex items-center gap-0.5 rounded bg-gray-100 px-1.5 py-0.5 font-semibold text-gray-700">
              ⚙️ تنظیمات سایت
            </span>
            در ربات
            <a href="https://t.me/Foroshgrambot" className="mx-1 text-[var(--primary)] hover:underline">@Foroshgrambot</a>
            دریافت یا تنظیم کنید.
          </p>
        </div>

        <button
          type="submit"
          disabled={loading}
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
            فروشنده → پنل فروش (نام کاربری + رمز)
          </div>
          <div className="flex items-center justify-center gap-2">
            <ShieldCheck className="h-3.5 w-3.5 text-blue-500" />
            ادمین → پنل مدیریت (نام کاربری + رمز)
          </div>
        </div>
      </form>

      {/* back to home */}
      <div className="mt-8 text-center">
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
