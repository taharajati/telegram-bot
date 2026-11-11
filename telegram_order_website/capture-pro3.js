const puppeteer = require('puppeteer-core');
(async () => {
  const b = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: true,
    args: ['--no-sandbox']
  });
  const p = await b.newPage();
  await p.setViewport({ width: 1080, height: 1080 });
  await p.goto('file:///T:/dars/projects/telegram/Telegramorderbot/ad-banner-pro.html', { waitUntil: 'networkidle0' });
  await p.evaluateHandle('document.fonts.ready');
  await new Promise(r => setTimeout(r, 200));

  const fs = require('fs');
  const dir = 'T:/dars/projects/telegram/Telegramorderbot/ad-banner-frames4';
  if (!fs.existsSync(dir)) fs.mkdirSync(dir);

  const delay = ms => new Promise(r => setTimeout(r, ms));
  let frame = 0;
  const shot = async () => { await p.screenshot({ path: `${dir}/frame_${String(frame++).padStart(3, '0')}.png` }); };

  // Scene 1: badge + headline + timer (0 - 1.2s) — 16 frames @ 12fps
  for (let i = 0; i < 16; i++) { await shot(); await delay(83); }

  // Scene 2: phone+browser enter + messages reveal (1.2 - 3s) — 22 frames
  for (let i = 0; i < 22; i++) { await shot(); await delay(83); }

  // Scene 3: full scene + CTA pulse (3 - 4.5s) — 18 frames
  for (let i = 0; i < 18; i++) { await shot(); await delay(83); }

  await b.close();
  console.log(`DONE ${frame} frames`);
})();