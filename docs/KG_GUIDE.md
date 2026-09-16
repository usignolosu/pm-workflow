# 知识图谱使用指南（v7.0.0）

> **项目路径**：`$HOME/Documents/workbuddy/工作流-产品/`
> **引入版本**：v3.0.0（2026-07-03，示例仓库首版）→ v7.0.0（2026-09-16，合并后定稿）
> **关联契约**：`contracts/schema/kg_contract.yaml`、`contracts/schema/agent_contracts.yaml`
> **数据规模**：128 实体 / 49 文件（合并 示例仓库 22 实体 + 本工作区演化 106 实体）

---

## 这是什么

知识图谱（Knowledge Graph, KG）是把所有"业务知识"结构化的目录。每个实体是一条 YAML 记录，
关系是独立 YAML 中的三元组（subject, predicate, object）。

**解决了什么**：
- `knowledge/` `memory/` 长期空置的承诺
- 多个完整 REQ 的 PRD/原型/代码躺在 `deliverables/`，从未被下游检索

**效果**：所有 Agent 起草时第 0 步查 KG，reviewer 审核时校验 `kg_refs` 是否合法，
机器门 `g014` 强制至少 1 条 `counter_example` 防模板污染。

---

## 一、5 类实体

| 类型 | 标识 | 说明 | 示例 |
|---|---|---|---|
| **Persona** | `*.PERSONA.NNN` | 用户画像 | `示例REQ-A.PERSONA.001`（持仓复盘者） |
| **Scenario** | `*.SCENARIO.NNN` | 用户场景卡 | `示例REQ-B.SCENARIO.002`（策略想法验证+回测） |
| **Insight** | `*.INSIGHT.NNN` | 关键洞察（含反例 `counter_example`） | `示例REQ-A.INSIGHT.002`（个人不需要专业回测，**反例**） |
| **Feature** | `*.FEATURE.NNN` | 功能点描述 | `REQ-005.FEATURE.003`（AI 自动应答 RAG 检索） |
| **Lesson** | `lesson.NNN` | 跨 REQ 的教训 | `lesson.008`（数据持久化方案模糊） |

**完整正则**（机器门 `g014` 校验）：
```
^(REQ-\d{3}\.[A-Z_]+\.\d{3}|g\d{3}|lesson\.\d{3}|agent\.[a-z_]+|scale\.[a-z]+|state\.[a-z_]+)$
```

---

## 二、快速上手

### 2.1 查询

```bash
PY=$HOME/.workbuddy/binaries/python/envs/default/bin/python

# 按 entity_id 精确查
$PY .workbuddy/skills/产品自动化工作流/scripts/query_kg.py \
  --entity REQ-001.PERSONA.001

# 按类型查
$PY .workbuddy/skills/产品自动化工作流/scripts/query_kg.py --type persona
$PY .workbuddy/skills/产品自动化工作流/scripts/query_kg.py --type scenario
$PY .workbuddy/skills/产品自动化工作流/scripts/query_kg.py --type insight

# 按关键词过滤
$PY .workbuddy/skills/产品自动化工作流/scripts/query_kg.py \
  --type scenario --keyword "回测"
```

### 2.2 全文检索（语义检索，推荐）

```bash
# 把外部材料（PRD 文档 / 调研报告 / 上轮 PR）灌入知识库
$PY .workbuddy/skills/产品自动化工作流/scripts/ingest.py \
  --src "/path/to/materials" --out runs/<run-id>/kb

# 按自然语言查
$PY .workbuddy/skills/产品自动化工作流/scripts/retrieve.py \
  --kb runs/<run-id>/kb --query "技术指标 回测 策略" --top 5
```

**已验证基线**（2026-09-16 示例需求）：
- 灌入参考项目 `examples/reference-project/docs`（PRD_v1 / Technical_Design_v1 / API_Documentation_v1 / PROGRESS）共 **150 片段**
- `retrieve --query "技术指标 回测 策略"` Top1 得分 0.775，命中准确

### 2.3 入库

把本轮产出的需求 PRD / 原型 / 用例沉淀为新实体，供后续需求检索：

```bash
$PY .workbuddy/skills/产品自动化工作流/scripts/ingest_to_kg.py \
  --req REQ-007 --src runs/<run-id>/
```

---

