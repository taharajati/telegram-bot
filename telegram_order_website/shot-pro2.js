const puppeteer = require('puppeteer-core');
(async () => {
  const b = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: true, args: ['--no-sandbox']
  });
  const p = await b.newPage();
  await p.setViewport({ width: 1080, height: 1080 });
  await p.goto('file:///T:/dars/projects/telegram/Telegramorderbot/ad-banner-pro.html', { waitUntil: 'networkidle0' });
  await p.evaluateHandle('document.fonts.ready');
  await new Promise(r => setTimeout(r, 4500));
  const vis = await p.evaluate(() => {
    const msgs = Array.from(document.querySelectorAll('.chat .msg'));
    return msgs.map(m => {
      const cs = getComputedStyle(m);
      const b = m.getBoundingClientRect();
      return { opacity: cs.opacity, visible: cs.opacity !== '0' && b.height > 0 };
    });
  });
  console.log('MSG VIS:', JSON.stringify(vis));
  await p.screenshot({ path: 'T:/dars/projects/telegram/Telegramorderbot/ad-banner-pro-preview2.png' });
  await b.close();
  console.log('SHOT');
})();