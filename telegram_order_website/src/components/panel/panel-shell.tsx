'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  BarChart3, CreditCard, ExternalLink, FolderTree, LayoutDashboard, Menu, Package, Settings, ShoppingCart,
  Store, Tag, Ticket, Users, X,
} from 'lucide-react';
import { Logo } from '@/components/site/logo';
import { LogoutButton } from '@/components/site/logout-button';
import { cn } from '@/lib/utils';

type Item = { href: string; label: string; icon: React.ElementType };

const NAV: Record<'admin' | 'seller', Item[]> = {
  seller: [
    { href: '/seller', label: 'داشبورد', icon: LayoutDashboard },
    { href: '/seller/orders', label: 'سفارش‌ها', icon: ShoppingCart },
    { href: '/seller/products', label: 'محصولات', icon: Package },
    { href: '/seller/discounts', label: 'کد تخفیف', icon: Tag },
    { href: '/seller/stats', label: 'آمار فروش', icon: BarChart3 },
    { href: '/seller/settings', label: 'تنظیمات', icon: Settings },
  ],
  admin: [
    { href: '/admin', label: 'داشبورد', icon: LayoutDashboard },
    { href: '/admin/shops', label: 'فروشگاه‌ها', icon: Store },
    { href: '/admin/orders', label: 'سفارش‌ها', icon: ShoppingCart },
    { href: '/admin/products', label: 'محصولات', icon: Package },
    { href: '/admin/categories', label: 'دسته‌بندی‌ها', icon: FolderTree },
    { href: '/admin/users', label: 'کاربران', icon: Users },
    { href: '/admin/claim-codes', label: 'کد دعوت', icon: Ticket },
    { href: '/admin/subscriptions', label: 'اشتراک‌ها', icon: CreditCard },
    { href: '/admin/settings', label: 'تنظیمات', icon: Settings },
  ],
};

export function PanelShell({
  variant,
  title,
  subtitle,
  publicHref,
  children,
}: {
  variant: 'admin' | 'seller';
  title: string;
  subtitle?: string;
  publicHref?: string;
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  // منو به مسیر فعلی وابسته است؛ با تغییر مسیر خودکار بسته می‌شود.
  const [openPath, setOpenPath] = useState<string | null>(null);
  const open = openPath === pathname;
  const setOpen = (value: boolean) => setOpenPath(value ? pathname : null);
  const root = `/${variant}`;

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpenPath(null);
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  const isActive = (href: string) => (href === root ? pathname === root : pathname.startsWith(href));

  const nav = (
    <nav aria-label="منوی پنل" className="flex flex-col gap-1">
      {NAV[variant].map((item) => {
        const active = isActive(item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? 'page' : undefined}
            className={cn(
              'flex min-h-11 items-center gap-3 rounded-sm px-3 text-sm font-medium transition-colors',
              active ? 'bg-brand-soft font-bold text-brand-strong' : 'text-ink-muted hover:bg-canvas hover:text-ink'
            )}
          >
            <item.icon className="h-4 w-4 shrink-0" aria-hidden="true" />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );

  const sidebarBody = (
    <div className="flex h-full flex-col gap-4">
      <div className="border-b border-line pb-4">
        <p className="truncate font-bold" title={title}>{title}</p>
        {subtitle && <p className="truncate text-xs text-ink-subtle">{subtitle}</p>}
      </div>
      {nav}
      <div className="mt-auto space-y-1 border-t border-line pt-4">
        {publicHref && (
          <a
            href={publicHref}
            target="_blank"
            rel="noopener noreferrer"
            className="flex min-h-11 items-center gap-3 rounded-sm px-3 text-sm font-medium text-ink-muted hover:bg-canvas hover:text-ink"
          >
            <ExternalLink className="h-4 w-4" aria-hidden="true" />
            مشاهده‌ی فروشگاه
          </a>
        )}
        <LogoutButton className="w-full justify-start" />
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-canvas">
      {/* نوار بالای موبایل */}
      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-line bg-surface px-4 py-2 lg:hidden">
        <Logo />
        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-label="باز کردن منوی پنل"
          aria-expanded={open}
          className="flex h-11 w-11 items-center justify-center rounded-sm border border-line-strong"
        >
          <Menu className="h-5 w-5" aria-hidden="true" />
        </button>
      </header>

      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button type="button" aria-label="بستن منو" className="absolute inset-0 bg-ink/40" onClick={() => setOpen(false)} />
          <aside className="absolute inset-y-0 end-0 flex w-72 max-w-[85vw] flex-col bg-surface p-4 shadow-pop">
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label="بستن منو"
              className="mb-2 flex h-11 w-11 items-center justify-center self-start rounded-sm hover:bg-canvas"
            >
              <X className="h-5 w-5" aria-hidden="true" />
            </button>
            {sidebarBody}
          </aside>
        </div>
      )}

      <div className="mx-auto flex max-w-7xl gap-6 px-4 py-6">
        <aside className="sticky top-6 hidden h-[calc(100vh-48px)] w-60 shrink-0 rounded-md border border-line bg-surface p-4 lg:block">
          <div className="mb-4"><Logo /></div>
          {sidebarBody}
        </aside>
        <main id="content" className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );
}
