#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
report_status.py — 执行留痕与状态上报

把每个子 agent 的工作状态追加写入 runs/<run-id>/execution-log.md。
状态契约：agent / state / doing / output / 来源 / 耗时

用法：
  python3 report_status.py --run 20260715-01 --agent 调研员 \
      --state running --doing "检索知识库" --output "research.md" --source "kb#12" --cost 3s
  python3 report_status.py --run 20260715-01 --summary    # 打印当前看板
"""
import argparse
import os
import sys
from datetime import datetime

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS_DIR = os.path.join(SKILL_DIR, "runs")


def log_path(run_id: str) -> str:
    return os.path.join(RUNS_DIR, run_id, "execution-log.md")


def ensure_run(run_id: str) -> str:
    path = log_path(run_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# 执行留痕 · run {run_id}\n\n")
    return path


VALID_STATES = {"pending", "running", "done", "blocked", "revision"}


def report(run_id, agent, state, doing, output, source, cost):
    if state not in VALID_STATES:
        print(f"[warn] state 应为 {VALID_STATES}，收到 {state}", file=sys.stderr)
    path = ensure_run(run_id)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = (f"- [{ts}] **{agent}** `{state}` | 在做什么：{doing} "
            f"| 产出：{output or '-'} | 来源：{source or '-'} | 耗时：{cost or '-'}\n")
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)
    print(f"✓ 已记录 {agent} → {state}")


def summary(run_id):
    path = log_path(run_id)
    if not os.path.exists(path):
        print(f"[warn] 未找到 {path}")
        return
    with open(path, encoding="utf-8") as f:
        print(f.read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="run-id，如 20260715-01")
    ap.add_argument("--agent", help="角色名")
    ap.add_argument("--state", help="pending/running/done/blocked/revision")
    ap.add_argument("--doing", default="")
    ap.add_argument("--output", default="")
    ap.add_argument("--source", default="")
    ap.add_argument("--cost", default="")
    ap.add_argument("--summary", action="store_true", help="打印当前执行日志")
    args = ap.parse_args()
    if args.summary:
        summary(args.run)
    else:
        if not args.agent or not args.state:
            ap.error("上报需提供 --agent 与 --state")
        report(args.run, args.agent, args.state, args.doing,
               args.output, args.source, args.cost)


if __name__ == "__main__":
    main()
