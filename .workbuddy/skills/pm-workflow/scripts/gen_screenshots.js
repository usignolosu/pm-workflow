#!/usr/bin/env node
'use strict';
/*
 * gen_screenshots.js — 将高保真原型(HTML)渲染为页面截图(PNG)，供 PRD §6 嵌入。
 *
 * 用法：
 *   node gen_screenshots.js --html ./prototype/index.html --out ./screenshots
 *   node gen_screenshots.js --html ./prototype/index.html --out ./screenshots \
 *        --screens screens.json          # 自定义每个屏的触发方式
 *   node gen_screenshots.js --html ./prototype/index.html --out ./screenshots \
 *        --width 390 --height 844 --scale 2 --wait 700
 *
 * screens.json 格式（可选，缺省自动探测 <section id>）：
 *   [ {"name":"home","trigger":"go('home')"},
 *     {"name":"game-hard","trigger":"go('game',{mode:'hard'})"} ]
 * 说明：trigger 是在页面上下文执行的 JS 字符串，用于切到目标屏；name 即输出文件名。
 *
 * 依赖：puppeteer-core（指向系统已安装的 Chrome/Chromium）。
 *   - 默认探测 macOS 的 Google Chrome.app；可用 CHROME_PATH 环境变量覆盖。
 *   - 截图存入 --out 目录，文件名 <name>.png。
 */

const fs = require('fs');
const path = require('path');
const os = require('os');
const url = require('url');
const puppeteer = require('puppeteer-core');

function findChrome() {
  if (process.env.CHROME_PATH && fs.existsSync(process.env.CHROME_PATH)) {
    return process.env.CHROME_PATH;
  }
  const candidates = [
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/usr/bin/google-chrome',
    '/usr/bin/chromium-browser',
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  ];
  for (const c of candidates) {
    if (fs.existsSync(c)) return c;
  }
  return null;
}

function parseArgs(argv) {
  const a = { html: null, out: './screenshots', width: 390, height: 844, scale: 2, wait: 600, screens: null };
  for (let i = 2; i < argv.length; i++) {
    const k = argv[i];
    if (k === '--html') a.html = argv[++i];
    else if (k === '--out') a.out = argv[++i];
    else if (k === '--width') a.width = parseInt(argv[++i], 10);
    else if (k === '--height') a.height = parseInt(argv[++i], 10);
    else if (k === '--scale') a.scale = parseInt(argv[++i], 10);
    else if (k === '--wait') a.wait = parseInt(argv[++i], 10);
    else if (k === '--screens') a.screens = argv[++i];
  }
  return a;
}

/*
 * 页面内嵌的公共片段：isVisible(id) + DOM 兜底切换。
 * 之所以不写死 go()：早期版本只认 go()，导致 gen_prototype.py 产出的原型「三张截图内容全同」。
 */
const INPAGE_HELPERS = `
  function isVisible(x) {
    var el = document.getElementById(x);
    if (!el) return false;
    var st = window.getComputedStyle(el);
    return st.display !== 'none' && st.visibility !== 'hidden';
  }
  function domFallback(id) {
    var nodes = document.querySelectorAll('section[id], .page');
    nodes.forEach(function(el){ el.classList.remove('active'); });
    var t = document.getElementById(id);
    if (t) t.classList.add('active');
    if (t && !isVisible(id)) {
      nodes.forEach(function(el){ el.style.display = 'none'; });
      t.style.display = 'block';
    }
  }
`;

/*
 * 构造「切到指定屏」的触发脚本。按可靠性从高到低尝试三种策略：
 *   ① 页面自带切屏函数（go / show / select / nav / switchPage / goTo）——示例A原型用 go()，
 *      示例B原型用 select()，gen_prototype.py 生成的原型用 show()；函数名不一，故按候选名逐个探测。
 *   ② 直接 DOM 切换：给目标 <section id> 或 .page 加 active 类，其余移除
 *      （gen_prototype.py 的 CSS 约定即 .page{display:none} / .page.active{display:block}）。
 *   ③ 兜底：改 display 内联样式，确保即使无 active 约定也能出图。
 */
