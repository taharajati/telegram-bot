import { SiteHeader } from '@/components/site/site-header';
import { SiteFooter } from '@/components/site/site-footer';

export default function SiteLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <a
        href="#content"
        className="sr-only focus:not-sr-only focus:fixed focus:start-4 focus:top-4 focus:z-50 focus:rounded-sm focus:bg-surface focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-brand"
      >
        پرش به محتوا
      </a>
      <SiteHeader />
      <main id="content" className="min-h-[60vh]">
        {children}
      </main>
      <SiteFooter />
    </>
  );
}
