#!/usr/bin/env python3
"""
ingest_to_kg.py — 把 REQ 产物入库到知识图谱（v5.0 精简版）

用 8 个轻量 extractor 抽 11 类实体。结构：
  - 3 个原 extractor（Persona/Scenario/Insight，01_user_research.md）
  - 6 个新 extractor（FR/NFR/Metric/Compliance/Tech/Risk/Annotation）
  - 2 个工具函数（_get_section / _get_field）

用法：
  python scripts/ingest_to_kg.py --req REQ-005 --mode semi-auto
  python scripts/ingest_to_kg.py --rebuild-index
"""
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("ERROR: 需要 PyYAML")

ROOT = Path(__file__).resolve().parents[4]  # B仓根: scripts→skill→skills→.workbuddy→工作流-产品
KG_DIR = ROOT / "knowledge_graph"
LEGACY_DIR = KG_DIR / "legacy"
INDEX = KG_DIR / "index.jsonl"

# 类型 → 文件名映射
TYPE_TO_FILE = {
    "Persona": "personas.yaml", "Scenario": "scenarios.yaml",
    "Insight": "insights.yaml", "FR": "fr.yaml", "NFR": "nfr.yaml",
    "Metric": "metrics.yaml", "ComplianceRule": "compliance.yaml",
    "TechComponent": "tech.yaml", "Risk": "risks.yaml",
    "Annotation": "annotations.yaml",
}


# ========== 工具 ==========
def _read(md_path):
    return md_path.read_text(encoding="utf-8") if md_path.exists() else ""


def _section(content, heading_regex):
    """取 ## 标题后的内容到下一个 ## 为止"""
    m = re.search(heading_regex, content)
    if not m:
        return ""
    rest = content[m.end():]
    end = re.search(r"\n## ", rest)
    return rest[: end.start()] if end else rest


def _field(body, label):
    m = re.search(rf"[-*]?\s*\*\*{label}[*：:]\*\*\s*([^\n]+)", body)
    return m.group(1).strip() if m else None


def _list_field(body, label):
    """多值字段：按顿号/逗号/分号/换行 split"""
    v = _field(body, label)
    return [s.strip() for s in re.split(r"[、,，;；\n]", v) if s.strip()] if v else []


def _make_entity(etype, req_id, fields, source):
    """实体工厂"""
    fields.setdefault("created", "auto-ingest")
    fields.setdefault("status", "active")
    fields.setdefault("confidence", 0.7)
    fields["_type"] = etype
    fields["req_id"] = req_id
    fields["source"] = source
    return fields


# ========== 3 个原 extractor（01_user_research.md） ==========
def extract_personas(content, req_id, source):
    entities = []
    section = _section(content, r"##\s*用户画像")
    for seq, m in enumerate(re.finditer(r"###\s*画像\s*\d+[:：]\s*([^\n]+)", section), 1):
        start, body = m.end(), section[m.end():]
        next_m = re.search(r"###\s*画像\s*\d+", body)
        body = body[: next_m.start()] if next_m else ""
        entities.append(_make_entity("Persona", req_id, {
            "id": f"{req_id}.PERSONA.{seq:03d}",
            "name": m.group(1).strip(), "name_cn": m.group(1).strip(),
            "core_need": _field(body, "核心诉求"),
            "pain_points": _list_field(body, "痛点"),
            "alternatives": _field(body, "现有替代方案") or _field(body, "替代方案"),
        }, source))
    return entities


def extract_scenarios(content, req_id, source):
    entities = []
    section = _section(content, r"##\s*典型场景")
    for seq, m in enumerate(re.finditer(r"###\s*场景\s*[A-Z\d]+[:：]\s*([^\n]+)", section), 1):
        start, body = m.end(), section[m.end():]
        next_m = re.search(r"###\s*场景", body)
        body = body[: next_m.start()] if next_m else ""
        entities.append(_make_entity("Scenario", req_id, {
            "id": f"{req_id}.SCENARIO.{seq:03d}",
            "name": m.group(1).strip(),
            "trigger": _field(body, "触发") or _field(body, "触发条件"),
            "flow": _list_field(body, "流程") or _list_field(body, "完整流程"),
            "expected_result": _field(body, "期望") or _field(body, "期望结果"),
            "failure_points": _list_field(body, "失败点") or _list_field(body, "可能的失败点"),
        }, source))
    return entities


