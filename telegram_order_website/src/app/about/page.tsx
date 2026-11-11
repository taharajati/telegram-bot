import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'درباره ما | فروشگرام',
  description: 'درباره پلتفرم فروشگرام — اتوماسیون فروش در تلگرام',
};

export default function AboutPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold mb-8 text-center">درباره فروشگرام</h1>

      <section className="mb-8">
        <p className="leading-7 text-[var(--text-secondary)] mb-6">
          فروشگرام یک پلتفرم چندمستأجری (Multi-Tenant) است که به فروشندگان اجازه می‌دهد 
          فروشگاه آنلاین خود را در تلگرام راه‌اندازی کنند. 
          هر فروشنده ربات اختصاصی خود را دارد، محصولاتش را مدیریت می‌کند، 
          و مشتری‌ها از طریق ربات سفارش می‌دهند و پرداخت می‌کنند.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">چطور کار می‌کند؟</h2>
        <ol className="list-decimal pr-6 space-y-3 text-[var(--text-secondary)] leading-7">
          <li><strong>ثبت‌نام:</strong> فروشنده از طریق ربات در ۴ مرحله فروشگاه خود را ثبت می‌کند</li>
          <li><strong>تأیید:</strong> پس از تأیید ادمین، لینک فروشگاه فعال می‌شود</li>
          <li><strong>مدیریت:</strong> فروشنده محصولات، دسته‌بندی‌ها و سفارش‌ها را از ربات یا سایت مدیریت می‌کند</li>
          <li><strong>فروش:</strong> مشتری‌ها از طریق لینک تلگرام وارد می‌شوند، خرید می‌کنند و پرداخت انجام می‌دهند</li>
        </ol>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">ارتباط با ما</h2>
        <div className="space-y-3 text-[var(--text-secondary)] leading-7">
          <p>
            📱 <strong>ربات تلگرام:</strong>{' '}
            <a href="https://t.me/Foroshgrambot" className="text-[var(--accent)] hover:underline">@Foroshgrambot</a>
          </p>
          <p>
            💬 <strong>پشتیبانی:</strong> از طریق ربات تلگرام (دستور /support)
          </p>
        </div>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">اینماد</h2>
        <p className="leading-7 text-[var(--text-secondary)]">
          فروشگرام در فرآیند اخذ نماد اعتماد الکترونیکی (اینماد) قرار دارد.
        </p>
      </section>
    </div>
  );
}
