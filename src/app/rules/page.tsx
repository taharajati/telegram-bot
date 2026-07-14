import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'قوانین و مقررات | فروشگرام',
  description: 'قوانین استفاده از پلتفرم فروشگرام',
};

export default function RulesPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold mb-8 text-center">قوانین و مقررات</h1>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">۱. پذیرش قوانین</h2>
        <p className="leading-7 text-[var(--text-secondary)]">
          استفاده از پلتفرم فروشگرام به‌منزلهٔ پذیرش کامل تمامی قوانین و مقررات زیر است. 
          اگر با هر یک از بندها موافق نیستید، لطفاً از سرویس استفاده نکنید.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">۲. مسئولیت فروشنده</h2>
        <p className="leading-7 text-[var(--text-secondary)]">
          تمامی فروشندگان مستقل هستند و فروشگرام صرفاً بستر فنی ارائه می‌دهد. 
          فروشنده مسئول صحت اطلاعات محصول، قیمت‌گذاری، موجودی و ارسال به‌موقع سفارش است.
          فروشگرام هیچ‌گونه مسئولیتی در قالب محتوای محصولات یا عملکرد فروشنده ندارد.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">۳. مسئولیت مشتری</h2>
        <p className="leading-7 text-[var(--text-secondary)]">
          مشتری موظف است اطلاعات صحیح شامل نام، شماره تماس و آدرس را وارد کند.
          هرگونه سوءاستفاده از سیستم، تلاش برای نفوذ یا دورزدن امنیت پلتفرم ممنوع است.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">۴. کپی‌رایت</h2>
        <p className="leading-7 text-[var(--text-secondary)]">
          تمامی حقوق مادی و معنوی این پلتفرم متعلق به فروشگرام است. 
          کپی‌برداری از کد، طراحی یا محتوای سایت بدون اجازه ممنوع است.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">۵. تغییرات قوانین</h2>
        <p className="leading-7 text-[var(--text-secondary)]">
          فروشگرام حق تغییر این قوانین را در هر زمان دارد. آخرین به‌روزرسانی در پایین همین صفحه درج می‌شود.
        </p>
      </section>

      <p className="text-sm text-[var(--text-muted)] text-center mt-12 border-t border-[var(--border-light)] pt-6">
        آخرین به‌روزرسانی: تیر ۱۴۰۵
      </p>
    </div>
  );
}
