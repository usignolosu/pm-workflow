#!/usr/bin/env python3
"""
state_context.py — UserPromptSubmit hook：每轮注入当前任务状态摘要

输出 ZCode hook 规范的 JSON：{"additionalContext": "..."}
任何异常都 fail-open（exit 0，无输出），绝不阻塞会话。
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]  # B仓根: scripts→skill→skills→.workbuddy→工作流-产品
# Route X：state.json 随 run 隔离在 runs/<run-id>/，不再有根级 state.json

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

RUNS = detect_root() / "runs"


def _latest_state_file():
    files = sorted(RUNS.glob("*/state.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def build_context() -> str:
    state_file = _latest_state_file()
    if not state_file:
        return ""
    s = json.loads(state_file.read_text(encoding="utf-8"))
    p = s.get("progress", {})
    lines = [
        f"[任务状态] REQ: {s.get('current_req')} | phase: {s.get('phase')} | "
        f"scale: {s.get('scale')} | mode: {s.get('mode')}",
        f"[进度] {p.get('percent', '?')}% {p.get('current_step_human', '')} | "
        f"下一步: {p.get('next_action', '')}",
    ]
    if s.get("gate"):
        lines.append(f"[门禁] {s['gate']} 等待 PM 决策——不要替 PM 拍板，也不要在门上继续推进")
    if s.get("bug_fix_in_progress"):
        lines.append(f"[bug 修复中] {s['bug_fix_in_progress']}")
    return "\n".join(lines)


def main() -> int:
    try:
        ctx = build_context()
        if ctx:
            print(json.dumps({"additionalContext": ctx}, ensure_ascii=False))
    except Exception:
        pass  # fail-open
    return 0


if __name__ == "__main__":
    sys.exit(main())
