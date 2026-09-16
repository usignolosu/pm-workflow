#!/usr/bin/env python3
"""
query_kg.py — 知识图谱查询 CLI（v2.0 重写版，纯 Python 解决 shell 转义问题）

用法：
  python3 scripts/query_kg.py --type persona --scale standard
  python3 scripts/query_kg.py --entity REQ-001.PERSONA.001
  python3 scripts/query_kg.py --type scenario --keywords "审批 报销"
  python3 scripts/query_kg.py --type compliance_rule --industry 金融
  python3 scripts/query_kg.py --type agent            # Agent 契约（fallback 到 contracts/）
  python3 scripts/query_kg.py --type scale            # Scale 路由（fallback 到 contracts/）
  python3 scripts/query_kg.py                          # 默认统计

说明：Agent / Scale 定义不再冗余存进 KG 实体，查询时直接读
contracts/schema/agent_contracts.yaml 和 contracts/schema/_MACHINE/scale_routing.yaml。
"""
import argparse
import json
import sys
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]  # B仓根: scripts→skill→skills→.workbuddy→工作流-产品
INDEX = ROOT / "knowledge_graph" / "index.jsonl"
KG_DIR = ROOT / "knowledge_graph"
AGENT_CONTRACTS = ROOT / "contracts" / "schema" / "agent_contracts.yaml"
SCALE_ROUTING = ROOT / "contracts" / "schema" / "_MACHINE" / "scale_routing.yaml"


def load_index():
    if not INDEX.exists():
        print(f"❌ 索引不存在: {INDEX}", file=sys.stderr)
        print("   请先运行: python scripts/ingest_to_kg.py --rebuild-index", file=sys.stderr)
        sys.exit(1)
    entries = []
    for line in INDEX.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return entries


