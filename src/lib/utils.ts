// src/lib/utils.ts
import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatPrice(amount: number): string {
  return `${amount.toLocaleString('fa-IR')} تومان`;
}

export function toJalali(dateStr: string): string {
  // تبدیل ساده: فقط date part را نمایش می‌دهیم
  try {
    const d = new Date(dateStr);
    // استفاده از تقویم جلالی با Intl
    const formatter = new Intl.DateTimeFormat('fa-IR-u-ca-persian', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
    return formatter.format(d);
  } catch {
    return dateStr.substring(0, 16);
  }
}

export function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    pending_payment: '⏳ در انتظار پرداخت',
    pending: '⏳ در انتظار بررسی',
    paid: '✅ پرداخت شده',
    confirmed: '✅ تأیید شده',
    shipped: '🚚 ارسال شده',
    delivered: '📦 تحویل داده شده',
    cancelled: '❌ لغو شده',
    refunded: '↩️ بازگشت وجه',
  };
  return labels[status] || status;
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    pending_payment: 'bg-amber-900/50 text-amber-300 border-amber-800',
    pending: 'bg-amber-900/50 text-amber-300 border-amber-800',
    paid: 'bg-emerald-900/50 text-emerald-300 border-emerald-800',
    confirmed: 'bg-emerald-900/50 text-emerald-300 border-emerald-800',
    shipped: 'bg-blue-900/50 text-blue-300 border-blue-800',
    delivered: 'bg-emerald-900/50 text-emerald-300 border-emerald-800',
    cancelled: 'bg-red-900/50 text-red-300 border-red-800',
    refunded: 'bg-purple-900/50 text-purple-300 border-purple-800',
  };
  return colors[status] || 'bg-slate-800 text-slate-300 border-slate-700';
}
