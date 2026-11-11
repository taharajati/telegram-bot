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
  await new Promise(r => setTimeout(r, 300));

  // Hide chat messages initially for staggered reveal
  await p.evaluate(() => {
    const msgs = document.querySelectorAll('.chat .msg');
    msgs.forEach(m => {
      m.style.opacity = '0';
      m.querySelectorAll('.bubble, .avatar').forEach(el => { el.style.animationPlayState = 'paused'; });
    });
  });

  const fs = require('fs');
  const dir = 'T:/dars/projects/telegram/Telegramorderbot/ad-banner-frames3';
  if (!fs.existsSync(dir)) fs.mkdirSync(dir);

  const delay = ms => new Promise(r => setTimeout(r, ms));
  let frame = 0;
  const shot = async () => { await p.screenshot({ path: `${dir}/frame_${String(frame++).padStart(3, '0')}.png` }); };

  // Scene 1: badge + headline + timer enter (0-1.2s) — capture 14 frames @ ~11.7fps
  for (let i = 0; i < 14; i++) { await shot(); await delay(85); }

  // Scene 2: reveal chat messages one by one (staggered, ~0.35s each)
  const msgCount = await p.evaluate(() => document.querySelectorAll('.chat .msg').length);
  for (let i = 0; i < msgCount; i++) {
    await p.evaluate(idx => {
      const msgs = document.querySelectorAll('.chat .msg');
      const m = msgs[idx];
      m.style.opacity = '1';
      m.querySelectorAll('.bubble, .avatar').forEach(el => { el.style.animationPlayState = 'running'; });
    }, i);
    for (let j = 0; j < 4; j++) { await shot(); await delay(85); }
  }

  // Scene 3: connector line + cards + footer (hold through end)
  for (let i = 0; i < 16; i++) { await shot(); await delay(85); }

  await b.close();
  console.log(`DONE ${frame} frames`);
})();