def extract_insights(content, req_id, source):
    entities = []
    section = _section(content, r"##\s*关键洞察")
    for seq, m in enumerate(re.finditer(r"[-*]\s*\*\*(HIGH|MED|LOW|洞察\s*\d+|\w+)[*：:]\*\*\s*([^\n]+)", section), 1):
        importance = m.group(1).strip()
        rest = section[m.end():]
        next_m = re.search(r"[-*]\s*\*\*", rest)
        body = rest[: next_m.start()] if next_m else ""
        counter_m = re.search(r"反例[：:]\s*([^\n]+)", body)
        entities.append(_make_entity("Insight", req_id, {
            "id": f"{req_id}.INSIGHT.{seq:03d}",
            "text": m.group(2).strip(),
            "importance": importance if importance in ("HIGH",", ", "LOW") else "MED",
            "counter_example": counter_m.group(1).strip() if counter_m else None,
        }, source))
    return entities


# ========== 6 个新 extractor ==========
def extract_frs(content, req_id, source):
    """FR + NFR：从 02_strategy_and_risk.md 表格"""
    entities = []
    for sec in [_section(content, r"##\s*(?:功能需求|FR|功能清单)\b"),
                _section(content, r"##\s*(?:非功能需求|NFR)\b")]:
        for seq, row in enumerate(re.finditer(
            r"\|\s*(FR|NFR)[-#]?(\d+)\s*\|([^|]+)\|[^|]*\|[^|]*\|\s*(P\d)", sec), 1):
            is_nfr = row.group(1) == "NFR"
            etype = "NFR" if is_nfr else "FR"
            cols = row.group(0).split("|")
            entities.append(_make_entity(etype, req_id, {
                "id": f"{req_id}.{etype}.{seq:03d}",
                "code": f"{'NFR' if is_nfr else 'FR'}-{row.group(2)}",
                "name": cols[2].strip() if len(cols) > 2 else "",
                "priority": row.group(4),
            }, source))
    return entities


def extract_metrics(content, req_id, source):
    """Metric：从 03_metrics_and_value.md 抽北极星 + 过程指标"""
    entities = []
    seq = 0
    north = _section(content, r"##\s*北极星指标\b")
    if north:
        m = re.search(r"###\s+([^\n]+)", north)
        if m:
            seq += 1
            body = north[m.end():]
            entities.append(_make_entity("Metric", req_id, {
                "id": f"{req_id}.METRIC.{seq:03d}",
                "name": m.group(1).strip(),
                "formula": _field(body, "计算公式") or _field(body, "公式"),
                "data_source": _field(body, "数据来源"),
                "target_value": _field(body, "目标值") or _field(body, "启动期目标值"),
                "north_star": True,
            }, source))
    proc = _section(content, r"##\s*过程指标\b")
    for m in re.finditer(r"###\s+(P\d[:：][^\n]+)", proc):
        seq += 1
        body = proc[m.end():]
        next_m = re.search(r"\n###", body)
        body = body[: next_m.start()] if next_m else ""
        entities.append(_make_entity("Metric", req_id, {
            "id": f"{req_id}.METRIC.{seq:03d}",
            "name": m.group(1).strip(),
            "formula": _field(body, "公式"),
            "data_source": _field(body, "数据来源"),
            "frequency": _field(body, "频率"),
            "target_value": _field(body, "目标"),
            "north_star": False,
        }, source))
    return entities


