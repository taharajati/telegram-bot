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
  await new Promise(r => setTimeout(r, 4300));
  await p.screenshot({ path: 'T:/dars/projects/telegram/Telegramorderbot/ad-banner-pro-preview.png' });
  await b.close();
  console.log('SHOT');
})();
