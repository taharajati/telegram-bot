import { cn } from '@/lib/utils';

/** کارت هم‌سطح با مرز ۱ پیکسلی؛ بدون سایه. */
export function Card({
  className,
  children,
  as: Tag = 'div',
}: {
  className?: string;
  children: React.ReactNode;
  as?: 'div' | 'section' | 'article';
}) {
  return (
    <Tag className={cn('rounded-md border border-line bg-surface p-5', className)}>{children}</Tag>
  );
}

export function CardTitle({ children, className }: { children: React.ReactNode; className?: string }) {
  return <h2 className={cn('text-base font-bold text-ink', className)}>{children}</h2>;
}

/** ردیف «برچسب: مقدار» برای جزئیات. */
export function DetailRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-line py-3 text-sm last:border-b-0">
      <dt className="shrink-0 text-ink-subtle">{label}</dt>
      <dd className="min-w-0 text-end font-medium text-ink break-words">{children}</dd>
    </div>
  );
}
