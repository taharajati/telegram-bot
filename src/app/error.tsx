'use client';

import Link from 'next/link';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="fa" dir="rtl">
      <body className="min-h-screen bg-[var(--bg)] text-[var(--text)] antialiased">
        <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 text-center">
          <div className="text-7xl font-extrabold text-red-500 mb-4">۵۰۰</div>
          <h1 className="text-2xl font-bold mb-2">خطای سرور</h1>
          <p className="text-[var(--text-secondary)] mb-8 max-w-md">
            یه اشکالی پیش اومده! تیم فنی در جریان هست.
          </p>
          <div className="flex gap-4">
            <button
              onClick={reset}
              className="rounded-lg bg-[var(--primary)] px-6 py-3 text-sm font-medium text-white transition hover:opacity-90"
            >
              تلاش مجدد
            </button>
            <Link
              href="/"
              className="rounded-lg border border-[var(--border-light)] bg-[var(--surface)] px-6 py-3 text-sm font-medium text-[var(--text)] transition hover:bg-[var(--hover-bg)]"
            >
              صفحه اصلی
            </Link>
          </div>
        </div>
      </body>
    </html>
  );
}
