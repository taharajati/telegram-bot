import Link from 'next/link';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Card, CardTitle, DetailRow } from '@/components/ui/card';
import { PaymentBadge, StatusBadge } from '@/components/ui/badge';
import { Table, Td, Th, Truncate } from '@/components/ui/table';
import { buttonStyles } from '@/components/ui/button';
import { Select } from '@/components/ui/field';
import {
  cn, formatNumber, formatPrice, getActorLabel, getPaymentMethodLabel, getStatusLabel, ORDER_STATUSES, toJalali,
} from '@/lib/utils';
import type { HistoryEntry } from '@/lib/queries';

/* eslint-disable @typescript-eslint/no-explicit-any */

export function OrdersTable({ orders, basePath, caption }: { orders: any[]; basePath: string; caption: string }) {
  return (
    <Table caption={caption}>
      <thead>
        <tr>
          <Th>کد رهگیری</Th>
          <Th>مبلغ</Th>
          <Th>وضعیت</Th>
          <Th>پرداخت</Th>
          <Th>گیرنده</Th>
          <Th>تاریخ ثبت</Th>
          <Th><span className="sr-only">عملیات</span></Th>
        </tr>
      </thead>
      <tbody>
        {orders.map((o) => (
          <tr key={o.id} className="hover:bg-canvas">
            <Td className="font-mono text-xs font-semibold" dir="ltr"><bdi>{o.tracking_code}</bdi></Td>
            <Td className="font-bold tabular-nums">{formatPrice(o.total_price)}</Td>
            <Td><StatusBadge status={o.status} /></Td>
            <Td><PaymentBadge status={o.payment_status} /></Td>
            <Td className="text-ink-muted">{o.receiver_name ? <Truncate>{o.receiver_name}</Truncate> : '—'}</Td>
            <Td className="whitespace-nowrap text-ink-muted tabular-nums">{toJalali(o.created_at)}</Td>
            <Td>
              <Link href={`${basePath}/${o.id}`} className="font-semibold text-brand underline-offset-4 hover:underline">
                جزئیات<span className="sr-only"> سفارش {o.tracking_code}</span>
              </Link>
            </Td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

export function StatusFilter({ basePath, current }: { basePath: string; current?: string }) {
  const chip = (active: boolean) =>
    cn(
      'inline-flex min-h-9 items-center rounded-sm border px-3 text-sm font-medium transition-colors',
      active ? 'border-brand bg-brand-soft text-brand-strong' : 'border-line-strong bg-surface text-ink-muted hover:text-ink'
    );
  return (
    <div className="mb-4 flex flex-wrap gap-2" role="group" aria-label="فیلتر وضعیت سفارش">
      <Link href={basePath} className={chip(!current)} aria-current={!current ? 'true' : undefined}>همه</Link>
      {ORDER_STATUSES.map((s) => (
        <Link
          key={s}
          href={`${basePath}?status=${s}`}
          className={chip(current === s)}
          aria-current={current === s ? 'true' : undefined}
        >
          {getStatusLabel(s)}
        </Link>
      ))}
    </div>
  );
}

export function Pagination({
  basePath, page, pageCount, params = {},
}: { basePath: string; page: number; pageCount: number; params?: Record<string, string | undefined> }) {
  if (pageCount <= 1) return null;
  const href = (p: number) => {
    const sp = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) if (v) sp.set(k, v);
    if (p > 1) sp.set('page', String(p));
    const s = sp.toString();
    return s ? `${basePath}?${s}` : basePath;
  };
  return (
    <nav aria-label="صفحه‌بندی" className="mt-4 flex items-center justify-between gap-3">
      {page > 1 ? (
        <Link href={href(page - 1)} className={buttonStyles({ variant: 'secondary', size: 'sm' })}>
          <ChevronRight className="h-4 w-4" aria-hidden="true" /> قبلی
        </Link>
      ) : <span />}
      <span className="text-sm text-ink-muted tabular-nums">صفحه‌ی {formatNumber(page)} از {formatNumber(pageCount)}</span>
      {page < pageCount ? (
        <Link href={href(page + 1)} className={buttonStyles({ variant: 'secondary', size: 'sm' })}>
          بعدی <ChevronLeft className="h-4 w-4" aria-hidden="true" />
        </Link>
      ) : <span />}
    </nav>
  );
}

export function OrderDetailView({
  order, items, history, statusAction, extraRows,
}: {
  order: any;
  items: any[];
  history: HistoryEntry[];
  statusAction: string;
  extraRows?: React.ReactNode;
}) {
  const itemsTotal = items.reduce((sum, it) => sum + Number(it.unit_price) * Number(it.quantity), 0);
  const discount = Number(order.discount_amount || 0);

  return (
    <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
      <div className="space-y-6">
        <Card as="section">
          <CardTitle>اطلاعات سفارش</CardTitle>
          <dl className="mt-2">
            <DetailRow label="وضعیت"><StatusBadge status={order.status} /></DetailRow>
            <DetailRow label="پرداخت"><PaymentBadge status={order.payment_status} /></DetailRow>
            <DetailRow label="روش پرداخت">{getPaymentMethodLabel(order.payment_method)}</DetailRow>
            {order.payment_receipt_text && (
              <DetailRow label="شماره تراکنش"><bdi dir="ltr">{order.payment_receipt_text}</bdi></DetailRow>
            )}
            {order.payment_receipt_file_id && !order.payment_receipt_text && (
              <DetailRow label="رسید">عکس رسید در ربات تلگرام ثبت شده است</DetailRow>
            )}
            {order.payment_ref && <DetailRow label="شماره پیگیری"><bdi dir="ltr">{order.payment_ref}</bdi></DetailRow>}
            <DetailRow label="گیرنده">{order.receiver_name || '—'}</DetailRow>
            <DetailRow label="شماره تماس"><bdi dir="ltr">{order.phone || '—'}</bdi></DetailRow>
            <DetailRow label="آدرس">{order.shipping_address || '—'}</DetailRow>
            {order.customer_notes && <DetailRow label="توضیحات مشتری">{order.customer_notes}</DetailRow>}
            <DetailRow label="تاریخ ثبت"><span className="tabular-nums">{toJalali(order.created_at)}</span></DetailRow>
            {extraRows}
          </dl>
        </Card>

        <Card as="section">
          <CardTitle>اقلام سفارش</CardTitle>
          {items.length > 0 ? (
            <div className="mt-3">
              <Table caption="اقلام سفارش">
                <thead>
                  <tr><Th>محصول</Th><Th>تعداد</Th><Th>قیمت واحد</Th><Th>جمع</Th></tr>
                </thead>
                <tbody>
                  {items.map((it) => (
                    <tr key={it.id}>
                      <Td><Truncate max="max-w-56">{it.product_name}</Truncate></Td>
                      <Td className="tabular-nums">{formatNumber(it.quantity)}</Td>
                      <Td className="tabular-nums">{formatPrice(it.unit_price)}</Td>
                      <Td className="font-bold tabular-nums">{formatPrice(Number(it.unit_price) * Number(it.quantity))}</Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </div>
          ) : (
            <p className="mt-2 text-sm text-ink-muted">اقلام این سفارش ثبت نشده است.</p>
          )}
          <dl className="mt-3">
            <DetailRow label="جمع اقلام"><span className="tabular-nums">{formatPrice(itemsTotal)}</span></DetailRow>
            {discount > 0 && (
              <DetailRow label={`تخفیف${order.discount_code ? ` (${order.discount_code})` : ''}`}>
                <span className="tabular-nums">−{formatPrice(discount)}</span>
              </DetailRow>
            )}
            <DetailRow label="مبلغ سفارش"><span className="text-lg font-extrabold tabular-nums text-brand">{formatPrice(order.total_price)}</span></DetailRow>
          </dl>
        </Card>
      </div>

      <div className="space-y-6">
        <Card as="section">
          <CardTitle>تغییر وضعیت</CardTitle>
          <form action={statusAction} method="POST" className="mt-3 space-y-3">
            <label htmlFor="status" className="block text-sm font-semibold">وضعیت جدید</label>
            <Select id="status" name="status" defaultValue={order.status}>
              {ORDER_STATUSES.map((s) => <option key={s} value={s}>{getStatusLabel(s)}</option>)}
            </Select>
            <button type="submit" className={buttonStyles({ className: 'w-full' })}>ثبت وضعیت</button>
          </form>
        </Card>

        <Card as="section">
          <CardTitle>تاریخچه‌ی وضعیت</CardTitle>
          {history.length > 0 ? (
            <ol className="mt-3 space-y-3 border-s border-line-strong ps-4">
              {history.map((h, i) => (
                <li key={i} className="relative text-sm">
                  <span aria-hidden="true" className="absolute -start-[21px] top-2 h-2 w-2 rounded-full bg-brand" />
                  <p className="font-semibold">{getStatusLabel(h.status)}</p>
                  <p className="text-xs text-ink-subtle tabular-nums">
                    {toJalali(h.at)} · {getActorLabel(h.by)}
                  </p>
                  {h.description && <p className="text-xs text-ink-muted">{h.description}</p>}
                </li>
              ))}
            </ol>
          ) : (
            <p className="mt-2 text-sm text-ink-muted">هنوز تغییری در وضعیت ثبت نشده است.</p>
          )}
        </Card>
      </div>
    </div>
  );
}
