// ─── Foroshgram Landing — editorial, bold, non-generic ───
import Link from 'next/link';
import {
  ArrowLeft, Bot, CreditCard, BarChart3, ExternalLink, Repeat2, Shield,
  MessageCircle, Zap, ShoppingBag, Sparkles, TrendingUp, Store, ChevronLeft, Send
} from 'lucide-react';
import { getSiteContent, getActiveShops, getActiveProducts, getRecentActivity, getRecentActiveShops } from '@/lib/db';
import { formatPrice } from '@/lib/utils';

export const dynamic = 'force-dynamic';

const ICONS: Record<string, React.ElementType> = {
  bot: Bot, payment: CreditCard, dashboard: BarChart3,
  link: ExternalLink, history: Repeat2, security: Shield,
};

export default async function HomePage() {
  const [heroContent, featureContent, shops, products, recentActivity, recentShops] = await Promise.all([
    getSiteContent('hero').catch(() => ({})),
    getSiteContent('features').catch(() => ({})),
    getActiveShops().catch(() => []),
    getActiveProducts(4).catch(() => []),
    getRecentActivity(15).catch(() => []),
    getRecentActiveShops(5).catch(() => []),
  ]);

  const title = (heroContent as Record<string,string>).title || 'فروشگاه تلگرامیت رو در ۳ دقیقه راه بنداز';
  const subtitle = (heroContent as Record<string,string>).subtitle || 'فروشگرام هر کسب‌وکاری رو به فروشگاه آنلاین تبدیل می‌کنه.';

  const features: { title: string; desc: string; icon: string }[] = (() => {
    try {
      const raw = (featureContent as Record<string,string>).items;
      return raw ? JSON.parse(raw) : [
        { title: 'ربات اختصاصی', desc: 'هر فروشنده یه پنل اختصاصی توی تلگرام داره', icon: 'bot' },
        { title: 'پرداخت کارت‌به‌کارت', desc: 'واریز مستقیم به شماره کارت فروشنده', icon: 'payment' },
        { title: 'داشبورد هوشمند', desc: 'آمار فروش، تاریخچه سفارش‌ها', icon: 'dashboard' },
        { title: 'صفحه اختصاصی', desc: 'هر فروشنده یه لینک اختصاصی داره', icon: 'link' },
        { title: 'تاریخچه وضعیت', desc: 'از ثبت سفارش تا تحویل', icon: 'history' },
        { title: 'امنیت کامل', desc: 'داده‌ها روی سرور خودت', icon: 'security' },
      ];
    } catch { return []; }
  })();

  // Build ticker items from real data
  const tickerItems: { text: string; type: 'new' | 'paid' | 'shop' }[] = [];
  for (const a of recentActivity) {
    tickerItems.push({
      text: a.label,
      type: a.label === 'پرداخت کارت‌به‌کارت' ? 'paid' : 'new',
    });
  }
  for (const s of recentShops) {
    tickerItems.push({
      text: `فروشگاه "${s.name}" فعال شد`,
      type: 'shop',
    });
  }
  // Fallback if no real data
  const displayTicker = tickerItems.length > 0 ? tickerItems : [
    { text: 'سفارش جدید از فروشگاه کفش رضایی', type: 'new' as const },
    { text: 'پرداخت کارت‌به‌کارت انجام شد', type: 'paid' as const },
    { text: 'فروشگاه لبنیات سنتی فعال شد', type: 'shop' as const },
    { text: '۲ سفارش در حال بررسی', type: 'new' as const },
    { text: 'محصول جدید به پوشاک مدرن اضافه شد', type: 'new' as const },
  ];

  const dotClass = (type: string) =>
    type === 'paid' ? 'bg-green-500' :
    type === 'shop' ? 'bg-blue-500' : 'bg-amber-500';

  return (
    <div className="overflow-hidden">

      {/* ════════════════════════════════════════════
          HERO — anchored typography + living graphic
         ════════════════════════════════════════════ */}
      <section className="relative isolate px-4 pt-16 pb-6 md:pt-28 md:pb-12">
        {/* background atmosphere */}
        <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
          <div className="absolute -top-40 -right-40 h-96 w-96 rounded-full bg-[var(--primary)]/5 blur-3xl animate-blob" />
          <div className="absolute -bottom-40 -left-40 h-72 w-72 rounded-full bg-[var(--primary)]/3 blur-3xl animate-blob" style={{animationDelay:'-3s'}} />
        </div>

        <div className="mx-auto max-w-5xl">
          {/* badge */}
          <div className="mb-6 flex items-center gap-2 text-sm font-semibold text-blue-500">
            <Send className="h-5 w-5" />
            پلتفرم اتوماسیون فروش در تلگرام
          </div>

          {/* title — editorial scale */}
          <h1 className="max-w-3xl text-[clamp(2rem,6vw,4.5rem)] font-black leading-[1.08] tracking-tight">
            {title.split('در ۳ دقیقه').length > 1 ? (
              <>
                {title.split('در ۳ دقیقه')[0]}
                <span className="relative whitespace-nowrap text-blue-500">
                  <span className="relative z-10">در ۳ دقیقه</span>
                  <span className="absolute inset-x-0 bottom-1 h-3 rounded-full bg-blue-100 -z-10" />
                </span>
                {title.split('در ۳ دقیقه')[1]}
              </>
            ) : title}
          </h1>

          {/* subtitle */}
          <p className="mt-5 max-w-xl text-lg leading-relaxed text-[var(--text-secondary)] md:text-xl">
            {subtitle}
          </p>

          {/* CTA + stat */}
          <div className="mt-8 flex flex-wrap items-center gap-4">
            <Link
              href="/login"
              className="group inline-flex items-center gap-2 rounded-[var(--radius-lg)] bg-blue-500 px-7 py-3.5 font-bold text-white shadow-lg shadow-blue-500/20 transition-all hover:bg-blue-600 hover:shadow-xl hover:shadow-blue-500/25 active:scale-[0.97]"
            >
              شروع کن
              <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-0.5" />
            </Link>
            <Link
              href="/login"
              className="inline-flex items-center gap-1.5 rounded-[var(--radius-lg)] border border-[var(--border)] bg-white px-6 py-3.5 font-semibold text-[var(--text-secondary)] transition hover:border-blue-500 hover:text-blue-500"
            >
              ورود فروشنده‌ها
              <ChevronLeft className="h-4 w-4" />
            </Link>
          </div>

          {/* editorial note */}
          <p className="mt-6 text-sm text-[var(--text-tertiary)]">
            بدون نیاز به برنامه‌نویسی • مناسب کسب‌وکارهای کوچک و متوسط • رایگان برای شروع
          </p>
        </div>
      </section>

      {/* ════════════════════════════════════════════
          PROCESS — horizontal anchored steps
         ════════════════════════════════════════════ */}
      <section className="px-4 py-20 md:py-32">
        <div className="mx-auto max-w-5xl">
          {/* section label */}
          <div className="mb-4 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.15em] text-[var(--text-tertiary)]">
            <span className="h-px w-6 bg-[var(--border)]" />
            چطور کار می‌کنه
          </div>

          <div className="grid gap-0 md:grid-cols-3">
            {[
              { n: '۰۱', t: 'کد دعوت بگیر', d: 'از ادمین فروشگرام یه کد دعوت یک‌بارمصرف دریافت کن — فقط چند ثانیه.' },
              { n: '۰۲', t: 'فروشگاهت رو ثبت کن', d: 'توی ربات فروشگرام با چند تا سوال ساده، فروشگاه اختصاصی خودتو راه بنداز.' },
              { n: '۰۳', t: 'لینک بده و بفروش', d: 'محصولاتتو اضافه کن، لینک فروشگاهتو به مشتری‌ها بده و سفارش بگیر.' },
            ].map((s, i) => (
              <div key={s.n} className="group relative border-l border-[var(--border-light)] px-8 first:pr-0 last:border-l-0 last:pl-0">
                {i < 2 && (
                  <div className="absolute -left-[5px] top-3 h-2.5 w-2.5 rounded-full border-2 border-[var(--border)] bg-[var(--bg)] transition-colors group-hover:border-blue-500 max-md:hidden" />
                )}
                <div className="mb-3 font-mono text-3xl font-black text-blue-500/20 transition-colors group-hover:text-blue-500/40">
                  {s.n}
                </div>
                <h3 className="mb-2 text-lg font-bold">{s.t}</h3>
                <p className="text-sm leading-relaxed text-[var(--text-secondary)]">{s.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════════
          FEATURES — editorial alternating
         ════════════════════════════════════════════ */}
      <section className="bg-[var(--surface)] border-y border-[var(--border-light)] px-4 py-20 md:py-28">
        <div className="mx-auto max-w-5xl">
          <div className="mb-4 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.15em] text-[var(--text-tertiary)]">
            <span className="h-px w-6 bg-[var(--border)]" />
            قابلیت‌ها
          </div>
          <h2 className="mb-14 text-3xl font-black md:text-4xl">چرا فروشگرام؟</h2>

          <div className="space-y-6">
            {features.slice(0, 4).map((f, i) => {
              const Icon = ICONS[f.icon] || Sparkles;
              return (
                <div
                  key={i}
                  className="group flex items-start gap-5 rounded-[var(--radius-lg)] border border-transparent px-5 py-4 transition-all hover:border-[var(--border-light)] hover:bg-white hover:shadow-[var(--shadow-pop)]"
                >
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[var(--radius)] bg-blue-100 text-blue-600">
                    <Icon className="h-5 w-5" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="font-bold">{f.title}</h3>
                    <p className="mt-0.5 text-sm text-[var(--text-secondary)]">{f.desc}</p>
                  </div>
                  <ArrowLeft className="mr-auto mt-2 h-4 w-4 shrink-0 text-[var(--text-tertiary)] opacity-0 transition-all group-hover:opacity-100 group-hover:-translate-x-1" />
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════════
          LIVE TICKER — real data from orders + shops
         ════════════════════════════════════════════ */}
      <section className="border-b border-[var(--border-light)] bg-white py-10">
        <div className="mx-auto max-w-5xl px-4">
          <div className="mb-4 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.15em] text-[var(--text-tertiary)]">
            <span className="h-px w-6 bg-[var(--border)]" />
            آخرین فعالیت‌ها
          </div>
          <div className="relative overflow-hidden rounded-[var(--radius-xl)] border border-blue-100 bg-gradient-to-r from-blue-50/50 via-white to-blue-50/50 px-4 py-4">
            <div className="flex animate-marquee gap-12 whitespace-nowrap text-sm">
              {[...Array(3)].map((_, outer) => (
                <div key={outer} className="flex shrink-0 gap-12">
                  {displayTicker.map((item, idx) => (
                    <span key={`${outer}-${idx}`} className="inline-flex items-center gap-2.5 text-[var(--text-secondary)]">
                      <span className={`inline-flex h-2 w-2 rounded-full ${dotClass(item.type)}`} />
                      {item.text}
                    </span>
                  ))}
                </div>
              ))}
            </div>
          </div>
          <p className="mt-3 text-xs text-[var(--text-tertiary)]">
            {tickerItems.length > 0
              ? 'آمار واقعی از فروشگاه‌های فعال'
              : 'فعالیت‌های لحظه‌ای فروشگاه‌ها'}
          </p>
        </div>
      </section>

      {/* ════════════════════════════════════════════
          PRODUCT SHOWCASE (if any)
         ════════════════════════════════════════════ */}
      {products.length > 0 && (
        <section className="px-4 py-20 md:py-28">
          <div className="mx-auto max-w-5xl">
            <div className="mb-4 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.15em] text-[var(--text-tertiary)]">
              <span className="h-px w-6 bg-[var(--border)]" />
              جدیدترین محصولات
            </div>
            <div className="flex items-end justify-between mb-8">
              <h2 className="text-3xl font-black md:text-4xl">نمونه محصولات</h2>
              <span className="hidden text-sm text-[var(--text-tertiary)] sm:block">{products.length} محصول</span>
            </div>
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
              {products.map((p) => (
                <div key={p.id} className="group rounded-[var(--radius-xl)] border border-[var(--border-light)] bg-white p-5 shadow-[var(--shadow-card)] transition-all hover:shadow-[var(--shadow-pop)] hover:-translate-y-0.5">
                  <div className="mb-4 flex h-36 items-center justify-center rounded-[var(--radius)] bg-[var(--bg-muted)]">
                    {p.image_file_id ? (
                      <img src={`/api/product-image/${p.id}`} alt={p.name} className="h-full w-full rounded-[var(--radius)] object-cover" />
                    ) : (
                      <ShoppingBag className="h-10 w-10 text-[var(--text-tertiary)]" />
                    )}
                  </div>
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <h3 className="truncate font-bold">{p.name}</h3>
                      {p.category_name && <p className="text-xs text-[var(--text-tertiary)]">{p.category_name}</p>}
                    </div>
                    <span className="shrink-0 font-bold text-blue-600">{formatPrice(p.price)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ════════════════════════════════════════════
          ACTIVE SHOPS (if any)
         ════════════════════════════════════════════ */}
      {shops.length > 0 && (
        <section className="bg-[var(--surface)] border-y border-[var(--border-light)] px-4 py-20 md:py-28">
          <div className="mx-auto max-w-5xl">
            <div className="mb-4 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.15em] text-[var(--text-tertiary)]">
              <span className="h-px w-6 bg-[var(--border)]" />
              فروشگاه‌های فعال
            </div>
            <div className="flex items-end justify-between mb-8">
              <h2 className="text-3xl font-black md:text-4xl">فروشگاه‌های عضو</h2>
              <span className="hidden text-sm text-[var(--text-tertiary)] sm:block">{shops.length} فروشگاه</span>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {shops.map((s) => (
                <Link key={s.id} href={`/shop/${s.id}`} className="group rounded-[var(--radius-xl)] border border-[var(--border-light)] bg-white p-5 shadow-[var(--shadow-card)] transition-all hover:shadow-[var(--shadow-pop)] hover:-translate-y-0.5">
                  <div className="flex items-center gap-3.5">
                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-[var(--radius)] bg-blue-100 text-blue-600">
                      <span className="text-lg font-black">{s.name.charAt(0)}</span>
                    </div>
                    <div className="min-w-0">
                      <h3 className="truncate font-bold">{s.name}</h3>
                      <p className="truncate text-xs text-[var(--text-tertiary)]">{s.description || 'فروشگاه فعال'}</p>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ════════════════════════════════════════════
          TRUST ROW — compact, no cards
         ════════════════════════════════════════════ */}
      <section className="px-4 py-20 md:py-24">
        <div className="mx-auto max-w-5xl">
          <div className="mb-4 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.15em] text-[var(--text-tertiary)]">
            <span className="h-px w-6 bg-[var(--border)]" />
            چرا به ما اعتماد کنی؟
          </div>
          <div className="grid gap-6 md:grid-cols-3">
            {[
              { icon: Shield, t: 'پرداخت امن', d: 'کارت‌به‌کارت با شماره کارت فروشنده — واریز مستقیم و بدون واسطه' },
              { icon: MessageCircle, t: 'پشتیبانی تلگرامی', d: 'هر سوالی داشتی، مستقیم از پشتیبانی بپرس' },
              { icon: Repeat2, t: 'پیگیری شفاف', d: 'از لحظه ثبت سفارش تا تحویل، همه‌چیز قابل پیگیریه' },
            ].map((f) => (
              <div key={f.t} className="flex items-start gap-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[var(--radius)] bg-blue-100 text-blue-600">
                  <f.icon className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="font-bold">{f.t}</h3>
                  <p className="mt-0.5 text-sm leading-relaxed text-[var(--text-secondary)]">{f.d}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════════
          FINAL CTA — anchored block, not a gradient card
         ════════════════════════════════════════════ */}
      <section className="border-t border-[var(--border-light)] bg-[var(--surface)] px-4 py-20 md:py-28">
        <div className="mx-auto max-w-3xl text-center">
          <div className="mb-4 flex items-center justify-center gap-2 text-xs font-bold uppercase tracking-[0.15em] text-[var(--text-tertiary)]">
            <span className="h-px w-6 bg-[var(--border)]" />
            شروع کن
            <span className="h-px w-6 bg-[var(--border)]" />
          </div>
          <h2 className="text-3xl font-black md:text-5xl">همین حالا شروع کن</h2>
          <p className="mx-auto mt-4 mb-8 max-w-lg text-[var(--text-secondary)]">
            برای گرفتن کد دعوت، با ما در تلگرام تماس بگیر. تیم پشتیبانی ظرف چند دقیقه پاسخ میده.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-4">
            <Link
              href="/login"
              className="inline-flex items-center gap-2 rounded-[var(--radius-lg)] bg-blue-500 px-7 py-3.5 font-bold text-white shadow-lg shadow-blue-500/20 transition-all hover:bg-blue-600 hover:shadow-xl hover:shadow-blue-500/25 active:scale-[0.97]"
            >
              ورود به فروشگرام
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>

    </div>
  );
}
