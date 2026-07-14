'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import {
  LayoutDashboard, Store, Package, ShoppingCart, Users, LogOut, Ticket, ChevronLeft,
} from 'lucide-react';
import toast from 'react-hot-toast';

interface Props { children: React.ReactNode }

const NAV_ITEMS = [
  { href: '/admin', icon: LayoutDashboard, label: 'داشبورد' },
  { href: '/admin/shops', icon: Store, label: 'فروشگاه‌ها' },
  { href: '/admin/products', icon: Package, label: 'محصولات' },
  { href: '/admin/categories', icon: Package, label: 'دسته‌بندی‌ها' },
  { href: '/admin/claim-codes', icon: Ticket, label: 'کد دعوت' },
  { href: '/admin/orders', icon: ShoppingCart, label: 'سفارش‌ها' },
  { href: '/admin/users', icon: Users, label: 'کاربران' },
];

export default function AdminLayoutClient({ children }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const [ok, setOk] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    fetch('/api/auth/me')
      .then(r => r.json())
      .then(d => {
        if (!d.authenticated || d.role !== 'admin') {
          toast.error('دسترسی غیرمجاز');
          router.push('/login');
        } else setOk(true);
      })
      .catch(() => router.push('/login'));
  }, [router]);

  const logout = async () => {
    await fetch('/api/auth/logout', { method: 'POST' });
    router.push('/');
  };

  if (!ok) return (
    <div className="flex h-64 items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-3 border-[var(--primary)] border-t-transparent" />
    </div>
  );

  const isActive = (href: string) =>
    href === '/admin' ? pathname === '/admin' : pathname.startsWith(href);

  return (
    <div className="mx-auto flex max-w-7xl gap-6 px-4 py-6">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/20 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`fixed inset-y-0 right-0 z-50 w-64 shrink-0 border-l border-[var(--border-light)] bg-white p-5 shadow-[var(--shadow-pop)] transition-transform lg:static lg:z-auto lg:block lg:w-56 lg:rounded-[var(--radius-xl)] lg:border lg:shadow-[var(--shadow-card)] ${
        sidebarOpen ? 'translate-x-0' : 'translate-x-full lg:translate-x-0'
      }`}>
        {/* header */}
        <div className="mb-5 flex items-center justify-between border-b border-[var(--border-light)] pb-4">
          <div className="flex items-center gap-2 font-extrabold">
            <LayoutDashboard className="h-5 w-5 text-[var(--primary)]" />
            مدیریت
          </div>
          <button onClick={() => setSidebarOpen(false)} className="lg:hidden text-[var(--text-tertiary)] hover:text-[var(--text)]">
            <ChevronLeft className="h-5 w-5" />
          </button>
        </div>

        {/* nav */}
        <nav className="flex flex-col gap-1">
          {NAV_ITEMS.map(item => {
            const active = isActive(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setSidebarOpen(false)}
                className={`flex items-center gap-2.5 rounded-[var(--radius)] px-3 py-2.5 text-sm font-medium transition-all ${
                  active
                    ? 'bg-[var(--primary)] text-white shadow-sm'
                    : 'text-[var(--text-secondary)] hover:bg-[var(--bg-muted)]'
                }`}
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* logout */}
        <button
          onClick={logout}
          className="mt-5 flex w-full items-center gap-2.5 rounded-[var(--radius)] border border-[var(--border-light)] px-3 py-2.5 text-sm font-medium text-[var(--danger)] transition hover:bg-red-50"
        >
          <LogOut className="h-4 w-4" />
          خروج
        </button>
      </aside>

      {/* Main Content */}
      <div className="min-w-0 flex-1">
        {/* Mobile top bar */}
        <div className="mb-4 flex items-center justify-between rounded-[var(--radius-xl)] border border-[var(--border-light)] bg-white px-4 py-3 shadow-[var(--shadow-card)] lg:hidden">
          <button onClick={() => setSidebarOpen(true)} className="flex items-center gap-2 text-sm font-bold">
            <LayoutDashboard className="h-4 w-4 text-[var(--primary)]" />
            پنل مدیریت
          </button>
          <button onClick={logout} className="text-sm font-medium text-[var(--danger)]">خروج</button>
        </div>
        {children}
      </div>
    </div>
  );
}