def cmd_entity(entries, eid, brief=False):
    """精确查一个实体"""
    entry = next((e for e in entries if e.get("id") == eid), None)
    if not entry:
        print(f"❌ entity_id '{eid}' 不在知识图谱中")
        sys.exit(1)

    if brief:
        # 摘要模式：1 行
        print(f"📌 {eid} ({entry.get('_type', '')} / {entry.get('name', '')})")
        return

    full_path = KG_DIR / entry["path"]
    print(f"📌 {eid} ({entry['_type']} / {entry.get('name', '')})")
    print("---")

    # 提取这一条实体
    import yaml
    data = yaml.safe_load(full_path.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else [data]
    for it in items:
        if it.get("id") == eid:
            print(yaml.dump(it, allow_unicode=True, sort_keys=False).rstrip())
            return
    print(f"⚠️ 索引说在 {full_path}，但 YAML 中找不到 id={eid}")


def cmd_agent_fallback(scale):
    """Agent 契约查询：直接读 contracts/schema/agent_contracts.yaml"""
    import yaml
    data = yaml.safe_load(AGENT_CONTRACTS.read_text(encoding="utf-8"))
    agents = data.get("agents", [])
    print(f"🔍 Agent 契约（来源 contracts/schema/agent_contracts.yaml，共 {len(agents)} 个）")
    print("---")
    for a in agents:
        out_file = a.get("output", {}).get("file", "?")
        print(f"  {a.get('id', '?'):12} {a.get('name_cn', ''):6} {a.get('name_en', ''):18} → {out_file}")
        if scale:
            for sec in a.get("output", {}).get("required_sections", []):
                mc = sec.get("min_count_by_scale", {})
                if scale in mc:
                    print(f"      {sec.get('name', '?')}: {scale} ≥ {mc[scale]}")
    print("---")


def cmd_scale_fallback(scale):
    """Scale 路由查询：直接读 contracts/schema/_MACHINE/scale_routing.yaml"""
    import yaml
    data = yaml.safe_load(SCALE_ROUTING.read_text(encoding="utf-8"))

    def dump(node, indent=2):
        for k, v in node.items():
            if isinstance(v, dict):
                print(" " * indent + f"{k}:")
                dump(v, indent + 2)
            elif isinstance(v, list):
                print(" " * indent + f"{k}:")
                for it in v:
                    print(" " * (indent + 2) + f"- {it}")
            else:
                print(" " * indent + f"{k}: {v}")

    levels = data.get("scales") or data.get("levels") or {}
    if isinstance(levels, list):
        levels = {s.get("id", "?"): s for s in levels if isinstance(s, dict)}
    targets = {scale: levels[scale]} if scale and scale in levels else levels
    label = f"（scale={scale}）" if scale else ""
    print(f"🔍 Scale 路由{label}（来源 contracts/schema/_MACHINE/scale_routing.yaml）")
    print("---")
    for k, v in targets.items():
        print(f"  [{k}]")
        dump(v if isinstance(v, dict) else {"value": v}, 4)
    print("---")


def cmd_type(entries, etype, keywords, scale, industry, brief=False, count_only=False):
    """按类型查（大小写不敏感）"""
    etype_lower = etype.lower()

    # v4.0.1：scale 过滤真正实现——通过 req_id 前缀（如 REQ-001 = standard 时代）
    # 历史 REQ scale 对照表（v2.0 contracts scale 定义）
    REQ_SCALE = {
        "REQ-001": "standard",
        "REQ-002": "standard",
        "示例REQ-A": "standard",
        "示例REQ-B": "complex",
        "REQ-005": "complex",
    }

    if count_only:
        n = sum(
            1 for e in entries
            if e.get("_type", "").lower() == etype_lower
            and (not scale or REQ_SCALE.get(e.get("req_id", ""), "") == scale)
        )
        print(f"📊 type={etype}" + (f" scale={scale}" if scale else "") + f": {n} 条")
        return

    print(f"🔍 查 type={etype}"
          + (f" scale={scale}" if scale else "")
          + (f" keywords=\"{keywords}\"" if keywords else "")
          + (f" industry={industry}" if industry else ""))
    print("---")

    count = 0
    kws = keywords.split() if keywords else []

    for e in entries:
        if e.get("_type", "").lower() != etype_lower:
            continue
        # scale 过滤：检查 req_id 对应 scale
        if scale and REQ_SCALE.get(e.get("req_id", ""), "") != scale:
            continue

        # 关键词过滤：拆词 OR 匹配（搜 YAML 文件全文）
        if kws:
            full_path = KG_DIR / e["path"]
            if not full_path.exists():
                continue
            content = full_path.read_text(encoding="utf-8")
            if not any(kw in content for kw in kws):
                continue

        eid = e.get("id", "?")
        name = e.get("name", "")
        print(f"  {eid:30}  —  {name}")
        count += 1

    print("---")
    print(f"共 {count} 条")


def cmd_stats(entries):
    """默认统计"""
    from collections import Counter
    c = Counter(e["_type"] for e in entries)
    print("📊 知识图谱统计")
    print("---")
    print(f"总条目数: {len(entries)}")
    print()
    print("按类型分组:")
    for t, n in sorted(c.items(), key=lambda x: -x[1]):
        print(f"  {t:20} {n:4d}")


def main():
    p = argparse.ArgumentParser(description="知识图谱查询 CLI")
    p.add_argument("--type", help="按实体类型查（Persona/Scenario/Insight/FR/...）")
    p.add_argument("--entity", help="按 entity_id 精确查")
    p.add_argument("--keywords", help="按关键词过滤（空格分隔 OR 匹配）")
    p.add_argument("--scale", choices=["light", "standard", "complex"], help="按 scale 过滤（当前未实现，仅占位）")
    p.add_argument("--industry", help="按行业过滤（仅 compliance_rule 用）")
    p.add_argument("--brief", action="store_true", help="仅输出一行摘要（id + name + 描述首行），不输出完整 YAML")
    p.add_argument("--count-only", action="store_true", help="仅输出数量，不列实体")
    args = p.parse_args()

    entries = load_index()

    if args.entity:
        cmd_entity(entries, args.entity, brief=args.brief)
    elif args.type and args.type.lower() == "agent":
        cmd_agent_fallback(args.scale)
    elif args.type and args.type.lower() == "scale":
        cmd_scale_fallback(args.scale)
    elif args.type:
        cmd_type(entries, args.type, args.keywords, args.scale, args.industry,
                 brief=args.brief, count_only=args.count_only)
    else:
        cmd_stats(entries)


if __name__ == "__main__":
    main()