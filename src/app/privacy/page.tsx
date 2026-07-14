import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'حریم خصوصی | فروشگرام',
  description: 'سیاست حفظ حریم خصوصی کاربران فروشگرام',
};

export default function PrivacyPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold mb-8 text-center">حریم خصوصی</h1>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">۱. اطلاعاتی که جمع‌آوری می‌کنیم</h2>
        <p className="leading-7 text-[var(--text-secondary)] mb-4">
          برای ارائهٔ خدمات، اطلاعات زیر را ذخیره می‌کنیم:
        </p>
        <ul className="list-disc pr-6 space-y-2 text-[var(--text-secondary)] leading-7">
          <li><strong>شناسه تلگرام</strong> — برای احراز هویت و ارسال نوتیفیکیشن</li>
          <li><strong>نام و نام خانوادگی</strong> — جهت درج در سفارش</li>
          <li><strong>شماره تماس</strong> — برای هماهنگی ارسال</li>
          <li><strong>آدرس</strong> — برای ارسال کالا</li>
          <li><strong>اطلاعات پرداخت</strong> — شماره کارت فروشنده و رسیدهای واریز (به‌صورت رمزگذاری‌شده)</li>
        </ul>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">۲. نحوهٔ استفاده از اطلاعات</h2>
        <p className="leading-7 text-[var(--text-secondary)]">
          اطلاعات شما صرفاً برای پردازش سفارش‌ها، ارسال نوتیفیکیشن و بهبود خدمات استفاده می‌شود.
          اطلاعات تماس شما در اختیار فروشندهٔ مرتبط با سفارش قرار می‌گیرد — نه بیشتر.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">۳. اشتراک‌گذاری اطلاعات</h2>
        <p className="leading-7 text-[var(--text-secondary)]">
          فروشگرام اطلاعات شما را به هیچ شخص ثالثی نمی‌فروشد. اطلاعات فقط در موارد قانونی (مثلاً حکم قضایی) 
          یا برای پردازش سفارش (اشتراک با فروشندهٔ مربوطه) منتشر می‌شود.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">۴. امنیت</h2>
        <p className="leading-7 text-[var(--text-secondary)]">
          رمز عبور فروشندگان با الگوریتم bcrypt هش می‌شود. ارتباط با سرور از طریق HTTPS رمزگذاری شده است.
          با این حال، هیچ روش ذخیره‌سازی در اینترنت ۱۰۰٪ امن نیست و ما نمی‌توانیم امنیت مطلق را تضمین کنیم.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">۵. حقوق شما</h2>
        <p className="leading-7 text-[var(--text-secondary)]">
          شما می‌توانید درخواست حذف حساب کاربری و اطلاعات خود را از طریق ربات تلگرام (دستور /support) ثبت کنید.
        </p>
      </section>

      <p className="text-sm text-[var(--text-muted)] text-center mt-12 border-t border-[var(--border-light)] pt-6">
        آخرین به‌روزرسانی: تیر ۱۴۰۵
      </p>
    </div>
  );
}
