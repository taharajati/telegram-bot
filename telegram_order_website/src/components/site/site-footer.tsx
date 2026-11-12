import Link from 'next/link';
import { botUrl, BOT_USERNAME } from '@/lib/utils';
import { Logo } from './logo';

const LINKS = [
  { href: '/rules', label: 'قوانین و مقررات' },
  { href: '/privacy', label: 'حریم خصوصی' },
  { href: '/return-policy', label: 'بازگشت کالا' },
  { href: '/about', label: 'درباره‌ی ما' },
  { href: '/login', label: 'ورود فروشندگان' },
];

export function SiteFooter() {
  return (
    <footer className="border-t border-line bg-surface">
      <div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 md:grid-cols-[1fr_auto]">
        <div>
          <Logo />
          <p className="mt-2 max-w-sm text-sm text-ink-muted">
            فروشگاه تلگرامی با مدیریت خودکار سفارش، پرداخت کارت‌به‌کارت و پیگیری مشتری.
          </p>
          <p className="mt-3 text-sm text-ink-muted">
            پشتیبانی:{' '}
            <a href={botUrl()} className="font-semibold text-brand underline-offset-4 hover:underline" dir="ltr">
              @{BOT_USERNAME}
            </a>{' '}
            (دستور <bdi dir="ltr">/support</bdi>)
          </p>
        </div>
        <nav aria-label="پیوندهای پایین صفحه" className="flex flex-wrap gap-x-6 gap-y-2 text-sm md:max-w-xs md:justify-end">
          {LINKS.map((l) => (
            <Link key={l.href} href={l.href} className="py-1 text-ink-muted hover:text-brand">
              {l.label}
            </Link>
          ))}
        </nav>
      </div>
      <div className="border-t border-line py-4 text-center text-xs text-ink-subtle">
        فروشگرام — تمامی حقوق محفوظ است
      </div>
    </footer>
  );
}
