'use client';

import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 text-center">
      <div className="text-7xl font-extrabold text-[var(--primary)] mb-4">۴۰۴</div>
      <h1 className="text-2xl font-bold mb-2">صفحه‌ای که دنبالشی پیدا نشد</h1>
      <p className="text-[var(--text-secondary)] mb-8 max-w-md">
        یا لینک خرابه یا این صفحه دیگه وجود نداره.
      </p>
      <div className="flex gap-4">
        <Link
          href="/"
          className="rounded-lg bg-[var(--primary)] px-6 py-3 text-sm font-medium text-white transition hover:opacity-90"
        >
          صفحه اصلی
        </Link>
        <Link
          href="https://t.me/Foroshgrambot"
          className="rounded-lg border border-[var(--border-light)] bg-[var(--surface)] px-6 py-3 text-sm font-medium text-[var(--text)] transition hover:bg-[var(--hover-bg)]"
        >
          ربات فروشگرام
        </Link>
      </div>
    </div>
  );
}
