#!/usr/bin/env python3
"""
pre_commit_gate_check.py — 主编排 git commit 前的硬审批门检查（v4.0.1）

实现 workflow/gates_CORE.md#门控的实现 中的门控脚本化：
1. 当前状态是否在硬审批门（PAUSE_GATE / clarification / strategy_gate）
   -> 如果在门+尝试 commit（不是 deliver/reject/feedback），则警告但放行
2. SCOPE_CHANGE 标记
   -> 标记存在则提示走回炉流程
3. lean_pm + 方案评审门通过后 commit IMPLEMENTING 相关
   -> 警告"lean_pm 模式不应进入研发"

不阻断 commit（避免破坏工作流），仅警告。fail-open 设计：
- 状态读取失败 -> 放行
- 解析失败 -> 放行
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]  # B仓根: scripts→skill→skills→.workbuddy→工作流-产品
# Route X：state.json 随 run 隔离在 runs/<run-id>/，不再有根级 state.json
RUNS = Path(__file__).resolve().parents[1] / "runs"


def _latest_state_file():
    files = sorted(RUNS.glob("*/state.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def load_state():
    sf = _latest_state_file()
    if not sf:
        return None
    try:
        return json.loads(sf.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def get_commit_msg():
    """从 .git/COMMIT_EDITMSG 读取 commit message（git 在 hook 时传入）"""
    msg_path = Path(".git/COMMIT_EDITMSG")
    if not msg_path.exists():
        return ""
    return msg_path.read_text(encoding="utf-8", errors="replace")


def check_pause_gate(state, msg):
    """检查 1：硬审批门上是否应该 commit"""
    if not state:
        return []
    warnings = []
    gate = state.get("gate")
    if gate and gate not in (None, "", "null"):
        # 硬审批门上 - 检查 commit 是否为合法推进动作
        if not any(kw in msg for kw in ["方案评审门", "原型评审门", "打回", "review", "审核", "feedback", "hook", "回炉", "REVISING"]):
            warnings.append(
                f"⚠️ 当前在「{gate}」状态，本次 commit 似乎与门推进无关。"
                f"建议先 PM 决策（通过 / 打回 / 改需求）再 commit。"
            )
    return warnings


def check_scope_change(state):
    """检查 2：SCOPE_CHANGE 标记"""
    if not state:
        return []
    if state.get("scope_change"):
        return ["⚠️ 当前 REQ 标有 scope_change=true，应走回炉流程（先 git revert/reset 受影响阶段再 commit）"]
    return []


def check_lean_pm_no_dev(state, msg):
    """检查 3：lean_pm 模式不应 commit IMPLEMENTING 相关"""
    if not state:
        return []
    if state.get("mode") != "lean_pm":
        return []
    # lean_pm 终点产物只有 PRD + 原型 + 用例
    lean_violations = [
        "implementation/code", "test_report.md", "B_dev", "原型研发",
    ]
    for v in lean_violations:
        if v in msg or any(v in (file_path or "") for file_path in get_staged_files()):
            return [
                f"⚠️ lean_pm 模式不应产出 '{v}'。"
                f"如确需研发，请改 mode=standard_pm（说 '切 standard_pm'）。"
            ]
    return []


def get_staged_files():
    """git diff --cached 拿暂存文件"""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return []
        return [f.strip() for f in result.stdout.splitlines() if f.strip()]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def main():
    state = load_state()
    msg = get_commit_msg()
    all_warnings = []
    all_warnings += check_pause_gate(state, msg)
    all_warnings += check_scope_change(state)
    all_warnings += check_lean_pm_no_dev(state, msg)

    if all_warnings:
        print("=" * 60)
        print("🚦 门控自检报告（pre_commit_gate_check.py）")
        print("=" * 60)
        for w in all_warnings:
            print(w)
        print("=" * 60)
        print("⚠️ 警告不阻断 commit（fail-open 设计）。如确认无误可继续。")
        print("=" * 60)

    # exit 0 = 放行（warn）；exit 2 = fail（暂未启用）
    return 0


if __name__ == "__main__":
    sys.exit(main())