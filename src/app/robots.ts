import type { MetadataRoute } from 'next';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: '*',
      allow: '/',
      disallow: ['/admin/', '/seller/', '/api/'],
    },
    sitemap: 'https://telegramorder.ir/sitemap.xml',
  };
}
