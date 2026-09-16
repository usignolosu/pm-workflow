#!/usr/bin/env python3
"""
validate_contract.py — 契约自动校验器（v2.0）

校验流程：
  Step 0: 加载契约定义（YAML）
  Step 1: 定位待校验文件
  Step 2: 文件命名校验
  Step 3: 必填章节校验
  Step 4: 最小数量校验（按 scale）
  Step 5: 通用防线校验（13 条）
  Step 6: 专用防线校验（按 agent）
  Step 7: 知识图谱引用校验
  Step 8: PRD 格式校验（仅 shangshu）
  Step 9: 汇总输出

用法：
  python scripts/validate_contract.py --req REQ-005 --agent libu
  python scripts/validate_contract.py --req REQ-005 --agent all
  python scripts/validate_contract.py --file <path> --agent libu --scale standard
  python scripts/validate_contract.py --req REQ-005 --agent libu --strictness warn
  python scripts/validate_contract.py --req REQ-005 --agent libu --json
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

try:
    import yaml
except ImportError:
    print("ERROR: 需要安装 PyYAML。运行: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

# 让脚本能导入 guardrail_checkers
sys.path.insert(0, str(Path(__file__).parent))
from guardrail_checkers import eval_guardrail, EVALUATORS


ROOT = Path(__file__).resolve().parents[4]  # B仓根: scripts→skill→skills→.workbuddy→工作流-产品
CONTRACTS_DIR = ROOT / "contracts" / "schema"
KG_INDEX = ROOT / "knowledge_graph" / "index.jsonl"


# ============================================================================
# 数据加载
# ============================================================================

def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_contracts() -> Dict:
    machine = CONTRACTS_DIR / "_MACHINE"
    return {
        "versioning": load_yaml(machine / "versioning.yaml"),
        "guardrails": load_yaml(CONTRACTS_DIR / "guardrails.yaml"),
        "load_order": load_yaml(CONTRACTS_DIR / "load_order.yaml"),
        "scale_routing": load_yaml(machine / "scale_routing.yaml"),
        "agent_contracts": load_yaml(CONTRACTS_DIR / "agent_contracts.yaml"),
        "kg_contract": load_yaml(CONTRACTS_DIR / "kg_contract.yaml"),
        "validation_rules": load_yaml(machine / "validation_rules.yaml"),
    }


def load_kg_index() -> Dict[str, Dict]:
    """返回 {entity_id: entity_dict}"""
    if not KG_INDEX.exists():
        return {}
    index = {}
    for line in KG_INDEX.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            e = json.loads(line)
            index[e["id"]] = e
        except json.JSONDecodeError:
            pass
    return index


# ============================================================================
# Violation 对象
# ============================================================================

class Violation:
    def __init__(self, rule_id, severity, line, evidence, fix, guardrail_ref=None):
        self.rule_id = rule_id
        self.severity = severity
        self.line = line
        self.evidence = evidence
        self.fix = fix
        self.guardrail_ref = guardrail_ref

    def to_dict(self):
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "line": self.line,
            "evidence": self.evidence,
            "fix": self.fix,
            "guardrail_ref": self.guardrail_ref,
        }


# ============================================================================
# 校验函数
# ============================================================================

def check_file_naming(file_path: Path, agent_contract: dict, req_id: str) -> List[Violation]:
    """Step 2: 文件命名校验"""
    violations = []
    output = agent_contract.get("output", {})
    expected = output.get("file") or (output.get("files", [{}])[0].get("path") if output.get("files") else None)

    if not expected:
        return violations

    # 替换模板变量
    expected_norm = expected.replace("${req_id}", req_id)
    if expected_norm not in str(file_path):
        violations.append(Violation(
            "file_naming", "P0", 0,
            f"文件路径 {file_path.name} 不符合契约 {expected_norm}",
            f"检查路径是否正确",
            guardrail_ref="file_naming"
        ))
    return violations


def check_required_sections(content: str, agent_contract: dict, scale: str) -> List[Violation]:
    """Step 3: 必填章节校验"""
    violations = []
    required = agent_contract.get("output", {}).get("required_sections", [])
    for section in required:
        name = section.get("name", "")
        # 检查二级或三级标题
        if f"## {name}" not in content and f"### {name}" not in content:
            violations.append(Violation(
                "required_sections", "P0", 0,
                f"缺失必填章节: ## {name}",
                f"在产出中添加 '## {name}' 章节",
                guardrail_ref="required_sections"
            ))

        # Step 4: 最小数量校验
        min_count = section.get("min_count_by_scale", {}).get(scale)
        if min_count:
            # 启发式：找 ### 画像 N / ### 场景 N / ### 洞察 N
            count = len([line for line in content.splitlines()
                         if re.match(r"^###\s*(画像|场景|洞察|典型场景|FR)[-:\s]*\d+", line.strip())])
            # 简化：如果有多个 ### 子标题且数量不足
            subsection_count = content.count("### ")
            if min_count > 1 and subsection_count < min_count:
                violations.append(Violation(
                    "min_counts", "P0", 0,
                    f"## {name} 下子章节数 {subsection_count} < scale={scale} 最低要求 {min_count}",
                    f"补充至至少 {min_count} 个子章节",
                    guardrail_ref="min_counts"
                ))
    return violations


import re


def check_universal_guardrails(content: str, agent: str, scale: str, kg_index: dict, strictness: str, is_legacy: bool) -> List[Violation]:
    """Step 5: 通用防线校验（13 + 1 条）"""
    violations = []
    guardrails = load_contracts()["guardrails"]["universal"]

    for g in guardrails:
        gid = g["id"]
        applies_to_scale = g.get("applies_to_scale", [])
        if applies_to_scale and scale not in applies_to_scale:
            continue

        # 跳过历史 REQ 的 waived_for_legacy 规则
        if is_legacy and g.get("waived_for_legacy"):
            continue

        # 跳过不属于该 agent 的防线
        applies_to = g.get("applies_to", ["all"])
        if "all" not in applies_to and agent not in applies_to:
            continue

        # 流程层/跨文件防线（machine_check: false）由reviewer人工执行
        if g.get("machine_check") is False:
            continue

        result = eval_guardrail(gid, content, agent=agent, scale=scale, kg_index=kg_index)

        if result.get("unimplemented"):
            violations.append(Violation(
                gid, "P1", 0,
                f"未实现 checker: {gid}",
                "scripts/guardrail_checkers.py 中实现",
                guardrail_ref=gid
            ))
            continue

        if result.get("error"):
            violations.append(Violation(
                gid, "P1", 0,
                f"checker 异常: {result.get('evidence')}",
                "修复 guardrail_checkers.py",
                guardrail_ref=gid
            ))
            continue

        if not result["pass"]:
            violations.append(Violation(
                gid, g.get("severity", "P0"), result["line"],
                result["evidence"],
                result["fix"],
                guardrail_ref=gid
            ))

    return violations


def check_agent_specific_guardrails(content: str, agent: str, strictness: str) -> List[Violation]:
    """Step 6: 专用防线校验"""
    violations = []
    guardrails = load_contracts()["guardrails"]["agent_specific"]

    for g in guardrails:
        if g.get("agent") != agent:
            continue
        result = eval_guardrail(g["id"], content, agent=agent)
        if not result["pass"]:
            violations.append(Violation(
                g["id"], g.get("severity", "P0"), result["line"],
                result["evidence"], result["fix"],
                guardrail_ref=g["id"]
            ))

    return violations


def check_prd_format(content: str) -> List[Violation]:
    """Step 8: PRD 10 章结构（仅 shangshu）"""
    violations = []
    prd_template = load_yaml(ROOT / "contracts" / "prd_template" / "prd_10ch.yaml")
    for ch in prd_template["chapters"]:
        if not ch.get("required"):
            continue
        num, name = ch["num"], ch["name"]
        # 检查 ## X. 名称 或 ## 名称
        patterns = [f"## {num}. {name}", f"## {name}", f"# {num}. {name}"]
        if not any(p in content for p in patterns):
            violations.append(Violation(
                "prd_format", "P0", 0,
                f"PRD 缺失第 {num} 章: {name}",
                f"添加 '## {num}. {name}' 章节",
                guardrail_ref="prd_format"
            ))
    return violations


def check_spec_quality(content: str, scale: str) -> List[Violation]:
    """Step 10: Spec 质量门（v6.0 P2-1，仅 shangshu 合并稿 PRD）"""
    violations = []
    checklist = (load_yaml(ROOT / "contracts" / "spec_checklist.yaml") or {}).get("checklist", [])
    for item in checklist:
        if not item.get("machine"):
            continue
        req_scale = item.get("scale_required")
        if req_scale and scale not in req_scale:
            continue
        sid, name, hint = item["id"], item["name"], item.get("fail_hint", "")
        ok = True
        if sid == "s002":
            acs = re.findall(r"AC-\d+", content)
            ok = len(acs) >= 3 and ("系统应" in content or "THE SYSTEM SHALL" in content.upper())
        elif sid == "s003":
            ok = len(re.findall(r"US-\d+", content)) >= 3
        elif sid == "s004":
            frs = re.findall(r"FR-(\d+)", content)
            ok = len(frs) == len(set(frs))
        elif sid == "s005":
            ok = bool(re.search(r"(POST|GET|PUT|DELETE)\s+/|API 契约|错误码", content))
        if not ok:
            violations.append(Violation(
                f"spec_{sid}", "P1", 0,
                f"Spec 质量门未过 [{name}]: {item['check']}",
                hint, guardrail_ref=f"spec_{sid}"
            ))
    return violations


# ============================================================================
# 主流程
# ============================================================================

def validate_file(file_path: Path, agent: str, scale: str, strictness: str, req_id: str,
                  merged_prd: bool = False) -> Dict:
    contracts = load_contracts()
    kg_index = load_kg_index()

    # 检查 legacy waiver
    legacy_waivers = contracts["versioning"].get("legacy_waivers", {})
    waived_reqs = legacy_waivers.get("applies_to_req_ids", [])
    is_legacy = req_id in waived_reqs

    content = file_path.read_text(encoding="utf-8")
    agent_contract = next(
        (a for a in contracts["agent_contracts"]["agents"] if a["id"] == agent),
        None,
    )
    if not agent_contract:
        return {
            "file": str(file_path),
            "agent": agent,
            "scale": scale,
            "verdict": "fail",
            "violations": [Violation("config", "P0", 0, f"未知 agent: {agent}", "检查 --agent 参数").to_dict()],
            "pass_count": 0, "fail_count": 1, "warn_count": 0,
            "is_legacy": is_legacy,
        }

    violations = []
    # v4.0.1 修复：合并稿模式或 --file 模式 + prd.md 合并稿，跳过 file_naming 校验
    merged_prd_mode = merged_prd
    standard_names = {
        "01_user_research.md", "02_strategy_and_risk.md", "03_metrics_and_value.md",
        "04_compliance.md", "05_solution.md", "06_audit_report.md",
        "review.md", "final_prd.md",
    }
    is_merged_file = file_path.name in {"prd.md", "final_prd.md"} and (
        merged_prd_mode or file_path.name == "final_prd.md"
    )
    file_mode = file_path.name not in standard_names
    if file_mode or is_merged_file:
        # 合并稿或 --file 模式指向非契约标准文件名：跳过 file_naming 校验
        pass
    else:
        violations += check_file_naming(file_path, agent_contract, req_id)
    violations += check_required_sections(content, agent_contract, scale)
    violations += check_universal_guardrails(content, agent, scale, kg_index, strictness, is_legacy)
    violations += check_agent_specific_guardrails(content, agent, strictness)
    if agent == "shangshu":
        violations += check_prd_format(content)
        if file_path.name in {"prd.md", "final_prd.md"}:
            violations += check_spec_quality(content, scale)

    # 应用 strictness
    fail_severities = {"off": [], "warn": ["P1", "P2", "P3"], "strict": ["P0", "P1"]}.get(strictness, [])

    fail_count = sum(1 for v in violations if v.severity in fail_severities)
    warn_count = sum(1 for v in violations if v.severity not in fail_severities and v.severity in ["P1", "P2", "P3"])
    pass_count = max(0, len(EVALUATORS) - len(violations))

    verdict = "fail" if fail_count > 0 else ("warn" if warn_count > 0 else "pass")

    return {
        "file": str(file_path),
        "agent": agent,
        "scale": scale,
        "verdict": verdict,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "warn_count": warn_count,
        "violations": [v.to_dict() for v in violations],
        "is_legacy": is_legacy,
    }


def main():
    parser = argparse.ArgumentParser(description="契约自动校验器（v2.0）")
    parser.add_argument("--req", help="REQ ID, e.g. REQ-005")
    parser.add_argument("--file", help="直接指定文件路径")
    parser.add_argument("--agent", required=True, help="agent slug (libu/bingbu/...)")
    parser.add_argument("--scale", choices=["light", "standard", "complex"], default="standard")
    parser.add_argument("--strictness", choices=["off", "warn", "strict"], default="off")
    parser.add_argument("--merged-prd", action="store_true",
                        help="v4.0.1：REQ 走合并稿模式（prd.md 单文件而非 01_~05_ 子文件）")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    # 定位文件
    if args.file:
        file_path = Path(args.file)
        req_id = args.req or "UNKNOWN"
    elif args.req:
        contracts = load_contracts()
        agent_contract = next(
            (a for a in contracts["agent_contracts"]["agents"] if a["id"] == args.agent),
            None,
        )
        if not agent_contract:
            print(f"ERROR: 未知 agent '{args.agent}'", file=sys.stderr)
            sys.exit(2)
        # 原型 A1/A2/B 等不同角色文件路径不同，这里默认 A1 (05_solution.md)
        output = agent_contract.get("output", {})
        # v4.0.1 合并稿模式：所有非reviewer/supervisor agent 都指向 prd.md
        if args.merged_prd and args.agent not in ("menxia", "shangshu", "xingbu"):
            file_template = "归档需求产出/${req_id}/01_drafted/prd.md"
        elif args.agent == "gongbu":
            file_template = "归档需求产出/${req_id}/01_drafted/05_solution.md"
        elif args.agent == "libu":
            file_template = "归档需求产出/${req_id}/01_drafted/01_user_research.md"
        elif args.agent == "bingbu":
            file_template = "归档需求产出/${req_id}/01_drafted/02_strategy_and_risk.md"
        elif args.agent == "hubu":
            file_template = "归档需求产出/${req_id}/01_drafted/03_metrics_and_value.md"
        elif args.agent == "libu_compliance":
            file_template = "归档需求产出/${req_id}/01_drafted/04_compliance.md"
        elif args.agent == "xingbu":
            file_template = "归档需求产出/${req_id}/01_drafted/06_audit_report.md"
        elif args.agent == "menxia":
            file_template = "归档需求产出/${req_id}/02_reviewed/review.md"
        elif args.agent == "shangshu":
            file_template = "归档需求产出/${req_id}/03_finalized/final_prd.md"
        else:
            file_template = output.get("file") or "归档需求产出/${req_id}/01_drafted/UNKNOWN.md"
        file_path = ROOT / file_template.replace("${req_id}", args.req)
        req_id = args.req
    else:
        print("ERROR: 必须提供 --req 或 --file", file=sys.stderr)
        sys.exit(2)

    if not file_path.exists():
        print(f"❌ 文件不存在: {file_path}", file=sys.stderr)
        sys.exit(2)

    result = validate_file(file_path, args.agent, args.scale, args.strictness, req_id,
                            merged_prd=args.merged_prd)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        icon = {"pass": "✅", "warn": "⚠️", "fail": "❌"}[result["verdict"]]
        legacy_note = " [LEGACY WAIVER applied]" if result["is_legacy"] else ""
        print(f"{icon} {result['verdict'].upper()}  {Path(result['file']).name}  "
              f"(scale={args.scale}, strictness={args.strictness}){legacy_note}")
        print(f"   pass={result['pass_count']}  fail={result['fail_count']}  warn={result['warn_count']}")
        for v in result["violations"]:
            ref = f"[{v['guardrail_ref']}]" if v.get("guardrail_ref") else ""
            print(f"   {v['severity']}  {v['rule_id']:20}  L{v['line']:3}  {ref}")
            print(f"      evidence: {v['evidence']}")
            print(f"      fix:      {v['fix']}")
        # 项目宪法（人工对照，不参与机器判定）
        constitution = load_yaml(CONTRACTS_DIR.parent / "constitution.yaml")
        principles = (constitution or {}).get("constitution", [])
        if principles:
            print(f"   📋 项目宪法 {len(principles)} 条已加载（reviewer人工对照，见 contracts/constitution.yaml）")

    # exit code: 0=pass, 1=warn, 2=fail
    sys.exit({"pass": 0, "warn": 1, "fail": 2}[result["verdict"]])


if __name__ == "__main__":
    main()