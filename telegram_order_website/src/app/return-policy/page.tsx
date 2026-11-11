import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'قوانین بازگشت کالا | فروشگرام',
  description: 'شرایط و قوانین بازگشت کالا و مرجوعی در فروشگرام',
};

export default function ReturnPolicyPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold mb-8 text-center">قوانین بازگشت کالا</h1>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">۱. شرایط عمومی</h2>
        <p className="leading-7 text-[var(--text-secondary)]">
          هر فروشنده می‌تواند سیاست بازگشت مختص خود را داشته باشد. 
          موارد زیر حداقل‌هایی است که تمام فروشندگان ملزم به رعایت آن هستند.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">۲. مهلت بازگشت</h2>
        <p className="leading-7 text-[var(--text-secondary)]">
          مشتری تا ۷ روز پس از تحویل کالا فرصت دارد درخواست بازگشت را از طریق ربات تلگرام ثبت کند.
          پس از آن، بازگشت کالا منوط به توافق با فروشنده است.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">۳. شرایط بازگشت</h2>
        <ul className="list-disc pr-6 space-y-2 text-[var(--text-secondary)] leading-7">
          <li>کالا در شرایط اولیه خود باشد (پلمپ، بسته‌بندی، برچسب)</li>
          <li>کالا استفاده یا نصب نشده باشد</li>
          <li>مدارک خرید (کد رهگیری سفارش) ارائه شود</li>
        </ul>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">۴. استثناها</h2>
        <p className="leading-7 text-[var(--text-secondary)]">
          کالاهای زیر قابل بازگشت نیستند:
        </p>
        <ul className="list-disc pr-6 space-y-2 text-[var(--text-secondary)] leading-7">
          <li>کالاهای دیجیتال (فایل، نرم‌افزار، اشتراک)</li>
          <li>کالاهای شخصی (لباس زیر، محصولات آرایشی بهداشتی استفاده‌شده)</li>
          <li>کالاهای سفارشی/تولید شده به درخواست مشتری</li>
          <li>کالاهایی که آسیب فیزیکی دارند (ناشی از استفادهٔ نادرست)</li>
        </ul>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">۵. هزینه بازگشت</h2>
        <p className="leading-7 text-[var(--text-secondary)]">
          هزینهٔ ارسال برگشتی در صورت تأیید مشکل از طرف فروشنده بر عهدهٔ فروشنده است. 
          در غیر این صورت، هزینه بر عهدهٔ مشتری می‌باشد.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">۶. بازگشت وجه</h2>
        <p className="leading-7 text-[var(--text-secondary)]">
          پس از تأیید بازگشت کالا توسط فروشنده، وجه طی ۴۸ ساعت کاری به حساب مشتری بازگردانده می‌شود.
        </p>
      </section>

      <p className="text-sm text-[var(--text-muted)] text-center mt-12 border-t border-[var(--border-light)] pt-6">
        آخرین به‌روزرسانی: تیر ۱۴۰۵
      </p>
    </div>
  );
}
