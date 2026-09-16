#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_prototype.py — 低保真 JSON → 高保真原型（HTML 可交互预览 + React 脚手架）

P0 骨架：读取页面规格 JSON（来自 references/prompts/prototype-desc.md 的结构），
生成：① 独立 HTML 可交互原型（免设计工具打开）② React+Tailwind 脚手架（每个页面一个组件）。

用法：
  python3 gen_prototype.py --spec pages.json --out ./prototype
  # pages.json 示例见 references/prompts/prototype-desc.md
"""
import argparse
import json
import os
import sys


def gen_html(spec: dict) -> str:
    pages = spec.get("pages", [])
    nav = "".join(f'<button onclick="show(\'{p["name"]}\')">{p["name"]}</button>' for p in pages)
    sections = ""
    for p in pages:
        els = "".join(f'<div class="el">🔹 {e}</div>' for e in p.get("elements", []))
        inter = "".join(f'<li>{k} → {v}</li>' for k, v in p.get("interactions", {}).items())
        layout = p.get("layout", "（未指定布局）")
        sections += f'''
<section id="{p['name']}" class="page">
  <h2>{p["name"]}</h2>
  <p class="layout">布局：{layout}</p>
  <div class="els">{els}</div>
  <div class="inter"><b>交互：</b><ul>{inter}</ul></div>
</section>'''
    return f"""<!doctype html>
<html lang="zh"><head><meta charset="utf-8">
<title>原型预览</title>
<style>
 body{{font-family:-apple-system,'PingFang SC',sans-serif;margin:0;background:#f7f8fa;color:#1f2937}}
 header{{display:flex;gap:8px;flex-wrap:wrap;padding:12px;background:#fff;border-bottom:1px solid #e5e7eb}}
 header button{{border:1px solid #d1d5db;background:#fff;border-radius:8px;padding:6px 12px;cursor:pointer}}
 header button:hover{{background:#eff6ff}}
 main{{padding:20px}}
 .page{{display:none;background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:20px;max-width:720px}}
 .page.active{{display:block}}
 h2{{margin-top:0}}
 .layout{{color:#6b7280;font-size:13px}}
 .el{{background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:8px 12px;margin:6px 0}}
 .inter{{margin-top:10px;font-size:13px}}
</style></head>
<body>
<header>{nav}</header>
<main>{sections}</main>
<script>
 function show(n){{document.querySelectorAll('.page').forEach(s=>s.classList.remove('active'));
   var el=document.getElementById(n); if(el) el.classList.add('active');}}
 if(document.querySelector('.page')) document.querySelector('.page').classList.add('active');
</script>
</body></html>"""


def gen_react(spec: dict, out: str):
    comps = ""
    for p in spec.get("pages", []):
        name = "".join(w.capitalize() for w in re.split(r"[\s/]+", p["name"]))
        els = "\n".join(f'      <div className="el">🔹 {e}</div>' for e in p.get("elements", []))
        comps += f"""
export function {name}() {{
  return (
    <div className="page">
      <h2>{p['name']}</h2>
      <p className="layout">布局：{p.get('layout','')}</p>
{els}
    </div>
  );
}}
"""
    app = f"""import {{ useState }} from 'react';
{comps}
export default function App() {{
  const [page, setPage] = useState('{spec.get('pages',[{}])[0].get('name','') if spec.get('pages') else ''}');
  return (
    <div>
      <nav>{{[{', '.join("'"+p['name']+"'" for p in spec.get('pages',[]))}]}}.map(n => (
        <button key={{n}} onClick={{() => setPage(n)}}>{{n}}</button>
      ))}}</nav>
      {{page === '{spec.get('pages',[{}])[0].get('name','') if spec.get('pages') else ''}' && <{''.join(w.capitalize() for w in re.split(r"[\\s/]+", spec.get('pages',[{}])[0].get('name','') if spec.get('pages') else ''))} />}}
    </div>
  );
}}
"""
    with open(os.path.join(out, "App.jsx"), "w", encoding="utf-8") as f:
        f.write(app)


import re
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True, help="页面规格 JSON")
    ap.add_argument("--out", required=True, help="原型输出目录")
    args = ap.parse_args()
    spec = json.load(open(args.spec, encoding="utf-8"))
    pages = spec.get("pages") or []
    if not pages:
        # 常见误用：写成 screens/blocks（gen_prototype 只认 pages/name/elements/layout/interactions）
        hint = ""
        if spec.get("screens"):
            hint = "（检测到顶层键 'screens'——本脚本要求的是 'pages'）"
        sys.stderr.write(
            "✗ spec 中 'pages' 为空，将产出空原型。%s\n"
            "  正确结构见 references/prompts/prototype-desc.md：\n"
            '  {"pages":[{"name":"登录页","elements":["手机号输入"],"layout":"居中卡片","interactions":{}}]}\n'
            % hint
        )
        sys.exit(5)
    os.makedirs(args.out, exist_ok=True)
    html = gen_html(spec)
    with open(os.path.join(args.out, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    try:
        gen_react(spec, args.out)
        print(f"✓ 生成 HTML 预览 + React 脚手架 → {args.out}")
    except Exception as e:
        print(f"✓ 生成 HTML 预览 → {args.out}（React 脚手架跳过：{e}）", file=sys.stderr)


if __name__ == "__main__":
    main()
