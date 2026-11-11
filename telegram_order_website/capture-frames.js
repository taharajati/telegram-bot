const puppeteer = require('puppeteer-core');

(async () => {
  const browser = await puppeteer.launch({
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu']
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1080, height: 1080, deviceScaleFactor: 1 });
  
  const fileUrl = 'file:///T:/dars/projects/telegram/Telegramorderbot/ad-banner-gif.html';
  await page.goto(fileUrl, { waitUntil: 'networkidle0' });
  
  // Wait for font
  await page.evaluateHandle('document.fonts.ready');
  await new Promise(r => setTimeout(r, 500));
  
  const framesDir = 'T:/dars/projects/telegram/Telegramorderbot/ad-banner-frames';
  const fs = require('fs');
  if (!fs.existsSync(framesDir)) fs.mkdirSync(framesDir);
  
  // Capture 40 frames over 4 seconds
  for (let i = 0; i < 40; i++) {
    await page.screenshot({ path: `${framesDir}/frame_${String(i).padStart(3,'0')}.png` });
    await new Promise(r => setTimeout(r, 100));
  }
  
  await browser.close();
  console.log('DONE: 40 frames captured');
})();