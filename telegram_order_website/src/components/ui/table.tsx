import { cn } from '@/lib/utils';

/** جدول با اسکرول افقی در عرض کم؛ `caption` برای صفحه‌خوان. */
export function Table({
  caption,
  children,
  className,
}: {
  caption: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className="overflow-x-auto rounded-md border border-line bg-surface">
      <table className={cn('w-full min-w-[640px] text-sm', className)}>
        <caption className="sr-only">{caption}</caption>
        {children}
      </table>
    </div>
  );
}

export function Th({ className, ...props }: React.ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      scope="col"
      className={cn('border-b border-line bg-canvas px-4 py-3 text-start text-xs font-semibold text-ink-muted', className)}
      {...props}
    />
  );
}

export function Td({ className, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return <td className={cn('border-b border-line px-4 py-3 align-middle text-ink', className)} {...props} />;
}

/** متن بلند را کوتاه می‌کند و کامل آن را در tooltip نشان می‌دهد. */
export function Truncate({ children, max = 'max-w-48' }: { children: string; max?: string }) {
  return (
    <span className={cn('block truncate', max)} title={children}>
      {children}
    </span>
  );
}
