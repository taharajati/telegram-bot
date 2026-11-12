'use client';

import Link from 'next/link';
import { buttonStyles } from '@/components/ui/button';

export default function Error({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <main id="content" className="mx-auto flex min-h-[60vh] max-w-md flex-col items-center justify-center px-4 text-center">
      <h1 className="text-2xl font-extrabold">صفحه بارگذاری نشد</h1>
      <p className="mt-2 text-sm text-ink-muted">
        درخواست به سرور یا پایگاه داده کامل نشد. چند ثانیه بعد دوباره تلاش کن؛ اگر ادامه داشت از صفحه‌ی اصلی وارد شو.
      </p>
      <div className="mt-6 flex gap-3">
        <button type="button" onClick={reset} className={buttonStyles()}>تلاش دوباره</button>
        <Link href="/" className={buttonStyles({ variant: 'secondary' })}>صفحه‌ی اصلی</Link>
      </div>
    </main>
  );
}
