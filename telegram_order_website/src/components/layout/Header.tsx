'use client';

import Link from 'next/link';
import { useState, useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { Zap, LogOut, LayoutDashboard, Store, ShoppingBag, User, ChevronDown } from 'lucide-react';
import toast from 'react-hot-toast';

interface Session {
  authenticated: boolean;
  userId?: number;
  role?: string;
  shopId?: number;
  firstName?: string;
}

const ROLE_LINKS: Record<string, { label: string; href: string; icon: React.ElementType }> = {
  admin: { label: 'پنل مدیریت', href: '/admin', icon: LayoutDashboard },
  seller: { label: 'پنل فروشنده', href: '/seller', icon: Store },
  customer: { label: 'پیگیری سفارش', href: '/orders', icon: ShoppingBag },
};

export default function Header() {
  const router = useRouter();
  const pathname = usePathname();
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [menuOpen, setMenuOpen] = useState(false);

  const fetchSession = async () => {
    try {
      const res = await fetch('/api/auth/me');
      if (!res.ok) { setSession(null); return; }
      const data = await res.json();
      setSession(data);
    } catch { setSession(null); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchSession(); }, [pathname]);

  const handleLogout = async () => {
    await fetch('/api/auth/logout', { method: 'POST' });
    setSession(null);
    toast.success('خروج موفق');
    router.push('/');
    router.refresh();
  };

  const roleInfo = session?.authenticated && session.role ? ROLE_LINKS[session.role] : null;

  return (
    <header className="sticky top-0 z-50 border-b border-[var(--border-light)] bg-[var(--bg-navbar)] backdrop-blur-lg">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3.5">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 text-lg font-extrabold tracking-tight">
          <span className="flex h-8 w-8 items-center justify-center rounded-[var(--radius)] bg-[var(--primary)] text-white">
            <Zap className="h-4 w-4" />
          </span>
          فروشگرام
        </Link>

        {/* Navigation */}
        <nav className="flex items-center gap-2 text-sm font-medium">
          {loading ? (
            <div className="h-9 w-24 animate-pulse rounded-[var(--radius)] bg-[var(--bg-muted)]" />
          ) : session?.authenticated && roleInfo ? (
            <div className="flex items-center gap-2">
              <span className="hidden items-center gap-1.5 text-xs text-[var(--text-secondary)] sm:flex">
                <User className="h-3.5 w-3.5" />
                {session.firstName || `شناسه ${session.userId}`}
              </span>
              <Link
                href={roleInfo.href}
                className="inline-flex items-center gap-1.5 rounded-[var(--radius)] bg-[var(--primary)] px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-[var(--primary-dark)] active:scale-[0.97]"
              >
                <roleInfo.icon className="h-4 w-4" />
                {roleInfo.label}
              </Link>
              <button
                onClick={handleLogout}
                className="inline-flex items-center gap-1.5 rounded-[var(--radius)] border border-[var(--border)] bg-white px-3 py-2 text-sm text-[var(--text-secondary)] transition-all hover:border-red-200 hover:text-red-500 active:scale-[0.97]"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <Link
              href="/login"
              className="inline-flex items-center gap-1.5 rounded-[var(--radius)] bg-[var(--primary)] px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-[var(--primary-dark)] active:scale-[0.97]"
            >
              ورود به فروشگرام
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
