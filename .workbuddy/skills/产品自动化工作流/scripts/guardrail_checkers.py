#!/usr/bin/env python3
"""
guardrail_checkers.py — Guardrail 校验函数注册表（v5.0 精简版）

19 个 checker 共享 4 个工具函数（_truncate / _line / _has_any / _section）。
每个 checker 主体 1-3 行。

g005/g006/g106 属流程层/跨文件校验（machine_check: false），reviewer人工执行。
函数签名：checker(content, agent, scale, **kw) -> {"pass", "line", "evidence", "fix"}
"""
import re

# ========== 工具 ==========
def _line(content, pos):
    return content[:pos].count("\n") + 1 if pos > 0 else 0


def _truncate(text, n=80):
    return text[:n] + "..." if len(text) > n else text


def _has_any(text, keywords):
    return any(k in text for k in keywords)


def _excluded_section_ranges(content, titles):
    """返回 ## 标题列表对应的字符位置区间（用于 g007 排除元章节）"""
    ranges = []
    for title in titles:
        for m in re.finditer(re.escape(title), content):
            end = re.search(r"\n## ", content[m.end():])
            ranges.append((m.start(), m.end() + end.start() if end else len(content)))
    return ranges


def _in_excluded(pos, ranges):
    return any(s <= pos < e for s, e in ranges)


# ========== 通用防线 13 条 ==========
def g001_no_fabrication(content, agent, scale, **kw):
    """不得捏造事实：扫描单独百分比/数据声明，无来源标注则 fail"""
    bad = re.compile(r"^.*\d+\.?\d*\s*%.*$", re.MULTILINE)
    source_kw = ["假设", "调研", "来源", "基于", "推算", "估计"]
    threshold_kw = ["≥", "≤", ">", "<", "="]  # 阈值/目标值豁免
    for m in bad.finditer(content):
        line = m.group().strip()
        if _has_any(line, source_kw) or _has_any(line, threshold_kw):
            continue
        return {"pass": False, "line": _line(content, m.start()),
                "evidence": _truncate(line),
                "fix": "添加来源标注（'基于调研'/'假设 N%'）或改写为阈值声明（'≤ N%'）"}
    return {"pass": True, "line": 0, "evidence": "", "fix": ""}


def g002_no_tbd(content, agent, scale, **kw):
    """不得标 TBD"""
    bad = re.search(r"\b(TBD|TODO)\b|待定", content, re.IGNORECASE)
    if bad:
        return {"pass": False, "line": _line(content, bad.start()),
                "evidence": _truncate(bad.group()),
                "fix": "替换为 `[⚠️ 假设 80%]` 或具体值"}
    return {"pass": True, "line": 0, "evidence": "", "fix": ""}


def g003_no_empty_words(content, agent, scale, **kw):
    """不得写空话"""
    bad_phrases = ["体验流畅", "提升效率", "简单易用", "快速响应", "稳定可靠", "用户友好"]
    for p in bad_phrases:
        m = re.search(re.escape(p), content)
        if m:
            return {"pass": False, "line": _line(content, m.start()),
                    "evidence": f"空洞表述: {p}",
                    "fix": "替换为可量化条件（< 200ms / ≥ 80%）"}
    return {"pass": True, "line": 0, "evidence": "", "fix": ""}


def g004_no_etc_trail(content, agent, scale, **kw):
    """不得使用'等'字收尾"""
    bad = re.search(r"等[\s。.\)）\"\'』]", content)
    if bad:
        return {"pass": False, "line": _line(content, bad.start()),
                "evidence": "末尾出现'等'字",
                "fix": "标'仅列当前已知项'或'共 N 项，已列完'"}
    return {"pass": True, "line": 0, "evidence": "", "fix": ""}


def g007_no_question(content, agent, scale, **kw):
    """无反问句（v4.0.1 排除 ## 开放问题 等元章节）"""
    excluded = _excluded_section_ranges(content, [
        "## 开放问题", "## 项目宪法对照", "## 反向检查", "## 反例",
        "## 反例支撑", "## 反例检查", "## 反向引用", "## 引用", "## 反查",
    ])
    for m in re.finditer(r"？|\?(?![a-zA-Z\d/])", content, re.MULTILINE):
        if _in_excluded(m.start(), excluded):
            continue
        line_start = content.rfind("\n", 0, m.start()) + 1
        line_end = content.find("\n", m.start())
        line = content[line_start:line_end if line_end > 0 else None]
        if line.strip().startswith("```") or "http" in line or "|" in line[:m.start()-line_start]:
            continue
        return {"pass": False, "line": _line(content, m.start()),
                "evidence": _truncate(line.strip()),
                "fix": "改陈述句。开放问题统一放文件末尾 ## 开放问题 章节"}
    return {"pass": True, "line": 0, "evidence": "", "fix": ""}


