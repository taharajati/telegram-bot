// src/lib/utils.ts
import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const numberFormat = new Intl.NumberFormat('fa-IR');

export function formatNumber(value: number | string | null | undefined): string {
  const n = Number(value ?? 0);
  return numberFormat.format(Number.isFinite(n) ? n : 0);
}

export function formatPrice(amount: number | string | null | undefined): string {
  return `${formatNumber(amount)} تومان`;
}

const dateFormat = new Intl.DateTimeFormat('fa-IR-u-ca-persian', {
  year: 'numeric',
  month: 'long',
  day: 'numeric',
});
const dateTimeFormat = new Intl.DateTimeFormat('fa-IR-u-ca-persian', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
});
const shortDateFormat = new Intl.DateTimeFormat('fa-IR-u-ca-persian', {
  month: 'short',
  day: 'numeric',
});

function toDate(value: string | Date | null | undefined): Date | null {
  if (!value) return null;
  const d = value instanceof Date ? value : new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

export function formatDate(value: string | Date | null | undefined): string {
  const d = toDate(value);
  return d ? dateFormat.format(d) : '—';
}

export function formatShortDate(value: string | Date | null | undefined): string {
  const d = toDate(value);
  return d ? shortDateFormat.format(d) : '—';
}

/** تاریخ و ساعت شمسی */
export function toJalali(value: string | Date | null | undefined): string {
  const d = toDate(value);
  return d ? dateTimeFormat.format(d) : '—';
}

/** ارقام فارسی/عربی را به لاتین و «ي/ك» عربی را به «ی/ک» تبدیل می‌کند. */
export function normalizeDigits(input: string): string {
  return input
    .replace(/[۰-۹]/g, (c) => String(c.charCodeAt(0) - 0x06f0))
    .replace(/[٠-٩]/g, (c) => String(c.charCodeAt(0) - 0x0660))
    .replace(/ي/g, 'ی')
    .replace(/ك/g, 'ک');
}

// ─── وضعیت سفارش ─────────────────────────────────────────
export type Tone = 'neutral' | 'brand' | 'success' | 'warning' | 'danger';

export const ORDER_STATUSES = [
  'pending_payment',
  'pending',
  'paid',
  'confirmed',
  'shipped',
  'delivered',
  'cancelled',
  'refunded',
] as const;

const STATUS_META: Record<string, { label: string; tone: Tone }> = {
  pending_payment: { label: 'در انتظار پرداخت', tone: 'warning' },
  pending: { label: 'در انتظار بررسی', tone: 'warning' },
  paid: { label: 'پرداخت شده', tone: 'brand' },
  confirmed: { label: 'تأیید شده', tone: 'brand' },
  shipped: { label: 'ارسال شده', tone: 'brand' },
  delivered: { label: 'تحویل داده شده', tone: 'success' },
  cancelled: { label: 'لغو شده', tone: 'danger' },
  refunded: { label: 'بازگشت وجه', tone: 'neutral' },
};

export function getStatusLabel(status: string): string {
  return STATUS_META[status]?.label ?? status;
}

export function getStatusTone(status: string): Tone {
  return STATUS_META[status]?.tone ?? 'neutral';
}

const PAYMENT_LABEL: Record<string, string> = {
  pending: 'در انتظار رسید',
  pending_review: 'رسید در انتظار بررسی',
  paid: 'پرداخت شده',
  cancelled: 'لغو شده',
};

export function getPaymentLabel(status: string | null | undefined): string {
  if (!status) return '—';
  return PAYMENT_LABEL[status] ?? status;
}

export function getPaymentTone(status: string | null | undefined): Tone {
  if (status === 'paid') return 'success';
  if (status === 'cancelled') return 'danger';
  return 'warning';
}

export function getPaymentMethodLabel(method: string | null | undefined): string {
  if (method === 'card_to_card') return 'کارت‌به‌کارت';
  return method || '—';
}

const ACTOR_LABEL: Record<string, string> = {
  system: 'سیستم',
  seller: 'فروشنده',
  seller_web: 'فروشنده (سایت)',
  admin: 'ادمین',
  admin_web: 'ادمین (سایت)',
  customer: 'مشتری',
  web: 'سایت',
};

export function getActorLabel(actor: string | null | undefined): string {
  if (!actor) return '—';
  return ACTOR_LABEL[actor] ?? actor;
}

/** آدرس تصویر محصول؛ مسیر API خودش محلی، تلگرام و placeholder را مدیریت می‌کند. */
export function productImageSrc(p: { id: number; image_url?: string | null; image_file_id?: string | null }): string | null {
  return p.image_url || p.image_file_id ? `/api/product-image/${p.id}` : null;
}

export const BOT_USERNAME = process.env.NEXT_PUBLIC_BOT_USERNAME || 'Foroshgrambot';
export const botUrl = (start?: string) =>
  `https://t.me/${BOT_USERNAME}${start ? `?start=${start}` : ''}`;
