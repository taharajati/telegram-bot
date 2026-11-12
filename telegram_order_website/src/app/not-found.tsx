import Link from 'next/link';
import { buttonStyles } from '@/components/ui/button';

export default function NotFound() {
  return (
    <main id="content" className="mx-auto flex min-h-[60vh] max-w-md flex-col items-center justify-center px-4 text-center">
      <p className="text-5xl font-extrabold tabular-nums text-brand">۴۰۴</p>
      <h1 className="mt-3 text-2xl font-extrabold">این صفحه پیدا نشد</h1>
      <p className="mt-2 text-sm text-ink-muted">آدرس را بررسی کن؛ ممکن است لینک اشتباه باشد یا فروشگاه یا محصول غیرفعال شده باشد.</p>
      <div className="mt-6 flex gap-3">
        <Link href="/" className={buttonStyles()}>صفحه‌ی اصلی</Link>
        <Link href="/shops" className={buttonStyles({ variant: 'secondary' })}>فهرست فروشگاه‌ها</Link>
      </div>
    </main>
  );
}
