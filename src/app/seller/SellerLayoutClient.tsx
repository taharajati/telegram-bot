'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Store, ShoppingCart, LogOut, Package, ExternalLink, ChevronLeft } from 'lucide-react';
import toast from 'react-hot-toast';

interface Props { children: React.ReactNode }

export default function SellerLayoutClient({ children }: Props) {
  const router = useRouter();
  const pathname = typeof window !== 'undefined' ? window.location.pathname : '';
  const [ok, setOk] = useState(false);
  const [shopUrl, setShopUrl] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    fetch('/api/auth/me')
      .then(r => r.json())
      .then(d => {
        if (!d.authenticated || (d.role !== 'seller' && d.role !== 'admin')) {
          toast.error('دسترسی غیرمجاز');
          router.push('/login');
        } else {
          setOk(true);
          if (d.shopId) setShopUrl(`http://185.204.168.57/shop/${d.shopId}`);
        }
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

  const navItems = [
    { href: '/seller', icon: Store, label: 'داشبورد' },
    { href: '/seller/products', icon: Package, label: 'محصولات' },
    { href: '/seller/orders', icon: ShoppingCart, label: 'سفارش‌ها' },
  ];

  const isActive = (href: string) =>
    href === '/seller' ? pathname === '/seller' : pathname.startsWith(href);

  return (
    <div className="mx-auto flex max-w-7xl gap-6 px-4 py-6">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 bg-black/20 backdrop-blur-sm lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <aside className={`fixed inset-y-0 right-0 z-50 w-64 shrink-0 border-l border-[var(--border-light)] bg-white p-5 shadow-[var(--shadow-pop)] transition-transform lg:static lg:z-auto lg:block lg:w-56 lg:rounded-[var(--radius-xl)] lg:border lg:shadow-[var(--shadow-card)] ${
        sidebarOpen ? 'translate-x-0' : 'translate-x-full lg:translate-x-0'
      }`}>
        <div className="mb-5 flex items-center justify-between border-b border-[var(--border-light)] pb-4">
          <div className="flex items-center gap-2 font-extrabold">
            <Store className="h-5 w-5 text-[var(--primary)]" />
            فروشنده
          </div>
          <button onClick={() => setSidebarOpen(false)} className="lg:hidden text-[var(--text-tertiary)] hover:text-[var(--text)]">
            <ChevronLeft className="h-5 w-5" />
          </button>
        </div>

        <nav className="flex flex-col gap-1">
          {navItems.map(item => {
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
          {shopUrl && (
            <a
              href={shopUrl}
              target="_blank"
              className="mt-2 flex items-center gap-2 rounded-[var(--radius)] bg-[var(--primary-light)] px-3 py-2.5 text-sm font-medium text-[var(--primary)] transition hover:bg-[var(--primary)] hover:text-white"
            >
              <ExternalLink className="h-4 w-4" />
              لینک فروشگاه
            </a>
          )}
        </nav>

        <button
          onClick={logout}
          className="mt-5 flex w-full items-center gap-2.5 rounded-[var(--radius)] border border-[var(--border-light)] px-3 py-2.5 text-sm font-medium text-[var(--danger)] transition hover:bg-red-50"
        >
          <LogOut className="h-4 w-4" />
          خروج
        </button>
      </aside>

      <div className="min-w-0 flex-1">
        {/* Mobile top bar */}
        <div className="mb-4 flex items-center justify-between rounded-[var(--radius-xl)] border border-[var(--border-light)] bg-white px-4 py-3 shadow-[var(--shadow-card)] lg:hidden">
          <button onClick={() => setSidebarOpen(true)} className="flex items-center gap-2 text-sm font-bold">
            <Store className="h-4 w-4 text-[var(--primary)]" />
            پنل فروشنده
          </button>
          <button onClick={logout} className="text-sm font-medium text-[var(--danger)]">خروج</button>
        </div>
        {children}
      </div>
    </div>
  );
}
