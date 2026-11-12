import { cn, getPaymentLabel, getPaymentTone, getStatusLabel, getStatusTone, type Tone } from '@/lib/utils';

const tones: Record<Tone, string> = {
  neutral: 'bg-canvas text-ink-muted border-line',
  brand: 'bg-brand-soft text-brand-strong border-brand-soft',
  success: 'bg-success-soft text-success border-success-soft',
  warning: 'bg-warning-soft text-warning border-warning-soft',
  danger: 'bg-danger-soft text-danger border-danger-soft',
};

/** معنا فقط با رنگ منتقل نمی‌شود: متن همیشه همراه نشان است. */
export function Badge({
  tone = 'neutral',
  className,
  children,
}: {
  tone?: Tone;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-sm border px-2 py-0.5 text-xs font-semibold whitespace-nowrap',
        tones[tone],
        className
      )}
    >
      {children}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  return <Badge tone={getStatusTone(status)}>{getStatusLabel(status)}</Badge>;
}

export function PaymentBadge({ status }: { status: string | null | undefined }) {
  return <Badge tone={getPaymentTone(status)}>{getPaymentLabel(status)}</Badge>;
}
