#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
self_check.py — Pm Workflow Skill 功能自校验

自动校验脚本层能否协同工作（不含 LLM 内容生成，那部分在 Skill 运行时由角色产出）：
  建示例知识库 → ingest → retrieve(验证检索命中) → build_graph → gen_prototype → report_status
输出 PASS/FAIL 汇总，全部通过则退出码 0。

用法：
  python3 self_check.py
  python3 self_check.py --kb-dir /tmp/mykb   # 指定知识库落点（默认系统临时目录）
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(SKILL_DIR, "scripts")


def detect_root() -> Path:
    """Route X+: 过程留痕写到工作区根，避免随 Skill 包分发出去。"""
    env = os.environ.get("PM_WORKFLOW_RUNS")
    if env:
        return Path(env).expanduser().resolve()
    cur = Path.cwd().resolve()
    for p in (cur, *cur.parents):
        if (p / ".git").exists():
            return p
    # 兜底：绝不落在 Skill 包内
    return Path.home() / "pm-workflow-runs"

FAILS = []


def check(name, cond, detail=""):
    mark = "✓ PASS" if cond else "✗ FAIL"
    print(f"{mark}  {name}" + ("" if cond else f"  → {detail}"))
    if not cond:
        FAILS.append(name)


def run(script, *args, **kw):
    cmd = [sys.executable, os.path.join(SCRIPTS, script), *args]
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb-dir", default=None, help="知识库目录（默认临时目录）")
    args = ap.parse_args()

    print("="*56)
    print(" Pm Workflow · 功能自校验")
    print("="*56)

    # 1) 建示例知识库源
    src = tempfile.mkdtemp(prefix="skillcheck_src_")
    with open(os.path.join(src, "tasks.md"), "w", encoding="utf-8") as f:
        f.write("# 团队任务看板\n团队任务协作工具支持任务看板视图，拖拽卡片改变状态，"
                "支持分配成员与截止提醒。成员可在看板上看到自己负责的任务。\n")
    with open(os.path.join(src, "login.md"), "w", encoding="utf-8") as f:
        f.write("# 登录\n用户通过手机号登录系统，需要验证码校验。登录失败应提示具体错误。\n")
    check("示例知识库源可写", os.path.exists(os.path.join(src, "tasks.md")))

    # 2) ingest
    kb = args.kb_dir or tempfile.mkdtemp(prefix="skillcheck_kb_")
    r = run("ingest.py", "--src", src, "--out", kb)
    idx = os.path.join(kb, "index.json")
    check("ingest 生成 index.json", os.path.exists(idx), r.stderr.strip())
    if os.path.exists(idx):
        data = json.load(open(idx, encoding="utf-8"))
        check("ingest 索引到片段(count>0)", data.get("count", 0) > 0, f"count={data.get('count')}")

    # 3) retrieve（验证检索命中）
    r = run("retrieve.py", "--kb", kb, "--query", "任务看板")
    out = r.stdout
    check("retrieve 正常输出", r.returncode == 0 and "任务看板" in out, r.stderr.strip())
    # 验证打分非全零：输出里应有 [0.xxx] 且某行分数>0
    import re
    scores = [float(x) for x in re.findall(r"\[([0-9]+\.[0-9]+)\]", out)]
    check("retrieve 打分有效(有>0分)", any(s > 0 for s in scores), f"scores={scores}")

    # 4) build_graph
    gpath = os.path.join(kb, "graph.json")
    r = run("build_graph.py", "--kb", kb, "--out", gpath)
    check("build_graph 生成 graph.json", os.path.exists(gpath), r.stderr.strip())
    if os.path.exists(gpath):
        g = json.load(open(gpath, encoding="utf-8"))
        check("图谱含节点(nodes>0)", len(g.get("nodes", [])) > 0, f"nodes={len(g.get('nodes',[]))}")

    # 5) gen_prototype
    proto_out = tempfile.mkdtemp(prefix="skillcheck_proto_")
    spec = os.path.join(proto_out, "pages.json")
    with open(spec, "w", encoding="utf-8") as f:
        json.dump({"pages": [{"name": "看板页", "elements": ["任务卡片", "添加按钮"],
                              "layout": "三列看板", "interactions": {"添加按钮": "打开新建弹窗"}}]}, f)
    r = run("gen_prototype.py", "--spec", spec, "--out", proto_out)
    check("gen_prototype 生成 index.html", os.path.exists(os.path.join(proto_out, "index.html")), r.stderr.strip())

    # 6) report_status（执行留痕）
    run_dir = os.path.join(str(detect_root() / "runs"), "self-check")
    r = run("report_status.py", "--run", "self-check", "--agent", "测试",
            "--state", "done", "--doing", "功能自校验", "--output", "self_check", "--cost", "1s")
    log = os.path.join(run_dir, "execution-log.md")
    check("report_status 写入 execution-log.md", os.path.exists(log), r.stderr.strip())

    # 7) gen_screenshots.js（PRD 页面截图）
    node = shutil.which("node")
    if not node:
        for cand in [
            os.path.expanduser("~/.workbuddy/binaries/node/versions/22.22.2/bin/node"),
            os.path.expanduser("~/.workbuddy/binaries/node/versions/22.22.3/bin/node"),
        ]:
            if os.path.exists(cand):
                node = cand
                break
    chrome = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
    if not chrome:
        for cand in [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]:
            if os.path.exists(cand):
                chrome = cand
                break
    if node and chrome:
        env = os.environ.copy()
        env["NODE_PATH"] = os.path.expanduser("~/.workbuddy/binaries/node/workspace/node_modules")
        shots_out = os.path.join(proto_out, "screenshots")
        r = subprocess.run(
            [node, os.path.join(SCRIPTS, "gen_screenshots.js"),
             "--html", os.path.join(proto_out, "index.html"),
             "--out", shots_out, "--scale", "1", "--wait", "300"],
            capture_output=True, text=True, env=env, timeout=60000,
        )
        pngs = [f for f in os.listdir(shots_out) if f.endswith(".png")] if os.path.isdir(shots_out) else []
        check("gen_screenshots.js 生成 PNG 截图", len(pngs) > 0, (r.stderr or r.stdout).strip())
    else:
        print(f"! WARN  跳过 gen_screenshots.js 校验：node={bool(node)}, chrome={bool(chrome)}")

    # 汇总
    print("-"*56)
    if FAILS:
        print(f"结果：FAIL（{len(FAILS)} 项未通过）")
        for f in FAILS:
            print(f"  - {f}")
        print("-"*56)
        sys.exit(1)
    print("结果：ALL PASS ✓  脚本链路功能完好")
    print("-"*56)
    sys.exit(0)


if __name__ == "__main__":
    main()
