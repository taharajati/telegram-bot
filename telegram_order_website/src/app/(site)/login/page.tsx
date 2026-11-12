'use client';

import { useId, useState } from 'react';
import Link from 'next/link';
import { Eye, EyeOff } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Field, Input } from '@/components/ui/field';
import { botUrl, normalizeDigits } from '@/lib/utils';

export default function LoginPage() {
  const uid = useId();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [show, setShow] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const user = normalizeDigits(username).trim();
    if (!user || !password) {
      setError('نام کاربری و رمز عبور را وارد کن.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: user, password }),
      });
      const data = await res.json().catch(() => ({}));
      if (data.success) {
        window.location.href = data.role === 'admin' ? '/admin' : data.role === 'seller' ? '/seller' : '/';
        return;
      }
      setError(data.error || 'نام کاربری یا رمز عبور درست نیست. دوباره امتحان کن.');
    } catch {
      setError('ارتباط با سرور برقرار نشد. اینترنت را بررسی کن و دوباره تلاش کن.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-md px-4 py-12 md:py-20">
      <h1 className="text-2xl font-extrabold">ورود به پنل فروشگرام</h1>
      <p className="mt-1 text-sm text-ink-muted">فروشنده‌ها و مدیرها با نام کاربری و رمز عبور وارد می‌شوند.</p>

      <form onSubmit={onSubmit} noValidate className="mt-6 space-y-4 rounded-md border border-line bg-surface p-6">
        <Field id={`${uid}-u`} label="نام کاربری" hint="نام کاربری تلگرام (برای مدیر: شناسه‌ی عددی)">
          <Input
            id={`${uid}-u`}
            dir="ltr"
            inputMode="text"
            autoComplete="username"
            autoCapitalize="none"
            spellCheck={false}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            aria-invalid={!!error}
            aria-describedby={error ? `${uid}-err` : `${uid}-u-hint`}
          />
        </Field>

        <Field id={`${uid}-p`} label="رمز عبور">
          <div className="relative">
            <Input
              id={`${uid}-p`}
              dir="ltr"
              type={show ? 'text' : 'password'}
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              aria-invalid={!!error}
              aria-describedby={error ? `${uid}-err` : undefined}
              className="pe-12"
            />
            <button
              type="button"
              onClick={() => setShow((s) => !s)}
              aria-label={show ? 'پنهان کردن رمز' : 'نمایش رمز'}
              aria-pressed={show}
              className="absolute inset-y-0 end-0 flex w-11 items-center justify-center text-ink-muted hover:text-ink"
            >
              {show ? <EyeOff className="h-4 w-4" aria-hidden="true" /> : <Eye className="h-4 w-4" aria-hidden="true" />}
            </button>
          </div>
        </Field>

        {error && (
          <p id={`${uid}-err`} role="alert" className="rounded-sm border border-danger bg-danger-soft px-3 py-2 text-sm font-medium text-danger">
            {error}
          </p>
        )}

        <Button type="submit" size="lg" className="w-full" disabled={loading}>
          {loading ? 'در حال ورود…' : 'ورود'}
        </Button>
      </form>

      <p className="mt-4 text-sm text-ink-muted">
        نام کاربری و رمز را از بخش «تنظیمات سایت» ربات{' '}
        <a href={botUrl()} className="font-semibold text-brand underline-offset-4 hover:underline" dir="ltr">@Foroshgrambot</a>{' '}
        بگیر. رمز را فراموش کردی؟ دستور <bdi dir="ltr">/reset_password</bdi> رمز موقت می‌دهد.
      </p>
      <p className="mt-6">
        <Link href="/" className="text-sm font-semibold text-brand underline-offset-4 hover:underline">بازگشت به صفحه‌ی اصلی</Link>
      </p>
    </div>
  );
}
