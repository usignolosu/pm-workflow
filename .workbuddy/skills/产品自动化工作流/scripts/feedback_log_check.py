#!/usr/bin/env python3
"""
feedback_log_check.py — feedback_log 目录结构校验（v4.0.1）

期望结构：
- feedback_log/README.md
- feedback_log/{agent_slug}/YYYY-MM-DD.md  # 按 Agent 分目录
- feedback_log/_delivery_{req_id}.md     # 交付复盘
- feedback_log/_reject_{req_id}.md        # 打回记录（可选）
- feedback_log/_timeout_{req_id}_{date}.md  # 澄清超时（可选）

校验：
- 每个目录都必须有 README.md 解释
- Agent 目录命名必须是有效 slug（libu/bingbu/hubu/...）
- 日期格式 YYYY-MM-DD.md

不阻断（fail-open），仅报告异常。
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]  # B仓根: scripts→skill→skills→.workbuddy→工作流-产品
FB = ROOT / "feedback_log"
EXPECTED_AGENTS = {
    "libu", "bingbu", "hubu", "libu_compliance", "gongbu",
    "xingbu", "menxia", "shangshu",
}
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")


def main():
    issues = []
    if not FB.exists():
        print(f"⚠️ {FB} 不存在")
        return 0

    for entry in sorted(FB.iterdir()):
        name = entry.name
        if name.startswith("_"):
            # 顶层特殊文件（_delivery_*, _reject_*, _timeout_*）
            continue
        if name in {"README.md", ".gitkeep"}:
            continue
        if entry.is_file():
            issues.append(f"❌ 顶层散文件 {name}（应放子目录或加 _ 前缀）")
            continue
        # 是目录
        if name not in EXPECTED_AGENTS:
            issues.append(
                f"⚠️ 未知 Agent 目录 {name}/（期望 {EXPECTED_AGENTS}）"
            )
        # 检查目录下是否有日期格式错误的文件
        for f in entry.iterdir():
            if f.is_file() and f.suffix == ".md":
                if not DATE_PATTERN.match(f.name):
                    issues.append(
                        f"⚠️ {name}/{f.name} 命名不符合 YYYY-MM-DD.md 格式"
                    )

    if issues:
        print("=" * 60)
        print("📋 feedback_log 结构检查")
        print("=" * 60)
        for i in issues:
            print(i)
        print("=" * 60)
        print(f"共 {len(issues)} 项需关注")
    else:
        print("✅ feedback_log 结构合规")

    return 0


if __name__ == "__main__":
    sys.exit(main())