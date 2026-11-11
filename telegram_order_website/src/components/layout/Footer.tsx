import Link from 'next/link';
import { Zap, Sparkles } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="border-t border-[var(--border-light)] bg-white py-12">
      <div className="mx-auto max-w-5xl px-4">
        <div className="flex flex-col items-center justify-between gap-6 text-center md:flex-row md:text-right">
          {/* branding */}
          <div>
            <Link href="/" className="inline-flex items-center gap-2 text-base font-extrabold">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--primary)] text-white">
                <Zap className="h-3.5 w-3.5" />
              </span>
              فروشگرام
            </Link>
            <p className="mt-2 max-w-xs text-sm leading-relaxed text-[var(--text-secondary)]">
              پلتفرم اتوماسیون فروش در تلگرام. فروشگاهت رو راه بنداز، سفارش‌ها رو خودکار مدیریت کن، پول رو آنلاین بگیر.
            </p>
          </div>

          {/* links */}
          <div className="flex flex-wrap justify-center gap-x-6 gap-y-2 text-sm">
            <Link href="/rules" className="text-[var(--text-secondary)] transition hover:text-[var(--primary)]">قوانین</Link>
            <Link href="/privacy" className="text-[var(--text-secondary)] transition hover:text-[var(--primary)]">حریم خصوصی</Link>
            <Link href="/return-policy" className="text-[var(--text-secondary)] transition hover:text-[var(--primary)]">بازگشت کالا</Link>
            <Link href="/about" className="text-[var(--text-secondary)] transition hover:text-[var(--primary)]">درباره ما</Link>
            <Link href="/login" className="text-[var(--text-secondary)] transition hover:text-[var(--primary)]">ورود</Link>
            <span className="text-[var(--text-tertiary)]">پشتیبانی: @ForoshgramBot</span>
          </div>
        </div>

        <div className="mt-8 border-t border-[var(--border-light)] pt-6 text-center text-xs text-[var(--text-tertiary)]">
          فروشگرام &mdash; تمامی حقوق محفوظ است &copy; {new Date().getFullYear()}
        </div>
      </div>
    </footer>
  );
}