def extract_compliance(content, req_id, source):
    """ComplianceRule：从 04_compliance.md 各 ## 段下的 ### 子节"""
    entities = []
    seq = 0
    decision = next((d for d in ("PASS", "NEEDS_REVIEW", "BLOCK") if d in content), "UNKNOWN")
    for heading in [r"##\s*行业合规\b", r"##\s*数据隐私评估\b",
                    r"##\s*伦理审查\b", r"##\s*品牌一致性\b"]:
        for m in re.finditer(r"###\s+([^\n]+)", _section(content, heading)):
            seq += 1
            entities.append(_make_entity("ComplianceRule", req_id, {
                "id": f"{req_id}.COMPLIANCE.{seq:03d}",
                "name": m.group(1).strip(),
                "judgment": decision,
                "confidence": 0.6,
            }, source))
    return entities


def extract_tech(content, req_id, source):
    """TechComponent：从 05_solution.md ## 技术选型 表格"""
    entities = []
    seq = 0
    for row in re.finditer(r"\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|",
                             _section(content, r"##\s*技术选型\b")):
        cat, name, reason = row.group(1).strip(), row.group(2).strip(), row.group(3).strip()
        if cat in {"层次", "层", ""} or ("技术" in cat and "选型" in cat):
            continue
        seq += 1
        entities.append(_make_entity("TechComponent", req_id, {
            "id": f"{req_id}.TECH.{seq:03d}",
            "name": name, "category": cat, "reason": reason,
            "license": "未声明",
        }, source))
    return entities


def extract_risks(content, req_id, source):
    """Risk：从 02_strategy_and_risk.md ## 风险 表格"""
    entities = []
    seq = 0
    risk = _section(content, r"##\s*风险(?:清单)?\b")
    for row in re.finditer(r"\|\s*([^|]+)\s*\|\s*(P\d|高|中|低)\s*\|", risk):
        seq += 1
        entities.append(_make_entity("Risk", req_id, {
            "id": f"{req_id}.RISK.{seq:03d}",
            "name": row.group(1).strip(),
            "level": row.group(2).strip(),
        }, source))
    return entities


def extract_annotations(content, req_id, source):
    """Annotation：从 annotation.md 表格"""
    entities = []
    seq = 0
    for row in re.finditer(r"\|\s*([①②③④⑤⑥⑦⑧⑨⑩\d]+)\s*\|\s*([^|]+)\s*\|", content):
        seq += 1
        entities.append(_make_entity("Annotation", req_id, {
            "id": f"{req_id}.ANNO.{seq:03d}",
            "number": row.group(1).strip(),
            "page": row.group(2).strip(),
            "confidence": 0.7,
        }, source))
    return entities


# ========== 写入 + 索引 ==========
def write_entities(req_id, entities_by_type):
    req_dir = LEGACY_DIR / req_id
    req_dir.mkdir(parents=True, exist_ok=True)
    for tname, entities in entities_by_type.items():
        if not entities:
            continue
        fp = req_dir / TYPE_TO_FILE.get(tname, f"{tname.lower()}.yaml")
        existing = []
        if fp.exists():
            try:
                existing = yaml.safe_load(fp.read_text(encoding="utf-8")) or []
                existing = existing if isinstance(existing, list) else []
            except yaml.YAMLError:
                existing = []
        existing_ids = {e.get("id") for e in existing}
        merged = existing + [e for e in entities if e.get("id") not in existing_ids]
        fp.write_text(yaml.dump(merged, allow_unicode=True, sort_keys=False), encoding="utf-8")
        print(f"  Wrote {len(merged) - len(existing)} new {tname} (total {len(merged)}) -> {fp.name}")


def rebuild_index():
    if not KG_DIR.exists():
        sys.exit("❌ KG 目录不存在")
    out = []
    for yaml_file in KG_DIR.rglob("*.yaml"):
        if yaml_file.name == "schema.yaml":
            continue
        try:
            data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict) and "_type" in item:
                out.append({
                    "_type": item["_type"], "id": item.get("id"),
                    "name": item.get("name") or item.get("name_cn") or item.get("title"),
                    "req_id": item.get("req_id"), "tags": item.get("tags", []),
                    "path": str(yaml_file.relative_to(KG_DIR)),
                })
    INDEX.write_text("\n".join(json.dumps(e, ensure_ascii=False, separators=(",",":"))
                              for e in out) + "\n", encoding="utf-8")
    print(f"✅ 重建索引: {len(out)} 条")