function buildAutoTrigger(id, extraArg) {
  const arg = JSON.stringify(id);
  const second = extraArg === undefined ? 'undefined' : JSON.stringify(extraArg);
  return `(function(){
  var id = ${arg};
  var extra = ${second};
${INPAGE_HELPERS}
  var fns = ['go', 'show', 'select', 'nav', 'switchPage', 'goTo'];
  for (var i = 0; i < fns.length; i++) {
    var f = window[fns[i]];
    if (typeof f === 'function') {
      try {
        if (extra === undefined) { f(id); } else { f(id, extra); }
        if (isVisible(id)) return;
      } catch (e) {}
    }
  }
  domFallback(id);
})();`;
}

async function resolveScreens(page, file) {
  if (file) {
    const raw = JSON.parse(fs.readFileSync(file, 'utf-8'));
    return raw.map((s) => ({ name: s.name, trigger: s.trigger }));
  }
  const ids = await page.evaluate(() =>
    Array.from(document.querySelectorAll('section[id]')).map((s) => s.id)
  );
  const screens = ids.map((id) => ({
    name: id,
    trigger: buildAutoTrigger(id),
  }));
  if (ids.includes('game')) {
    // 示例A类原型有「困难」变体：优先 go('game',{mode:'hard'})，函数不存在时退回 DOM 兜底
    screens.push({
      name: 'game-hard',
      trigger: buildAutoTrigger('game', { mode: 'hard' }),
    });
  }
  return screens;
}

(async () => {
  const a = parseArgs(process.argv);
  if (!a.html || !fs.existsSync(a.html)) {
    console.error('✗ 用法：node gen_screenshots.js --html <原型index.html> --out <截图目录>');
    process.exit(1);
  }
  const chrome = findChrome();
  if (!chrome) {
    console.error('✗ 未找到 Chrome/Chromium。请安装 Google Chrome，或设置环境变量 CHROME_PATH 指向可执行文件。');
    process.exit(2);
  }
  fs.mkdirSync(a.out, { recursive: true });

  const browser = await puppeteer.launch({
    executablePath: chrome,
    headless: true,
    timeout: 30000,
    args: [
      '--no-sandbox',
      '--disable-gpu',
      '--disable-dev-shm-usage',
      '--no-first-run',
      '--no-default-browser-check',
      '--disable-extensions',
      '--disable-features=Translate,OptimizationHints',
      '--use-gl=swiftshader',
      '--force-color-profile=srgb',
      `--user-data-dir=${os.tmpdir()}/wb-proto-shots-${Date.now()}`,
    ],
  });
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: a.width, height: a.height, deviceScaleFactor: a.scale });
    const fileUrl = url.pathToFileURL(path.resolve(a.html)).href;
    await page.goto(fileUrl, { waitUntil: 'domcontentloaded', timeout: 20000 });
    await new Promise((r) => setTimeout(r, a.wait));

    const screens = await resolveScreens(page, a.screens);
    if (!screens.length) {
      console.error('✗ 未探测到任何可截图屏（无 <section id> 且未提供 screens.json）');
      process.exit(3);
    }
    const seen = new Map();
    let dupWarn = 0;
    for (const s of screens) {
      try {
        await page.evaluate(s.trigger);
        await new Promise((r) => setTimeout(r, a.wait));
        const outFile = path.join(a.out, `${s.name}.png`);
        await page.screenshot({ path: outFile, fullPage: false });
        const sz = fs.statSync(outFile).size;
        const dup = seen.get(sz);
        if (dup) {
          console.error(`⚠ ${s.name}.png 与 ${dup}.png 字节数相同（${sz}），疑似未真正切屏`);
          dupWarn++;
        } else {
          seen.set(sz, s.name);
        }
        console.log(`✓ ${s.name}.png  (${sz} bytes)`);
      } catch (e) {
        console.error(`✗ ${s.name}.png 失败：${e.message}`);
      }
    }
    if (dupWarn) {
      console.error(`\n⚠ 共 ${dupWarn} 张疑似重复。请检查原型切屏函数名是否为 go/show/select，或改用 --screens screens.json 显式指定 trigger。`);
    }
    console.log(`\n完成：共生成 ${screens.length} 张截图 → ${path.resolve(a.out)}`);
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error('✗ 运行异常：', e.message);
  process.exit(4);
});
