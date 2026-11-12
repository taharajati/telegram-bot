'use client';

import { useState } from 'react';
import { LogOut } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export function LogoutButton({ className, label = 'خروج' }: { className?: string; label?: string }) {
  const [pending, setPending] = useState(false);

  async function logout() {
    setPending(true);
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
    } finally {
      window.location.href = '/';
    }
  }

  return (
    <Button variant="ghost" size="sm" className={cn(className)} onClick={logout} disabled={pending}>
      <LogOut className="h-4 w-4" aria-hidden="true" />
      {pending ? 'در حال خروج…' : label}
    </Button>
  );
}
