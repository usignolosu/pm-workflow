/**
 * render_cards.js — 把 docs/cards/card-N.html 渲染成小红书格式图片
 *
 * 输出：docs/screenshots/card-N.png，750x1000 CSS px @ dsf1.44 => 1080x1440 (严格 3:4)
 * 特性：白底铺满、无圆角、无阴影（适合小红书整图发布）
 *
 * 依赖：puppeteer-core（已装在受管 node workspace）+ 系统 Google Chrome
 * 运行：
 *   NODE_PATH=$HOME/.workbuddy/binaries/node/workspace/node_modules \
 *   $HOME/.workbuddy/binaries/node/versions/22.22.2-3/bin/node scripts/render_cards.js
 */
const puppeteer = require('puppeteer-core');
const path = require('path');
const fs = require('fs');
const os = require('os');

const CHROME =
  process.env.CHROME_PATH ||
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

const ROOT = path.resolve(__dirname, '..', '..', '..', '..'); // scripts → skill → skills → .workbuddy → 工作区根
const CARDS = path.join(ROOT, 'docs', 'cards');
const OUT = path.join(ROOT, 'docs', 'screenshots');

const W = 750; // CSS px
const H = 1000; // 3:4
const DSF = 1.44; // 1080 x 1440

const OVERRIDE = `
  html,body{background:#FFFFFF !important;margin:0 !important;padding:0 !important}
  body{display:block !important}
  .deck{padding:0 !important;gap:0 !important}
  .card{width:${W}px !important;height:${H}px !important;min-height:${H}px !important;
        max-height:${H}px !important;margin:0 !important;border-radius:0 !important;
        box-shadow:none !important}
  .brand{margin-bottom:auto !important}
  .title{margin-top:0 !important}
  .footer{margin-top:auto !important}
`;

(async () => {
  if (!fs.existsSync(CHROME)) {
    console.error('✗ 未找到 Chrome：' + CHROME);
    process.exit(2);
  }
  fs.mkdirSync(OUT, { recursive: true });

  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: true,
    timeout: 30000,
    args: [
      '--no-sandbox',
      '--disable-gpu',
      '--disable-dev-shm-usage',
      '--no-first-run',
      '--no-default-browser-check',
      '--disable-extensions',
      '--use-gl=swiftshader',
      '--force-color-profile=srgb',
      '--disable-features=Translate,OptimizationHints',
      '--user-data-dir=' + path.join(os.tmpdir(), 'wb-cards-' + Date.now()),
    ],
  });

  try {
    const page = await browser.newPage();
    await page.setViewport({ width: W, height: H, deviceScaleFactor: DSF });

    for (let i = 1; i <= 8; i++) {
      const src = path.join(CARDS, `card-${i}.html`);
      const out = path.join(OUT, `card-${i}.png`);
      if (!fs.existsSync(src)) {
        console.error(`✗ 缺少源文件 ${src}`);
        continue;
      }
      await page.goto('file://' + src, { waitUntil: 'domcontentloaded', timeout: 15000 });
      await page.addStyleTag({ content: OVERRIDE });
      await new Promise((r) => setTimeout(r, 250));
      await page.screenshot({
        path: out,
        clip: { x: 0, y: 0, width: W, height: H },
      });
      console.log(`✓ card-${i}.png  ${Math.round(W * DSF)}x${Math.round(H * DSF)}  ${fs.statSync(out).size} B`);
    }
    console.log(`\n完成：8 张 → ${OUT}`);
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error('✗ 运行异常：', e.message);
  process.exit(1);
});