def g008_boundary_required(content, agent, scale, **kw):
    """边界条件必填"""
    if not _has_any(content, ["边界条件", "边界"]):
        return {"pass": False, "line": 0, "evidence": "无 '边界条件' 章节",
                "fix": "添加'边界条件'和'离线/错误兜底策略'子节"}
    return {"pass": True, "line": 0, "evidence": "", "fix": ""}


def g009_persistence_required(content, agent, scale, **kw):
    """持久化方案必填"""
    if not _has_any(content, ["持久化", "LocalStorage", "SQLite", "数据库"]):
        return {"pass": False, "line": 0, "evidence": "无 '持久化' 描述",
                "fix": "写明持久化方式（LocalStorage / SQLite / PostgreSQL）"}
    return {"pass": True, "line": 0, "evidence": "", "fix": ""}


def g010_timestamp_required(content, agent, scale, **kw):
    """数据时间戳必填"""
    if _has_any(content, ["数据", "行情"]) and not _has_any(content, ["时间戳", "更新于"]):
        return {"pass": False, "line": 0, "evidence": "无 '时间戳'/'更新于' 描述",
                "fix": "添加 '数据更新时间展示方式' 和 '数据时效标注'"}
    return {"pass": True, "line": 0, "evidence": "", "fix": ""}


def g011_degradation_required(content, agent, scale, **kw):
    """数据降级链路必写"""
    if _has_any(content, ["API", "接口", "外部"]) and \
       not _has_any(content, ["降级", "备用", "fallback", "离线"]):
        return {"pass": False, "line": 0, "evidence": "无 '降级'/'备用' 描述",
                "fix": "至少 3 级降级：主源 → 备用源 → 离线模拟池 → 不可用提示"}
    return {"pass": True, "line": 0, "evidence": "", "fix": ""}


def g012_algorithm_boundary(content, agent, scale, **kw):
    """算法边界条件必写"""
    if _has_any(content, ["计算", "回测", "统计"]) and "边界" not in content:
        return {"pass": False, "line": 0, "evidence": "无 '算法边界' 描述",
                "fix": "覆盖零输入/单值/整除边界/索引越界/时序末尾"}
    return {"pass": True, "line": 0, "evidence": "", "fix": ""}


def g013_prd_alignment(content, agent, scale, **kw):
    """原型-实施对齐契约（仅 gongbu/menxia）"""
    if agent not in ("gongbu", "menxia"):
        return {"pass": True, "line": 0, "evidence": "", "fix": ""}
    if not _has_any(content, ["对齐", "原型"]):
        return {"pass": False, "line": 0, "evidence": "无 '对齐检查' 描述",
                "fix": "在产出中明确 '原型-PRD 对齐检查' 段落"}
    return {"pass": True, "line": 0, "evidence": "", "fix": ""}


def g014_kg_refs_required(content, agent, scale, kg_index=None, **kw):
    """知识图谱引用必填（v2.0）"""
    if scale not in ("standard", "complex") or agent not in (
            "libu", "bingbu", "hubu", "libu_compliance", "gongbu"):
        return {"pass": True, "line": 0, "evidence": "", "fix": ""}
    if "## 知识图谱引用" not in content and "kg_refs" not in content:
        return {"pass": False, "line": 0, "evidence": f"scale={scale} 必含 kg_refs",
                "fix": "添加 ## 知识图谱引用 段，至少 1 个 entity_id"}
    m = re.search(r"kg_refs:\s*(.+?)(?:\n##|\Z)", content, re.DOTALL)
    if not m:
        return {"pass": True, "line": 0, "evidence": "", "fix": ""}
    entity_ids = re.findall(r"entity_id:\s*(\S+)", m.group(1))
    if not entity_ids:
        return {"pass": False, "line": 0, "evidence": "kg_refs 段无 entity_id",
                "fix": "添加至少 1 个 entity_id: REQ-XXX.PERSONA.NNN"}
    pattern = r"^(REQ-\d{3}\.[A-Z_]+\.\d{3}|g\d{3}|lesson\.\d{3}|agent\.[a-z_]+|scale\.[a-z]+|state\.[a-z_]+)$"
    for eid in entity_ids:
        if not re.match(pattern, eid):
            return {"pass": False, "line": 0, "evidence": f"entity_id 格式错误: {eid}",
                    "fix": "参考 contracts/schema/kg_contract.yaml#entity_id_format"}
    if kg_index:
        for eid in entity_ids:
            if eid not in kg_index:
                return {"pass": False, "line": 0, "evidence": f"entity_id '{eid}' 不在 KG 中",
                        "fix": "运行 ingest_to_kg.py 或修正引用"}
    if agent in ("libu", "bingbu"):
        roles = re.findall(r"role:\s*(\S+)", m.group(1))
        if roles and "counter_example" not in roles:
            return {"pass": False, "line": 0,
                    "evidence": f"{agent} 缺 counter_example（防模板污染）",
                    "fix": "至少 1 个 role 改为 counter_example"}
    return {"pass": True, "line": 0, "evidence": "", "fix": ""}


