// پیش‌نمایش محلی یک ویجت تلگرام با state نمونه (فقط برای بررسی ظاهر؛ API واقعی نیست).
// اجرا:  node _preview_widget.js <widget.html> <state.json> <out.png>
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');
const puppeteer = require('puppeteer-core');

const [widget, stateFile, out] = process.argv.slice(2);
const html = fs.readFileSync(widget, 'utf8');
const state = fs.readFileSync(stateFile, 'utf8').trim();
const stub = `<style>:root{--tg-theme-bg-color:#fff;--tg-theme-text-color:#000;--tg-theme-hint-color:#707579;--tg-theme-link-color:#3390ec;--tg-theme-button-color:#3390ec;--tg-theme-button-text-color:#fff;--tg-theme-secondary-bg-color:#f1f1f4;--tg-theme-destructive-text-color:#e53935}body{font-family:system-ui,Tahoma}.bubble{width:340px;margin:14px;background:#fff;border-radius:16px;overflow:hidden}</style>
<script>window.TelegramWidget={chatData:${JSON.stringify(state)},HapticFeedback:{impactOccurred(){},notificationOccurred(){}},onEvent(){},ready(){},request:()=>Promise.resolve({result:null})}</script>`;
const page = `<!doctype html><meta charset="utf-8"><body style="margin:0;background:#cfd9e3"><div class="bubble">${stub}${html}</div></body>`;
const tmp = path.join(path.dirname(path.resolve(out)), '_widget_preview.html');
fs.writeFileSync(tmp, page);

(async () => {
  const browser = await puppeteer.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true });
  const p = await browser.newPage();
  await p.setViewport({ width: 400, height: 640 });
  await p.goto(pathToFileURL(tmp).href);
  await p.screenshot({ path: out });
  await browser.close();
  console.log('preview ->', out);
})();
