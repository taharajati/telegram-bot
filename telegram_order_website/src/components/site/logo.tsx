import Link from 'next/link';
import { Send } from 'lucide-react';

export function Logo() {
  return (
    <Link href="/" className="inline-flex items-center gap-2 text-lg font-extrabold text-ink">
      <Send className="h-5 w-5 text-brand" aria-hidden="true" />
      فروشگرام
    </Link>
  );
}
