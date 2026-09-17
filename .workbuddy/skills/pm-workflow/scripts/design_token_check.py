#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
design_token_check.py — 硬编码色值 / px 自检（Guardrail g015）

读取 contracts/design_tokens.yaml 的 primitive 层，收集「合法值集合」
（色值 + font-size + spacing），扫描目标 HTML 文件中的硬编码字面量：
  - #RGB / #RRGGBB 十六进制色值
  - rgb(...) / rgba(...) 函数色值
  - <数字>px 字号 / 间距
命中 primitive 合法集合 → PASS；不在 → 报出 `文件:行号: 值`，并提示应使用的 token。
退出码：有问题返回 1（便于接入 CI / guardrail），无问题返回 0 并打印 OK。

用法：
  python3 design_token_check.py path/to/a.html
  python3 design_token_check.py dir/  other.html
  python3 design_token_check.py --root /path/to/repo  a.html   # 指定 token 文件所在仓库根
"""
import argparse
import os
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: 需要 PyYAML（pip install pyyaml）", file=sys.stderr)
    sys.exit(2)


# ---------- 路径解析：与 self_check.py 一致的三级 detect_root() ----------
def detect_root() -> Path:
    """三级路径解析：PM_WORKFLOW_RUNS 环境变量 → 向上找 .git 根 → $HOME/pm-workflow-runs 兜底"""
    env = os.environ.get("PM_WORKFLOW_RUNS")
    if env:
        return Path(env).expanduser().resolve()
    cur = Path.cwd().resolve()
    for p in (cur, *cur.parents):
        if (p / ".git").exists():
            return p
    return Path.home() / "pm-workflow-runs"


# 脚本相对仓库根（scripts → pm-workflow → skills → .workbuddy → 仓库根）
REPO_ROOT_BY_SCRIPT = Path(__file__).resolve().parents[4]


def find_tokens_yaml(root_arg):
    """定位 contracts/design_tokens.yaml：--root 优先，其次 detect_root()，再次脚本相对仓库根。"""
    candidates = []
    if root_arg:
        candidates.append(Path(root_arg).expanduser().resolve() / "contracts" / "design_tokens.yaml")
    candidates.append(detect_root() / "contracts" / "design_tokens.yaml")
    candidates.append(REPO_ROOT_BY_SCRIPT / "contracts" / "design_tokens.yaml")
    for c in candidates:
        if c.is_file():
            return c
    searched = "\n  ".join(str(c) for c in candidates)
    print(f"ERROR: 找不到 contracts/design_tokens.yaml，已尝试：\n  {searched}", file=sys.stderr)
    sys.exit(2)


# ---------- 解析 primitive 合法值 ----------
PX_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)px\s*$")
HEX_FULL = re.compile(r"^#([0-9a-fA-F]{6})$")
HEX_SHORT = re.compile(r"^#([0-9a-fA-F]{3})$")

# rules.exceptions 中明确允许的关键字（hex 形式单独加入 legal_colors）
COLOR_EXCEPTIONS = {"#ffffff", "white", "transparent", "currentcolor"}


def parse_px(value):
    m = PX_RE.match(str(value))
    return int(float(m.group(1))) if m else None


def load_legal_values(tokens_path: Path):
    """返回 (legal_colors:set, legal_px:set, color_to_hex:dict, px_to_tokens:dict)"""
    data = yaml.safe_load(tokens_path.read_text(encoding="utf-8"))
    primitive = data.get("primitive", {}) or {}
    color = primitive.get("color", {}) or {}
    font_size = primitive.get("font-size", {}) or {}
    spacing = primitive.get("spacing", {}) or {}
    radius = primitive.get("radius", {}) or {}

    legal_colors = {str(v).lower() for v in color.values()}
    legal_colors |= COLOR_EXCEPTIONS

    legal_px = set()
    px_to_tokens = {}
    # D2-方案A：primitive 全部含 px 的维度（font-size / spacing / radius）并入合法集合，
    # 这样 border-radius: 12px 之类合法圆角能 PASS（同时仍需方案B 限定属性上下文）。
    for layer in (font_size, spacing, radius):
        for name, v in layer.items():
            px = parse_px(v)
            if px is not None:
                legal_px.add(px)
                px_to_tokens.setdefault(px, []).append(name)

    # 色值名 -> hex（用于建议最近 token）
    color_to_hex = {name: str(hx).lower() for name, hx in color.items()}
    return legal_colors, legal_px, color_to_hex, px_to_tokens


# ---------- 最近 token 建议 ----------
def hex_to_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def nearest_color_token(hexv, color_to_hex):
    target = hex_to_rgb(hexv)
    best, best_d = None, None
    for name, hx in color_to_hex.items():
        d = sum((a - b) ** 2 for a, b in zip(target, hex_to_rgb(hx)))
        if best_d is None or d < best_d:
            best_d, best = d, name
    return best or "（无可用 token）"


def nearest_px_token(px, px_to_tokens, legal_px):
    if not legal_px:
        return "（无可用 token）"
    near = min(legal_px, key=lambda x: abs(x - px))
    names = px_to_tokens.get(near, [])
    return f"{near}px（token: {', '.join(names)}）" if names else f"{near}px"


# ---------- 扫描 ----------
HEX_RE = re.compile(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")
RGB_RE = re.compile(r"rgba?\(\s*[\d.\s,%]+\s*\)")
NUM_PX_RE = re.compile(r"(\d+(?:\.\d+)?)px")


# ---------- 注释剥离（保留行号）：把注释内容替换为等长空格 ----------
def strip_comments(text):
    """剥离 CSS 块注释 /* ... */、HTML 注释 <!-- ... -->、单行 // 注释。
    注释内容替换为等长空格（不删行、不动换行），保证后续扫描报错行号与原文一致。
    """
    # CSS 块注释（可跨行，非贪婪）
    text = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.DOTALL)
    # HTML 注释（可跨行，非贪婪）
    text = re.sub(r"<!--.*?-->", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.DOTALL)
    # 单行 // 注释：排除 URL 的 :// 写法（http:// 等），其余视为行注释
    text = re.sub(r"(?<!:)//[^\n]*", lambda m: " " * len(m.group(0)), text)
    return text


def normalize_color(c):
    """色值归一化：小写 + 三位简写展开为六位。#FFF→#ffffff, #abc→#aabbcc。"""
    c = c.lower()
    if c.startswith("#"):
        h = c[1:]
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        return "#" + h
    return c


