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
  await new Promise(r => setTimeout(r, 400));

  // Hide all chat messages first, then reveal them one by one
  await p.evaluate(() => {
    const msgs = document.querySelectorAll('.chat .msg');
    msgs.forEach(m => { m.style.opacity = '0'; m.style.transform = 'translateY(12px)'; m.style.transition = 'opacity .4s ease, transform .4s ease'; });
  });

  const fs = require('fs');
  const dir = 'T:/dars/projects/telegram/Telegramorderbot/ad-banner-frames2';
  if (!fs.existsSync(dir)) fs.mkdirSync(dir);

  const delay = ms => new Promise(r => setTimeout(r, ms));
  let frame = 0;
  const shot = async () => { await p.screenshot({ path: `${dir}/frame_${String(frame++).padStart(3, '0')}.png` }); };

  // Scene 1: headline & mockups enter (0.0 - 0.8s) — 8 frames @ 10fps
  for (let i = 0; i < 8; i++) { await shot(); await delay(100); }

  // Scene 2: reveal chat messages one by one (~0.4s each)
  const msgCount = await p.evaluate(() => document.querySelectorAll('.chat .msg').length);
  for (let i = 0; i < msgCount; i++) {
    await p.evaluate(idx => {
      const msgs = document.querySelectorAll('.chat .msg');
      msgs[idx].style.opacity = '1';
      msgs[idx].style.transform = 'translateY(0)';
    }, i);
    for (let j = 0; j < 4; j++) { await shot(); await delay(100); }  // 4 frames per message
  }

  // Scene 3: hold final (1.2s)
  for (let i = 0; i < 12; i++) { await shot(); await delay(100); }

  await b.close();
  console.log(`DONE ${frame} frames`);
})();