## 三、需求里的 `kg_refs` 怎么写（机器门强制）

> v7.0.0 起，`standard` 与 `complex` 规模**必填** `kg_refs`（机器门 `g014` P0 fail）。
> 缺 1 条 `role: counter_example`（防模板污染）即 P0 fail。

### 3.1 字段格式

```yaml
## 知识图谱引用

kg_refs:
  - entity_id: REQ-XXX.SCENARIO.NNN
    role: template         # 参考结构/字段/写法
    note: 引用理由
  - entity_id: REQ-XXX.PERSONA.NNN
    role: reference        # 引用内容作为依据
    note: 引用理由
  - entity_id: REQ-XXX.INSIGHT.NNN
    role: counter_example  # 作为反例使用，说明本 REQ 与之差异（防模板污染）
    note: 引用理由
```

### 3.2 角色语义

| role | 用途 | 何时用 |
|---|---|---|
| **template** | 参考此实体的**结构/字段/写法** | 字段借鉴、表头套用、术语命名 |
| **reference** | 引用此实体的**内容作为依据** | 沿用前序需求结论、复用画像、复用洞察 |
| **counter_example** | 作为**反例**使用 | 推翻前序结论 / 说明本 REQ 与之差异 / 防止后续沿用旧模板 |

### 3.3 真实示例（demo-20260101）

```yaml
## 知识图谱引用
kg_refs:
  - entity_id: 示例REQ-B.SCENARIO.002
    role: reference
    note: 前序「示例分析平台 V2」的「策略想法验证+回测」场景，本需求 S2 的直接前身
  - entity_id: 示例REQ-A.INSIGHT.002
    role: counter_example
    note: 前序 示例REQ-A 判定「个人不需要专业级计算」，本轮竞品对齐（同类平台若干
      均已把基准对比/样本外当默认能力）推翻该假设。作真实反例，防止后续沿用旧模板。
  - entity_id: lesson.008
    role: template
    note: 教训「数据持久化方案模糊」→ 本需求 §6.12 以服务端 SQLite 替代 localStorage
```

---

## 四、与 PRD 模板的对应关系

PRD 模板 `references/templates/prd.md` 末尾固定有「## 知识图谱引用」段，complex / standard 规模
必须填写；lightweight 规模可选。

**校验时序**（机器门 `validate_contract.py`）：
1. 读 `## 知识图谱引用` 段下的 `kg_refs` 列表
3. 校验每个 `entity_id` 命中正则 + 在图谱中存在
4. 校验 `role` 至少 1 个为 `counter_example`（仅 `libu` / `bingbu` 角色）
5. P0 fail 时阻塞归档

---

## 五、合并后的图谱结构

```
knowledge_graph/
├── index.jsonl                    # 主索引（128 条）
├── README.md                      # 图谱导航
├── entities/
│   ├── guardrails/                # 22 个 guardrail 实体（g001~g020）
│   ├── lessons/                   # 9 个跨 REQ 教训
│   └── REQ-001~005/               # 5 个历史 REQ 的实体
└── legacy/
    └── REQ-001~005/               # 示例仓库迁入的 YAML（仅 REQ-001/002/004/005 有实体文件）
```

**已知缺口**：106 条实体**仅有索引无实体文件**（来自合并时未迁完），
机器门对引用校验通过即认为存在；如需查看具体内容，运行 `query_kg.py --entity <id>`。

---

## 六、附录：从 示例仓库迁入的关键变化

| 维度 | 示例仓库 v3.x | 本工作区 v7.0.0 | 变化原因 |
|---|---|---|---|
| 路径 | `$HOME/Documents/姊妹工作流仓库/` | `$HOME/Documents/workbuddy/工作流-产品/` | 合并 |
| 旧称 | 三省六部 agent 名 | `libu` / `bingbu` / `shangshu` / `menxia` 等 slug | 清旧名，按职能命名 |
| 实体数 | 22（仅 guardrail） | **128**（+Lesson +Persona +Scenario） | 合并时补齐 |
| 强制项 | 仅校验存在 | **校验存在 + 至少 1 counter_example** | 防模板污染（实战需要） |
| `g014` | warn | **P0 fail**（complex/standard） | 强制需求血统追溯 |

---

*本指南由「产品自动化工作流 v7.0.0」系统产出 · 2026-09-16*