# D2-方案B：px 检查只在以下 CSS 属性的上下文里生效，其余属性的 px
# （如 border: 1px solid / box-shadow: 0 2px 8px / transform: translateX(2px)）
# 一律放行，避免误伤合法原型（reviewer guardrail g015 不被误触发）。
CHECK_PX_PROPS = {
    "font-size", "padding", "margin", "gap",
    "width", "height", "min-width", "max-width", "min-height", "max-height",
    "top", "right", "bottom", "left", "inset",
    "border-radius", "border-top-left-radius", "border-top-right-radius",
    "border-bottom-left-radius", "border-bottom-right-radius",
    "border-width", "border-top-width", "border-right-width",
    "border-bottom-width", "border-left-width",
    "padding-top", "padding-right", "padding-bottom", "padding-left",
    "margin-top", "margin-right", "margin-bottom", "margin-left",
}

PROP_DECL_RE = re.compile(r"([\w-]+)\s*:\s*([^;{}]*)")


def scan_file(path: Path, legal_colors, legal_px, color_to_hex, px_to_tokens, check_px):
    """返回 [(line_no, value, hint), ...]"""
    findings = []
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(f"! WARN 无法读取 {path}: {e}", file=sys.stderr)
        return findings

    # D1：扫描前剥离注释（等长空格替换，行号不变）
    text = strip_comments(raw)
    # D3：比对合法集合前统一归一化（小写 + 三位简写展开），但报错显示原始写法
    legal_colors_norm = {normalize_color(c) for c in legal_colors}

    for i, line in enumerate(text.splitlines(), 1):
        for m in HEX_RE.finditer(line):
            val = "#" + m.group(1)
            if normalize_color(val) in legal_colors_norm:
                continue
            sug = nearest_color_token(val, color_to_hex)
            findings.append((i, val, f"不在 primitive.color 合法集合，建议改用 token: {sug}"))
        for m in RGB_RE.finditer(line):
            findings.append((i, m.group(0), "rgb()/rgba() 为硬编码色值，应引用 primitive.color 的 token"))
        if check_px:
            # D2：仅在明确属性上下文里检查 px
            for decl in PROP_DECL_RE.finditer(line):
                prop = decl.group(1).lower()
                if prop not in CHECK_PX_PROPS:
                    continue
                for pxm in NUM_PX_RE.finditer(decl.group(2)):
                    px = int(float(pxm.group(1)))
                    if px in legal_px:
                        continue
                    sug = nearest_px_token(px, px_to_tokens, legal_px)
                    findings.append((i, pxm.group(0), f"不在 primitive.font-size/spacing/radius 合法集合，建议改用 token: {sug}"))
    return findings


def collect_html(paths):
    files = []
    for p in paths:
        pp = Path(p)
        if pp.is_dir():
            files.extend(sorted(pp.rglob("*.html")))
        elif pp.is_file():
            files.append(pp)
        else:
            print(f"! WARN 路径不存在，已跳过：{p}", file=sys.stderr)
    return files


def main():
    ap = argparse.ArgumentParser(
        description="硬编码色值 / px 自检（Guardrail g015）：对照 contracts/design_tokens.yaml 的 primitive 层")
    ap.add_argument("paths", nargs="+", help="要扫描的 HTML 文件或目录（支持多个）")
    ap.add_argument("--root", default=None, help="token 文件所在仓库根（默认用 detect_root() 三级解析）")
    ap.add_argument("--no-px", action="store_true", help="跳过 px 检查（仅查色值）")
    args = ap.parse_args()

    tokens_path = find_tokens_yaml(args.root)
    legal_colors, legal_px, color_to_hex, px_to_tokens = load_legal_values(tokens_path)

    html_files = collect_html(args.paths)
    if not html_files:
        print("⚠️ 未找到任何 HTML 文件可扫描", file=sys.stderr)
        sys.exit(2)

    all_findings = []
    for f in html_files:
        for ln, val, hint in scan_file(f, legal_colors, legal_px, color_to_hex, px_to_tokens,
                                       check_px=not args.no_px):
            all_findings.append((f, ln, val, hint))

    print(f"token 规范：{tokens_path}")
    print(f"扫描文件：{len(html_files)} 个")
    if all_findings:
        print("=" * 64)
        print("✗ design_token_check 发现硬编码（Guardrail g015）")
        print("=" * 64)
        for f, ln, val, hint in all_findings:
            print(f"{f}:{ln}: {val}  → {hint}")
        print("=" * 64)
        print(f"共 {len(all_findings)} 处问题，请改用 contracts/design_tokens.yaml 中的 token")
        sys.exit(1)
    print("✓ OK：未发现违规硬编码色值 / px（均命中 primitive 合法集合）")
    sys.exit(0)


if __name__ == "__main__":
    main()
