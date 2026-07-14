'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { redirect } from 'next/navigation';
import Link from 'next/link';
import Header from '@/components/layout/Header';

interface Props {
  children: React.ReactNode;
  allowedRoles: string[];
}

export default function ProtectedLayout({ children, allowedRoles }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const [session, setSession] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/auth/me')
      .then(r => r.json())
      .then(data => {
        setSession(data);
        if (!data.authenticated || !allowedRoles.includes(data.role)) {
          router.push('/login');
        }
      })
      .catch(() => router.push('/login'))
      .finally(() => setLoading(false));
  }, [router, allowedRoles]);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-[var(--primary)] border-t-transparent" />
      </div>
    );
  }

  if (!session?.authenticated) return null;

  return (
    <div className="min-h-screen bg-[var(--bg)]">
      <Header />
      <main className="mx-auto min-h-[calc(100vh-8rem)] max-w-7xl px-4 py-6">
        {children}
      </main>
    </div>
  );
}