// src/components/shared/Card.tsx
import { cn } from '@/lib/utils';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
}

export default function Card({ children, className, onClick }: CardProps) {
  return (
    <div
      className={cn(
        'rounded-[var(--radius-xl)] border border-[var(--border-light)] bg-white p-5 shadow-[var(--shadow-card)] transition-all',
        onClick && 'cursor-pointer hover:shadow-[var(--shadow-pop)] hover:-translate-y-0.5',
        className
      )}
      onClick={onClick}
    >
      {children}
    </div>
  );
}
