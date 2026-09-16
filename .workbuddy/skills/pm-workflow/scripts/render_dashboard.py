#!/usr/bin/env python3
"""
render_dashboard.py — 任务总览面板渲染器（v4.0）

用法：
  python3 scripts/render_dashboard.py              # 终端打印
  python3 scripts/render_dashboard.py --obsidian  # 写入 Obsidian 笔记
  python3 scripts/render_dashboard.py --json      # 输出 JSON
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: 需要 PyYAML", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[4]  # B仓根: scripts→skill→skills→.workbuddy→工作流-产品
# Route X：活动需求目录改指 runs/<run-id>/（不再读根级 state.json / 归档需求产出）
RUNS = Path(__file__).resolve().parents[1] / "runs"
KG_INDEX = ROOT / "knowledge_graph" / "index.jsonl"
FEEDBACK_DIR = ROOT / "feedback_log"
EVOLUTION_DIR = ROOT / "evolution_log"
DELIVERABLES = RUNS  # 活动需求目录（runs/<run-id>/），内含 */03_finalized/INDEX.md


def _latest_state_file():
    """返回 runs/ 下最近修改的 state.json（机读状态随 run 隔离），无则 None"""
    files = sorted(RUNS.glob("*/state.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None
# v4.0.1 修复：Obsidian vault 路径硬编码 → 配置化
# 优先级：OBSIDIAN_VAULT 环境变量 > state.json obsidian_note_path > 默认值
_DEFAULT_OBSIDIAN = Path.home() / "Documents" / "Codex" / "obsidian_ai"


def _resolve_obsidian_path() -> Path:
    env_vault = os.environ.get("OBSIDIAN_VAULT")
    if env_vault:
        return Path(env_vault) / "10-Notes" / "工作流体系" / "任务总览.md"
    # state.json 可选覆盖（Route X：随 run 隔离，取最近修改的一份）
    sf = _latest_state_file()
    if sf:
        try:
            s = json.loads(sf.read_text(encoding="utf-8"))
            custom = s.get("obsidian_note_path")
            if custom:
                return Path(custom)
        except (json.JSONDecodeError, OSError):
            pass
    return _DEFAULT_OBSIDIAN / "10-Notes" / "工作流体系" / "任务总览.md"


OBSIDIAN_NOTE = _resolve_obsidian_path()


def load_state():
    if not STATE.exists():
        return {}
    return json.loads(STATE.read_text(encoding="utf-8"))


def load_kg_stats():
    if not KG_INDEX.exists():
        return {"total": 0, "by_type": {}}
    types = []
    for line in KG_INDEX.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                e = json.loads(line)
                types.append(e.get("_type", "Unknown"))
            except json.JSONDecodeError:
                pass
    from collections import Counter
    c = Counter(types)
    return {"total": len(types), "by_type": dict(c.most_common())}


def load_history():
    """从 4 个 03_finalized/INDEX.md 解析历史 REQ 列表"""
    history = []
    if not DELIVERABLES.exists():
        return history
    for idx_path in sorted(DELIVERABLES.glob("*/03_finalized/INDEX.md")):
        req_id = idx_path.parent.parent.name
        content = idx_path.read_text(encoding="utf-8")
        # 解析 frontmatter
        if not content.startswith("---"):
            continue
        try:
            parts = content.split("---", 2)
            if len(parts) < 3:
                continue
            fm = yaml.safe_load(parts[1])
            if not isinstance(fm, dict):
                continue
        except yaml.YAMLError:
            continue

        history.append({
            "req_id": req_id,
            "title": fm.get("title", "(无标题)"),
            "scale": fm.get("scale", "?"),
            "state": fm.get("state", "?"),
            "current_phase": fm.get("current_phase", "?"),
            "current_gate": fm.get("current_gate", "null"),
            "created": str(fm.get("created", "?")),
            "finalized": str(fm.get("finalized")) if fm.get("finalized") else None,
            "delivered": str(fm.get("delivered")) if fm.get("delivered") else None,
            "abandoned": str(fm.get("abandoned")) if fm.get("abandoned") else None,
            "defect_summary": fm.get("defect_summary") or {"p0": 0, "p1": 0, "p2": 0, "p3": 0},
            "agents_completed": sum(
                1 for a in fm.get("agents_dispatched", {}).values()
                if isinstance(a, dict) and a.get("state") == "completed"
            ),
            "agents_total": len(fm.get("agents_dispatched", {})),
        })
    return history


def load_recent_feedback(n=5):
    """最近 N 条 PM 反馈"""
    if not FEEDBACK_DIR.exists():
        return []
    files = []
    for f in FEEDBACK_DIR.rglob("*.md"):
        files.append((f.stat().st_mtime, f))
    files.sort(reverse=True)
    out = []
    for _, path in files[:n]:
        content = path.read_text(encoding="utf-8")
        # 取第一行非空标题 + 第一段内容
        lines = [l.strip() for l in content.splitlines() if l.strip() and not l.startswith("#")]
        first_para = lines[0][:100] if lines else "(空)"
        out.append({
            "file": str(path.relative_to(ROOT)),
            "mtime": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d"),
            "excerpt": first_para,
        })
    return out


def render_terminal(state, history, feedback, kg_stats) -> str:
    """终端输出 5 段：当前 / 历史 / 计数 / 反馈 / 下一步"""
    lines = []
    lines.append("=" * 70)
    lines.append(f"📊 supervisor·reviewer·专家组 产品工作流 · 任务总览 · {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("=" * 70)

    # 1. 当前 REQ
    lines.append("")
    lines.append("🔵 当前 REQ")
    lines.append("-" * 70)
    if state:
        # v3.3 新增：progress 进度条视图
        progress = state.get("progress")
        if progress:
            step = progress.get("current_step", "?")
            label = progress.get("current_step_human", step)
            total = progress.get("total_steps", 1)
            percent = progress.get("percent", 0)
            next_action = progress.get("next_action", "")
            eta = progress.get("eta_minutes", 0)
            questions = progress.get("next_questions", [])

            # 进度条（█/░，宽 30）
            bar_w = 30
            filled = int(bar_w * percent / 100)
            bar = "█" * filled + "░" * (bar_w - filled)
            lines.append(f"   进度:     [{bar}] {percent}%  阶段 {step}")
            lines.append(f"   标签:     {label}")
            if next_action:
                lines.append(f"   下一步:   {next_action}")
            if questions:
                lines.append(f"   待答:")
                for q in questions[:3]:
                    lines.append(f"     - {q}")
            if eta:
                lines.append(f"   预估剩余: {eta} 分钟")
            lines.append("")

        lines.append(f"   ID:        {state.get('current_req', '(无)')}")
        lines.append(f"   Phase:     {state.get('phase', '?')}")
        lines.append(f"   Step:      {state.get('step', '?') or '(无)'}")
        lines.append(f"   Scale:     {state.get('scale', '?')}")
        lines.append(f"   Gate:      {state.get('gate', 'null') or 'null'}")
        lines.append(f"   Clarify:   pending={state.get('clarification_pending', 'null')} skipped={state.get('clarification_skipped', 'false')}")
        lines.append(f"   Updated:   {state.get('updated', '?')}")

        # Bug 修复进行中（过滤 closed）
        bug_in_progress = state.get("bug_fix_in_progress")
        if bug_in_progress:
            if isinstance(bug_in_progress, dict):
                bug_in_progress = [bug_in_progress]
            if bug_in_progress:
                open_bugs = [b for b in bug_in_progress if isinstance(b, dict) and b.get("status") != "closed"]
                if open_bugs:
                    lines.append(f"   🐛 Bug 修复中: {len(open_bugs)} 个")
                    for b in open_bugs:
                        lines.append(f"      - {b.get('bug_id', '?')} ({b.get('severity', '?')}, {b.get('status', '?')}) req={b.get('req_id', '?')}")
    else:
        lines.append("   (state.json 不存在)")

    # 2. 历史 REQ 表格
    lines.append("")
    lines.append("📚 历史 REQ")
    lines.append("-" * 70)
    if not history:
        lines.append("   (无历史 REQ)")
    else:
        lines.append(f"   {'REQ ID':<10} {'状态':<12} {'Scale':<10} {'Agents':<10} {'P0':<4} {'Delivered':<12}")
        lines.append("   " + "-" * 68)
        for h in history:
            gate = h["current_gate"].strip('"') if isinstance(h["current_gate"], str) else "null"
            state_display = f"{h['state']}/{gate}" if gate != "null" else h["state"]
            delivered = (h["delivered"] or "-")[:10]
            lines.append(
                f"   {h['req_id']:<10} {state_display:<12} {h['scale']:<10} "
                f"{h['agents_completed']}/{h['agents_total']:<8} {h['defect_summary'].get('p0', 0):<4} {delivered:<12}"
            )

    # 3. 阶段计数
    lines.append("")
    lines.append("📈 阶段计数")
    lines.append("-" * 70)
    counts = {"DELIVERED": 0, "PAUSE_GATE": 0, "DRAFTING": 0, "IMPLEMENTING": 0, "TESTING": 0, "INIT": 0, "ABANDONED": 0, "OTHER": 0}
    for h in history:
        if h["state"] in counts:
            counts[h["state"]] = counts.get(h["state"], 0) + 1
        else:
            counts["OTHER"] += 1
    for k, v in counts.items():
        if v > 0:
            lines.append(f"   {k:<12} {v}")
    lines.append(f"   KG 实体:    {kg_stats['total']} 条（{len(kg_stats['by_type'])} 类型）")

    # 4. 最近反馈
    lines.append("")
    lines.append("💬 最近反馈（最近 5 条）")
    lines.append("-" * 70)
    if not feedback:
        lines.append("   (无反馈记录)")
    else:
        for fb in feedback:
            lines.append(f"   [{fb['mtime']}] {fb['file']}")
            lines.append(f"      {fb['excerpt']}")

    # 5. 下一步动作
    lines.append("")
    lines.append("➡️  下一步动作")
    lines.append("-" * 70)
    if state and state.get("bug_fix_in_progress"):
        open_bugs = [b for b in (state.get("bug_fix_in_progress") if isinstance(state.get("bug_fix_in_progress"), list) else [state.get("bug_fix_in_progress")])
                     if isinstance(b, dict) and b.get("status") != "closed"]
        if open_bugs:
            lines.append("   🐛 Bug 修复中 — 原型修代码 → 审计回归 → 关闭")
            lines.append(f"      待关闭: {open_bugs[0].get('bug_id', '?')}")
    elif state and state.get("phase") == "CLARIFYING":
        lines.append("   🚦 澄清门开启中 — 等 PM 回答 5 维度（背景/核心问题/预期范围/场景/用户）")
    elif state and state.get("gate"):
        lines.append(f"   🚦 {state.get('gate')} — 等 PM 决策（通过 / 打回 / 改需求）")
    elif state and state.get("phase") == "DELIVERED":
        lines.append("   ✅ 当前 REQ 已交付 — 跑 ./scripts/status.sh 复查历史，或说'开始新需求：XXX'启动下一个")
    elif state and state.get("phase") == "INIT":
        lines.append("   🚦 已建档 — 等待 PM 提供 initial_request.md 后启动 DRAFTING")
    else:
        lines.append("   (当前不在硬审批门上，按流程推进)")

    lines.append("")
    lines.append("=" * 70)
    lines.append("💡 快捷指令: status / 进度 / 看任务 / 我现在到哪了")
    lines.append("=" * 70)
    return "\n".join(lines)


def render_obsidian(state, history, feedback, kg_stats) -> str:
    """生成 Obsidian 任务总览笔记"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    out = []
    out.append("---")
    out.append(f"title: 任务总览")
    out.append(f"updated: {now}")
    out.append(f"data_source: scripts/render_dashboard.py")
    out.append("tags: [supervisor + reviewer + 专家组, dashboard, status]")
    out.append("---")
    out.append("")
    out.append("# 📊 supervisor·reviewer·专家组 产品工作流 · 任务总览")
    out.append("")
    out.append(f"> 自动生成于 {now} · 数据源 `scripts/render_dashboard.py`")
    out.append("")

    # 当前 REQ 卡片
    out.append("## 🔵 当前 REQ")
    out.append("")
    if state:
        out.append("| 字段 | 值 |")
        out.append("|---|---|")
        out.append(f"| ID | `{state.get('current_req', '(无)')}` |")
        out.append(f"| Phase | **{state.get('phase', '?')}** |")
        out.append(f"| Step | {state.get('step', '?') or '(无)'} |")
        out.append(f"| Scale | {state.get('scale', '?')} |")
        out.append(f"| Gate | `{state.get('gate', 'null') or 'null'}` |")
        out.append(f"| Clarification | pending=`{state.get('clarification_pending', 'null')}` skipped=`{state.get('clarification_skipped', 'false')}` |")
        out.append(f"| Updated | {state.get('updated', '?')} |")
    else:
        out.append("(state.json 不存在)")
    out.append("")

    # 历史 REQ 表格
    out.append("## 📚 历史 REQ")
    out.append("")
    if not history:
        out.append("(无历史 REQ)")
    else:
        out.append("| REQ ID | 标题 | 状态 | Gate | Scale | Agents | P0/P1/P2/P3 | Created | Delivered |")
        out.append("|---|---|---|---|---|---|---|---|---|")
        for h in history:
            gate = h["current_gate"].strip('"') if isinstance(h["current_gate"], str) and h["current_gate"] else "—"
            ds = h["defect_summary"]
            agents = f"{h['agents_completed']}/{h['agents_total']}"
            out.append(
                f"| {h['req_id']} | {h['title']} | {h['state']} | {gate} | "
                f"{h['scale']} | {agents} | "
                f"{ds.get('p0', 0)}/{ds.get('p1', 0)}/{ds.get('p2', 0)}/{ds.get('p3', 0)} | "
                f"{h['created']} | {h['delivered'] or '—'} |"
            )
    out.append("")

    # 阶段计数
    out.append("## 📈 阶段计数")
    out.append("")
    counts = {"DELIVERED": 0, "PAUSE_GATE": 0, "DRAFTING": 0, "IMPLEMENTING": 0, "TESTING": 0, "INIT": 0, "ABANDONED": 0, "OTHER": 0}
    for h in history:
        if h["state"] in counts:
            counts[h["state"]] += 1
        else:
            counts["OTHER"] += 1
    out.append("| 状态 | 数量 |")
    out.append("|---|---|")
    for k, v in counts.items():
        if v > 0:
            out.append(f"| {k} | {v} |")
    out.append(f"| KG 实体总数 | {kg_stats['total']} 条（{len(kg_stats['by_type'])} 类型） |")
    out.append("")

    # KG 详情
    if kg_stats.get("by_type"):
        out.append("### 知识图谱分布")
        out.append("")
        out.append("| 类型 | 数量 |")
        out.append("|---|---|")
        for t, n in kg_stats["by_type"].items():
            out.append(f"| {t} | {n} |")
        out.append("")

    # 最近反馈
    out.append("## 💬 最近反馈")
    out.append("")
    if not feedback:
        out.append("(无反馈记录)")
    else:
        out.append("| 时间 | 文件 | 摘要 |")
        out.append("|---|---|---|")
        for fb in feedback:
            out.append(f"| {fb['mtime']} | `{fb['file']}` | {fb['excerpt']} |")
    out.append("")

    # 状态机图
    out.append("## 🔄 状态机图")
    out.append("")
    out.append("```mermaid")
    out.append("stateDiagram-v2")
    out.append("    [*] --> INIT")
    out.append("    INIT --> CLARIFYING: scale=complex")
    out.append("    CLARIFYING --> DRAFTING: PM 答完/跳过")
    out.append("    DRAFTING --> PRD_ASSEMBLY")
    out.append("    PRD_ASSEMBLY --> REVIEWING")
    out.append("    REVIEWING --> REVISING: fail")
    out.append("    REVIEWING --> FINALIZING: pass")
    out.append("    FINALIZING --> PAUSE_GATE_方案评审门")
    out.append("    PAUSE_GATE_方案评审门 --> PROTOTYPING: light 跳过")
    out.append("    PROTOTYPING --> PAUSE_GATE_原型评审门")
    out.append("    PAUSE_GATE_原型评审门 --> IMPLEMENTING")
    out.append("    IMPLEMENTING --> TESTING")
    out.append("    TESTING --> DELIVERED")
    out.append("    DELIVERED --> [*]")
    out.append("```")
    out.append("")

    # 下一步动作
    out.append("## ➡️ 下一步动作")
    out.append("")
    if state and state.get("phase") == "CLARIFYING":
        out.append("- 🚦 **澄清门开启中** — 等 PM 回答 5 维度（背景/核心问题/预期范围/场景/用户）")
        out.append("- 答完说 `✅ 答完了`，或 `跳过澄清` 用默认值继续")
    elif state and state.get("gate"):
        out.append(f"- 🚦 **{state.get('gate')}** — 等 PM 决策（`通过` / `打回：XXX` / `改需求：XXX`）")
    elif state and state.get("phase") == "DELIVERED":
        out.append("- ✅ 当前 REQ 已交付")
        out.append("- 复查历史或启动下一个：说 `开始新需求：XXX`")
    elif state and state.get("phase") == "INIT":
        out.append("- 🚦 已建档 — 等 PM 提供 initial_request.md 后启动 DRAFTING")
    else:
        out.append("- (当前不在硬审批门上，按流程推进)")
    out.append("")

    # 链接
    out.append("## 🔗 相关笔记")
    out.append("")
    out.append("- [[概览]]")
    out.append("- [[工作流程]]")
    out.append("- [[角色说明]]")
    out.append("- [[v3.0 重构 + v3.1 澄清门]]")
    out.append("")

    return "\n".join(out)


def main():
    p = argparse.ArgumentParser(description="任务总览面板渲染器")
    p.add_argument("--obsidian", action="store_true", help="写入 Obsidian 笔记")
    p.add_argument("--json", action="store_true", help="输出 JSON")
    args = p.parse_args()

    state = load_state()
    history = load_history()
    feedback = load_recent_feedback(5)
    kg_stats = load_kg_stats()

    if args.json:
        print(json.dumps({
            "state": state,
            "history": history,
            "feedback": feedback,
            "kg_stats": kg_stats,
        }, ensure_ascii=False, indent=2))
        return

    if args.obsidian:
        content = render_obsidian(state, history, feedback, kg_stats)
        # 写 .tmp 再 mv 防半截文件
        OBSIDIAN_NOTE.parent.mkdir(parents=True, exist_ok=True)
        tmp = OBSIDIAN_NOTE.with_suffix(".md.tmp")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(OBSIDIAN_NOTE)
        print(f"✅ Obsidian 笔记已写入：{OBSIDIAN_NOTE}")
        return

    # 默认：终端
    print(render_terminal(state, history, feedback, kg_stats))


if __name__ == "__main__":
    main()