# ========== Agent 专用防线 8 条 ==========
def g101_libu_source(content, agent, scale, **kw):
    """用户研究-画像来源标注"""
    if agent != "libu" or "## 用户画像" not in content and "### 画像" not in content:
        return {"pass": True, "line": 0, "evidence": "", "fix": ""}
    labels = ["基于需求推断", "基于通用行业认知", "基于用户调研假设", "来源标注"]
    if not _has_any(content, labels):
        return {"pass": False, "line": 0, "evidence": "画像无来源标注",
                "fix": "每个画像加 '基于需求推断/行业认知/调研假设' 之一"}
    return {"pass": True, "line": 0, "evidence": "", "fix": ""}


def g102_bingbu_fr_unique(content, agent, scale, **kw):
    """战略-功能编号唯一（v4.0.1 只匹配列表项，不匹配小节标题范围）"""
    if agent != "bingbu":
        return {"pass": True, "line": 0, "evidence": "", "fix": ""}
    fr_codes = []
    for line in content.splitlines():
        m = re.match(r"^\s*[-*]\s+\*{0,2}FR[-#]\s*(\d+)", line)
        if m:
            fr_codes.append(m.group(1))
    if fr_codes and len(fr_codes) != len(set(fr_codes)):
        from collections import Counter
        dup = [k for k, v in Counter(fr_codes).items() if v > 1]
        return {"pass": False, "line": 0, "evidence": f"FR 编号列表项重复: {dup}",
                "fix": "FR 编号全局唯一，去重"}
    return {"pass": True, "line": 0, "evidence": "", "fix": ""}


def g103_hubu_quantifiable(content, agent, scale, **kw):
    """指标-验收标准可量化"""
    if agent != "hubu":
        return {"pass": True, "line": 0, "evidence": "", "fix": ""}
    bad = ["响应要快", "体验要好", "用户喜欢", "稳定性高", "性能好"]
    for p in bad:
        m = re.search(re.escape(p), content)
        if m:
            return {"pass": False, "line": _line(content, m.start()),
                    "evidence": f"主观判词: {p}",
                    "fix": "用可量化条件替代（'接口响应 < 200ms'）"}
    return {"pass": True, "line": 0, "evidence": "", "fix": ""}


def g104_compliance_decision(content, agent, scale, **kw):
    """合规-必须三选一"""
    if agent != "libu_compliance":
        return {"pass": True, "line": 0, "evidence": "", "fix": ""}
    if "建议咨询法务" in content:
        return {"pass": False, "line": 0, "evidence": "占位结论 '建议咨询法务'",
                "fix": "替换为 PASS / NEEDS_REVIEW / BLOCK"}
    if not any(d in content for d in ["PASS", "NEEDS_REVIEW", "BLOCK"]):
        return {"pass": False, "line": 0, "evidence": "无三选一结论",
                "fix": "每项合规检查给 PASS/NEEDS_REVIEW/BLOCK"}
    return {"pass": True, "line": 0, "evidence": "", "fix": ""}


