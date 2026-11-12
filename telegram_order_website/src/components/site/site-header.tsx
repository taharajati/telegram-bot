import Link from 'next/link';
import { LayoutDashboard, Menu, Store } from 'lucide-react';
import { getSession } from '@/lib/auth';
import { buttonStyles } from '@/components/ui/button';
import { LogoutButton } from './logout-button';
import { Logo } from './logo';

const NAV = [
  { href: '/#how', label: 'نحوه‌ی کار' },
  { href: '/#features', label: 'امکانات' },
  { href: '/#pricing', label: 'پلن‌ها' },
  { href: '/shops', label: 'فروشگاه‌ها' },
  { href: '/about', label: 'درباره‌ی ما' },
];

export async function SiteHeader() {
  const session = await getSession().catch(() => null);
  const panel =
    session?.role === 'admin'
      ? { href: '/admin', label: 'پنل مدیریت', icon: LayoutDashboard }
      : session?.role === 'seller'
        ? { href: '/seller', label: 'پنل فروشنده', icon: Store }
        : null;

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-surface shadow-sticky">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
        <Logo />

        <nav aria-label="منوی اصلی" className="hidden items-center gap-1 md:flex">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="rounded-sm px-3 py-2 text-sm font-medium text-ink-muted transition-colors hover:bg-canvas hover:text-ink"
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          {panel ? (
            <>
              <Link href={panel.href} className={buttonStyles({ size: 'sm' })}>
                <panel.icon className="h-4 w-4" aria-hidden="true" />
                {panel.label}
              </Link>
              <LogoutButton className="hidden sm:inline-flex" />
            </>
          ) : (
            <Link href="/login" className={buttonStyles({ size: 'sm', variant: 'secondary' })}>
              ورود فروشندگان
            </Link>
          )}

          <details className="relative md:hidden">
            <summary
              className="inline-flex min-h-9 min-w-9 items-center justify-center rounded-sm border border-line-strong text-ink"
              aria-label="باز کردن منو"
            >
              <Menu className="h-5 w-5" aria-hidden="true" />
            </summary>
            <div className="absolute end-0 top-full mt-2 w-56 rounded-md border border-line bg-surface p-2 shadow-pop">
              {NAV.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="block rounded-sm px-3 py-3 text-sm font-medium text-ink hover:bg-canvas"
                >
                  {item.label}
                </Link>
              ))}
            </div>
          </details>
        </div>
      </div>
    </header>
  );
}
