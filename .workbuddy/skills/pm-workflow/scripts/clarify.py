#!/usr/bin/env python3
"""
clarify.py — 需求澄清门 CLI（v5.0 精简版）

5 个 action 共享 _read_state / _save_state / _output_path 3 个工具。
模板填充 + 状态切换压缩成 _set_phase。
"""
import argparse
import os
import json
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("ERROR: 需要 PyYAML")

ROOT = Path(__file__).resolve().parents[4]  # B仓根: scripts→skill→skills→.workbuddy→工作流-产品
QUESTIONS_YAML = ROOT / "workflow" / "clarification_questions.yaml"
TEMPLATE = ROOT / "templates" / "clarification.md"
# Route X：活动需求目录改指 runs/<run-id>/（不再写根级 归档需求产出/），state.json 随 run 隔离

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


# ========== 工具 ==========
def _state_path(req_id):
    return RUNS / req_id / "state.json"


def _read_state(req_id):
    p = _state_path(req_id)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _save_state(req_id, state):
    p = _state_path(req_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _output_path(req_id):
    return RUNS / req_id / "01_drafted" / "01_clarifications.md"


def _load_questions():
    return yaml.safe_load(QUESTIONS_YAML.read_text(encoding="utf-8"))


def _set_phase(req_id, state, phase, skipped):
    """统一处理状态切换"""
    state["phase"] = phase
    state["clarification_pending"] = None
    state["clarification_skipped"] = skipped
    state["step"] = "起草准备"
    state["updated"] = datetime.now().isoformat()
    _save_state(req_id, state)


def _check_answers(md_path):
    """检查哪些维度已答完，返回 answered 维度 id 集合"""
    if not md_path.exists():
        return set()
    content = md_path.read_text(encoding="utf-8")
    q = _load_questions()
    answered = set()
    for d in q["dimensions"]:
        m = re.search(rf"## \d+\.\s*{d['label']}.*?(?=##|\Z)", content, re.DOTALL)
        if not m:
            continue
        section = m.group(0)
        if "PM 答复：" in section and re.search(r"PM 答复[：:]\s*(?:<[^>]+>)?\s*$", section, re.MULTILINE):
            continue
        m2 = re.search(r"PM 答复[：:]\s*([^\n<]+)", section)
        if m2 and m2.group(1).strip():
            answered.add(d["id"])
    return answered


# ========== 5 个 action ==========
def action_init(req_id):
    out = _output_path(req_id)
    out.parent.mkdir(parents=True, exist_ok=True)
    content = TEMPLATE.read_text(encoding="utf-8")
    content = content.replace("REQ-XXX", req_id)
    content = content.replace("YYYY-MM-DD HH:MM", datetime.now().strftime("%Y-%m-%d %H:%M"))
    out.write_text(content, encoding="utf-8")
    print(f"✅ 已生成 {out}")


def action_show(req_id):
    q = _load_questions()
    print(f"📋 澄清问题清单（{req_id}）\n" + "=" * 60)
    for d in q["dimensions"]:
        print(f"\n## {d['id']}. {d['label']}（{'必填' if d.get('required') else '选填'}）")
        print(f"   Q: {d['question']}")
        if d.get("why_ask"):
            print(f"   Why: {d['why_ask']}")
    print("\n" + "=" * 60 + "\n回复方式：")
    print("  - '回答 1：背景 = ...'\n  - '✅ 答完了'\n  - '跳过澄清'\n  - '清单再看一下'")
    out = _output_path(req_id)
    if out.exists():
        answered = _check_answers(out)
        print(f"\n当前 {out.name}:")
        for d in q["dimensions"]:
            mark = "✅" if d["id"] in answered else "❌"
            print(f"  {mark} {d['label']}")


def action_submit(req_id, answers_file):
    out = _output_path(req_id)
    if not out.exists():
        sys.exit(f"❌ {out} 不存在，先跑 init")
    answers_content = Path(answers_file).read_text(encoding="utf-8")
    current = out.read_text(encoding="utf-8")
    q = _load_questions()

    for d in q["dimensions"]:
        ans_match = re.search(rf"## \d+\.\s*{d['label']}.*?(?=##|\Z)", answers_content, re.DOTALL)
        if not ans_match:
            continue
        ans_match2 = re.search(r"PM 答复[：:]\s*([^\n<]+)", ans_match.group(0))
        if not ans_match2 or not ans_match2.group(1).strip():
            continue
        answer = ans_match2.group(1).strip()
        cur_pattern = rf"(## \d+\.\s*{d['label']}.*?PM 答复[：:])\s*(?:<[^>]+>)?"
        cur_match = re.search(cur_pattern, current, re.DOTALL)
        if cur_match:
            current = current.replace(cur_match.group(0), cur_match.group(1) + " " + answer, 1)

    out.write_text(current, encoding="utf-8")
    answered = _check_answers(out)
    print(f"✅ 答复已写入 {out}\n   已答 {len(answered)}/5 维度：{answered}")

    if len(answered) == 5:
        _set_phase(_read_state(), "DRAFTING", False)
        print("✅ 5 维度全答完，进入 DRAFTING")
    else:
        print(f"⚠️ 还有 {5 - len(answered)} 维度未答，可继续回答或'✅ 答完了'")


def action_skip(req_id):
    _set_phase(_read_state(), "DRAFTING", True)
    # 同步 01_clarifications.md 和 INDEX.md 的 clarification_skipped 标记
    req_dir = RUNS / req_id / "01_drafted"
    for name in ("01_clarifications.md", "INDEX.md"):
        f = req_dir / name
        if not f.exists():
            continue
        content = re.sub(r"clarification_skipped:\s*`?[a-z]+`?", "clarification_skipped: true", f.read_text(encoding="utf-8"))
        f.write_text(content, encoding="utf-8")
    print(f"✅ {req_id} 澄清门已跳过（clarification_skipped=true），进入 DRAFTING")


def action_check(req_id):
    state = _read_state(req_id)
    out = _output_path(req_id)
    answered = _check_answers(out) if out.exists() else set()
    print(f"📊 {req_id} 澄清门状态")
    print(f"   state.clarification_pending: {state.get('clarification_pending', 'null')}")
    print(f"   state.clarification_skipped: {state.get('clarification_skipped', 'false')}")
    print(f"   state.clarification_mode: {state.get('clarification_mode', 'scale-dependent')}")
    print(f"   01_clarifications.md: {'存在' if out.exists() else '不存在'}")
    print(f"   已答维度: {len(answered)}/5 ({answered})")
    if state.get("clarification_pending") == "clarification":
        if len(answered) == 5:
            print("\n💡 建议：'✅ 答完了' 进入 DRAFTING")
        else:
            print(f"\n💡 建议：回答剩余 {5 - len(answered)} 维度，或'跳过澄清'")


def main():
    p = argparse.ArgumentParser(description="需求澄清门 CLI")
    p.add_argument("--req", required=True, help="REQ ID")
    p.add_argument("action", choices=["init", "show", "submit", "skip", "check"])
    p.add_argument("--file", help="submit 模式的答复文件路径")
    args = p.parse_args()

    actions = {
        "init": lambda: action_init(args.req),
        "show": lambda: action_show(args.req),
        "submit": action_submit if args.file else (
            lambda: sys.exit("ERROR: submit 模式必须 --file")),
        "skip": lambda: action_skip(args.req),
        "check": lambda: action_check(args.req),
    }
    if args.action == "submit" and not args.file:
        sys.exit("ERROR: submit 模式必须 --file")
    actions[args.action]()


if __name__ == "__main__":
    main()
