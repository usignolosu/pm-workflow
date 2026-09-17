# 知识图谱（Knowledge Graph）

> 项目路径：`姊妹工作流仓库（已归档）/knowledge_graph/`
> 引入版本：v2.0.0（2026-07-03）
> 关联契约：`contracts/schema/kg_contract.yaml`

## 这是什么

知识图谱（KG）是把所有"业务知识"结构化的目录。每个实体是一条 YAML 记录，关系是独立 YAML 中的三元组（subject, predicate, object）。

解决了原系统的两个问题：
1. `knowledge/` `memory/` 是空目录承诺，从未真正填充
2. 4 个完整 REQ 的 PRD/原型/代码躺在 `deliverables/`，从未被下游检索

现在所有 Agent 起草时第 0 步 = 查 KG，reviewer审核时校验 kg_refs 是否合法。

## 目录结构

```
knowledge_graph/
├── README.md                  # 本文件
├── schema.yaml                # 实体/关系类型定义（自描述）
├── index.jsonl                # 扁平索引（每行一个实体，jq/grep 可查）
├── entities/                  # 全局共享实体
│   ├── agent/                 # 8 个 Agent 定义
│   ├── guardrail/             # 22 条防线定义
│   ├── scale/                 # 3 个需求等级
│   └── state/                 # 工作流状态
├── legacy/                    # 历史 REQ 入库
│   ├── REQ-001/
│   │   ├── personas.yaml
│   │   ├── scenarios.yaml
│   │   ├── insights.yaml
│   │   ├── fr.yaml
│   │   └── relations.yaml
│   ├── REQ-002/...
│   ├── 示例REQ-A/...
│   └── 示例REQ-B/...
└── _overproduced/             # 降级时归档"超出当前等级"的产物
```

## 实体类型一览

| 类型 | ID 模式 | 示例 | 数量目标 |
|---|---|---|---|
| Persona（用户画像） | `REQ-XXX.PERSONA.NNN` | `REQ-001.PERSONA.001` | P0 必入库 |
| Scenario（典型场景） | `REQ-XXX.SCENARIO.NNN` | `REQ-001.SCENARIO.001` | P0 必入库 |
| Insight（关键洞察） | `REQ-XXX.INSIGHT.NNN` | `REQ-001.INSIGHT.001` | P0 必入库 |
| FR（功能需求） | `REQ-XXX.FR.NNN` | `REQ-001.FR.001` | P0 必入库 |
| NFR（非功能需求） | `REQ-XXX.NFR.NNN` | `REQ-001.NFR.001` | P1 |
| Metric（指标） | `REQ-XXX.METRIC.NNN` | `REQ-001.METRIC.001` | P1 |
| ComplianceRule（合规规则） | `REQ-XXX.COMPLIANCE.NNN` | `REQ-001.COMPLIANCE.001` | P2 |
| TechComponent（技术组件） | `REQ-XXX.TECH.NNN` | `REQ-001.TECH.001` | P2 |
| Risk（风险） | `REQ-XXX.RISK.NNN` | `REQ-001.RISK.001` | P1 |
| Annotation（原型标注） | `REQ-XXX.ANNO.NNN` | `REQ-001.ANNO.001` | P2 |
| Lesson（教训） | `lesson.NNN` | `lesson.001` | P0 必入库 |
| Guardrail（防线） | `gNNN` | `g001` | 全局 22 条 |
| Agent | `agent.{slug}` | `agent.libu` | 全局 8 个 |
| Scale（需求等级） | `scale.{level}` | `scale.standard` | 全局 3 个 |
| State（工作流状态） | `state.{step}` | `state.drafting` | 全局 11 个 |

## 关系类型一览

| Predicate | subject → object | 示例 |
|---|---|---|
| produces | Agent → Deliverable | `agent.libu produces 01_user_research.md` |
| belongs-to | Persona/FR/... → REQ | `REQ-001.PERSONA.001 belongs-to REQ-001` |
| contains | REQ → FR/Persona/... | `REQ-001 contains REQ-001.PERSONA.001` |
| uses | Persona → FR/Scenario | `REQ-001.PERSONA.001 uses REQ-001.FR.001` |
| measures | Metric → FR | `REQ-001.METRIC.001 measures REQ-001.FR.001` |
| constrains | ComplianceRule → FR | `REQ-001.COMPLIANCE.001 constrains REQ-001.FR.001` |
| implements | TechComponent → FR | `REQ-001.TECH.001 implements REQ-001.FR.001` |
| references | Annotation → FR | `REQ-001.ANNO.001 references REQ-001.FR.001` |
| derived-from | Lesson/Entity → REQ | `lesson.001 derived-from 示例REQ-B` |
| applies-to | Guardrail → Agent | `g001 applies-to all` |

## 使用方式

### 查询

```bash
# 按类型查
bash scripts/query_kg.py --type persona --scale standard

# 按 entity_id 查
bash scripts/query_kg.py --entity REQ-001.PERSONA.001

# 按关键词查
bash scripts/query_kg.py --type scenario --keywords "审批 报销"

# 按行业查合规规则
bash scripts/query_kg.py --type compliance_rule --industry 金融

# Agent 契约 / Scale 路由（不存 KG，fallback 直接读 contracts/）
bash scripts/query_kg.py --type agent
bash scripts/query_kg.py --type scale --scale standard
```

### 入库（DELIVERED 自动触发）

```bash
# 手动入库
python scripts/ingest_to_kg.py --req REQ-005 --mode manual

# 半自动入库（脚本抽取 + 人工审核）
python scripts/ingest_to_kg.py --req REQ-005 --mode semi-auto

# 重建索引
python scripts/ingest_to_kg.py --rebuild-index
```

### 校验

```bash
# 校验 KG 自身（ID 唯一、引用合法）
python scripts/validate_kg.py

# Agent 产出引用是否合法
python scripts/validate_contract.py --req REQ-005 --agent libu
```

## 元数据规范

每个实体 YAML 必带字段：

```yaml
source: "deliverables/.../file.md#L行号"   # 必填，可追溯
created: YYYY-MM-DD                          # 必填
status: legacy | active                      # 必填
confidence: 0.0~1.0                          # 可选
notes: "..."                                  # 可选
```

## 版本历史

| 日期 | 变更 |
|---|---|
| 2026-07-03 | 初始化：建库 + 4 个历史 REQ 入库（P0 实体）|