const puppeteer = require('puppeteer-core');
(async () => {
  const b = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: true,
    args: ['--no-sandbox']
  });
  const p = await b.newPage();
  await p.setViewport({ width: 1080, height: 1080 });
  await p.goto('file:///T:/dars/projects/telegram/Telegramorderbot/ad-banner-bot-site.html', { waitUntil: 'networkidle0' });
  await p.evaluateHandle('document.fonts.ready');
  await new Promise(r => setTimeout(r, 2600));
  const r = await p.evaluate(() => {
    const q = sel => {
      const el = document.querySelector(sel);
      if (!el) return null;
      const b = el.getBoundingClientRect();
      return { x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width), h: Math.round(b.height) };
    };
    const doc = document.documentElement;
    return {
      scrollW: doc.scrollWidth, scrollH: doc.scrollHeight,
      clientW: doc.clientWidth, clientH: doc.clientHeight,
      badge: q('.badge'), headline: q('.headline'), caption: q('.caption'),
      phone: q('.phone'), browser: q('.browser'), mockups: q('.mockups'),
      chatLast: q('.chat .msg:last-child'), replyRow: q('.reply-row'),
      siteFooter: q('.site-footer')
    };
  });
  console.log(JSON.stringify(r, null, 1));
  await b.close();
})();