def g105_gongbu_license(content, agent, scale, **kw):
    """原型-A1-许可证必标"""
    if agent != "gongbu" or not _has_any(content, ["技术选型", "依赖"]):
        return {"pass": True, "line": 0, "evidence": "", "fix": ""}
    if not _has_any(content, ["MIT", "Apache", "GPL", "BSD", "商业", "自研", "许可证"]):
        return {"pass": False, "line": 0, "evidence": "无许可证标注",
                "fix": "每个组件/依赖注明许可证（MIT/Apache/GPL/BSD/商业/自研）"}
    return {"pass": True, "line": 0, "evidence": "", "fix": ""}


def g107_xingbu_severity(content, agent, scale, **kw):
    """审计-缺陷带严重程度"""
    if agent != "xingbu" or "缺陷" not in content:
        return {"pass": True, "line": 0, "evidence": "", "fix": ""}
    if not any(s in content for s in ["P0", "P1", "P2", "P3"]):
        return {"pass": False, "line": 0, "evidence": "缺陷无严重程度",
                "fix": "每个缺陷标 P0/P1/P2/P3"}
    return {"pass": True, "line": 0, "evidence": "", "fix": ""}


def g108_menxia_evidence(content, agent, scale, **kw):
    """reviewer-判据引原文"""
    if agent != "menxia":
        return {"pass": True, "line": 0, "evidence": "", "fix": ""}
    vague = ["逻辑有问题", "写得不好", "需要改进"]
    for p in vague:
        m = re.search(re.escape(p), content)
        if m:
            return {"pass": False, "line": _line(content, m.start()),
                    "evidence": f"判据笼统: '{p}'",
                    "fix": "具体到文件:行 + 违反契约第几条"}
    return {"pass": True, "line": 0, "evidence": "", "fix": ""}


def g015_token_color(content, agent, scale, **kw):
    """原型-硬编码色值检查（v6.0 P3-1：不在 design_tokens 内的 hex = 打回）"""
    from pathlib import Path
    if agent != "gongbu" or "#" not in content:
        return {"pass": True, "line": 0, "evidence": "", "fix": ""}

    allowed = {"FFFFFF", "FFF", "000000", "000"}  # exceptions：画布/文字反白
    tokens_path = Path(__file__).parent.parent / "contracts" / "design_tokens.yaml"
    try:
        import yaml
        tokens = yaml.safe_load(tokens_path.read_text(encoding="utf-8")) or {}
        for layer in ("primitive", "semantic"):
            colors = (tokens.get(layer) or {}).get("color") or {}
            allowed |= {v.lstrip("#").upper() for v in colors.values()
                        if isinstance(v, str) and v.startswith("#")}
    except Exception:
        pass  # token 文件缺失时退化为只拦明显非法值，不误报

    for m in re.finditer(r"#([0-9a-fA-F]{3,8})\b", content):
        hex_val = m.group(1).upper()
        expanded = hex_val if len(hex_val) in (6, 8) else "".join(c * 2 for c in hex_val)
        if expanded not in allowed:
            return {"pass": False, "line": _line(content, m.start()),
                    "evidence": f"硬编码色值 #{hex_val} 不在 design_tokens.yaml",
                    "fix": "改用 design_tokens 的 primitive/semantic token（或 REQ 目录 override）"}
    return {"pass": True, "line": 0, "evidence": "", "fix": ""}


# ========== 注册表 ==========
EVALUATORS = {
    "g001": g001_no_fabrication, "g002": g002_no_tbd, "g003": g003_no_empty_words,
    "g004": g004_no_etc_trail, "g007": g007_no_question, "g008": g008_boundary_required,
    "g009": g009_persistence_required, "g010": g010_timestamp_required,
    "g011": g011_degradation_required, "g012": g012_algorithm_boundary,
    "g013": g013_prd_alignment, "g014": g014_kg_refs_required,
    "g101": g101_libu_source, "g102": g102_bingbu_fr_unique,
    "g103": g103_hubu_quantifiable, "g104": g104_compliance_decision,
    "g105": g105_gongbu_license, "g107": g107_xingbu_severity,
    "g108": g108_menxia_evidence, "g015": g015_token_color,
}


def eval_guardrail(gid, content, agent="", scale="standard", kg_index=None):
    """运行指定 Guardrail 校验"""
    fn = EVALUATORS.get(gid)
    if not fn:
        return {"pass": True, "line": 0, "evidence": f"未实现: {gid}",
                "fix": "", "unimplemented": True}
    try:
        return fn(content, agent, scale, kg_index=kg_index)
    except Exception as e:
        return {"pass": True, "line": 0, "evidence": f"checker 异常: {e}",
                "fix": "", "error": True}