# ========== 命令 ==========
def cmd_semi_auto(req_id):
    dd = ROOT / "归档需求产出" / req_id / "01_drafted"
    if not dd.exists():
        sys.exit(f"❌ {dd} 不存在")

    # 文件 → extractor 映射
    plan = [
        ("Persona", dd / "01_user_research.md", extract_personas),
        ("Scenario", dd / "01_user_research.md", extract_scenarios),
        ("Insight", dd / "01_user_research.md", extract_insights),
        ("FR", dd / "02_strategy_and_risk.md", extract_frs),
        ("NFR", dd / "02_strategy_and_risk.md", extract_frs),
        ("Metric", dd / "03_metrics_and_value.md", extract_metrics),
        ("ComplianceRule", dd / "04_compliance.md", extract_compliance),
        ("TechComponent", dd / "05_solution.md", extract_tech),
        ("Risk", dd / "02_strategy_and_risk.md", extract_risks),
        ("Annotation", dd / "annotation.md", extract_annotations),
    ]

    print(f"🔍 扫描 {req_id} 产物...")
    entities_by_type = {}
    for tname, fp, extractor in plan:
        content = _read(fp)
        source = str(fp.relative_to(ROOT))
        # FR / NFR 同源，需要拆分
        if tname in ("FR", "NFR"):
            all_frs = extractor(content, req_id, source)
            entities_by_type[tname] = [e for e in all_frs if e["_type"] == tname]
        else:
            entities_by_type[tname] = extractor(content, req_id, source)
        print(f"  {tname}: {len(entities_by_type[tname])} 条")

    write_entities(req_id, entities_by_type)
    rebuild_index()
    print(f"\n✅ {req_id} 入库完成")


def cmd_manual(req_id, tname):
    print(f"📝 手动添加 {tname} 到 {req_id}（粘贴 YAML，EOF 结束）")
    lines = []
    try:
        while True:
            line = input()
            if line.strip() == "EOF":
                break
            lines.append(line)
    except EOFError:
        pass
    if not lines:
        return
    try:
        entities = yaml.safe_load("\n".join(lines))
    except yaml.YAMLError as e:
        sys.exit(f"YAML 解析失败: {e}")
    write_entities(req_id, {tname: entities})
    rebuild_index()


def cmd_add(req_id, tname, eid, data):
    entity = yaml.safe_load(data)
    entity["_type"] = tname
    entity["id"] = eid
    entity["req_id"] = req_id
    entity.setdefault("created", "manual-add")
    entity.setdefault("status", "active")
    write_entities(req_id, {tname: [entity]})
    rebuild_index()


def main():
    import argparse
    p = argparse.ArgumentParser(description="KG 入库工具")
    p.add_argument("--req", help="REQ ID")
    p.add_argument("--mode", choices=["semi-auto", "manual", "add"], default="semi-auto")
    p.add_argument("--type", help="实体类型")
    p.add_argument("--id", help="entity_id")
    p.add_argument("--data", help="实体 YAML")
    p.add_argument("--rebuild-index", action="store_true")
    args = p.parse_args()

    if args.rebuild_index:
        rebuild_index()
        return
    if not args.req:
        sys.exit("ERROR: 必须提供 --req")

    if args.mode == "semi-auto":
        cmd_semi_auto(args.req)
    elif args.mode == "manual":
        if not args.type:
            sys.exit("ERROR: manual 模式必须 --type")
        cmd_manual(args.req, args.type)
    elif args.mode == "add":
        if not (args.type and args.id and args.data):
            sys.exit("ERROR: add 模式必须 --type --id --data")
        cmd_add(args.req, args.type, args.id, args.data)


if __name__ == "__main__":
    main()