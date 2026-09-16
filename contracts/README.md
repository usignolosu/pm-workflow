# contracts/ — 机器可读契约

> 替代 `workflow/contracts.md`（v1.0，已归档到 `workflow/_archive/contracts.v1.md`）
> 当前契约版本：**v2.0.0**（2026-07-03）

## 这是什么

把原本 364 行的 Markdown 契约拆成 8 个 YAML + 1 个 PRD 模板，每个文件单一职责、机器可解析。
新增"知识图谱契约"和"校验规则"两个主题，支持 PM 级业务知识沉淀与 Agent 自动校验。

## 目录

```
contracts/
├── README.md                          # 本文件（人读入口）
├── schema/
│   ├── versioning.yaml                # 版本号 + SemVer 策略
│   ├── guardrails.yaml                # 13 通用 + 8 专用 + 1 新增 = 22 条防线
│   ├── load_order.yaml                # 8 个 Agent 装载顺序（唯一权威源）
│   ├── scale_routing.yaml             # light/standard/complex 路由
│   ├── agent_contracts.yaml           # 各 Agent 输入/输出/必填/可选契约
│   ├── kg_contract.yaml               # 知识图谱契约（v2.0 新增）
│   └── validation_rules.yaml          # 校验规则（机器可读）
└── prd_template/
    └── prd_10ch.yaml                  # 10 章 PRD 模板（唯一权威源）
```

## 解决原 contracts.md 的问题

| 原问题 | 修复方式 |
|---|---|
| §2 与 §4 Load Order 重复 | `load_order.yaml` 为唯一权威源，删除原 §4 |
| §14.2 与 §16 PRD 章节重复且冲突 | `prd_10ch.yaml` 为唯一权威源，删除原 §16 |
| 通用防线从 7 → 13 条（README 过时） | `guardrails.yaml` 显式列 13 条通用 + 8 条专用 |
| 缺失版本号 | `versioning.yaml` 引入 SemVer |
| 缺失等级变更流程 | `scale_routing.yaml` 加 `promotion/demotion` 段 |
| 缺失打回回归流程 | `validation_rules.yaml` 加 `revision_cycle` 段 |
| Load Order 硬编码表格 | YAML 化 + 模板变量 `${req_id}`/`${scale}` |
| 契约条目无分类标签 | universal/agent_specific/scale/kg 四类标签 |
| 无扩展点 | `versioning.yaml` 的 `semver_policy` |
| 无知识库接入接口 | `kg_contract.yaml`（v2.0 新增）+ Guardrail #14 |

## 使用方式

### 人读入口

```bash
# 看完整契约清单
cat contracts/README.md

# 看某个 Agent 的契约
cat contracts/schema/agent_contracts.yaml

# 看知识图谱如何被 Agent 引用
cat contracts/schema/kg_contract.yaml
```

### 机器读取

```bash
# 校验器（reviewer审核时必走）
python scripts/validate_contract.py --req REQ-005 --agent libu

# KG 查询（Agent 调度时第 0 步）
bash scripts/query_kg.py --type persona --scale standard
```

## 模板变量约定

所有 YAML 中可使用以下变量，校验器/Agent 调度时替换：

| 变量 | 含义 | 示例 |
|---|---|---|
| `${req_id}` | 需求 ID | `REQ-005` |
| `${scale}` | 需求等级 | `light` / `standard` / `complex` |
| `${industry}` | 业务行业（合规专用） | `金融` / `医疗` / `教育` |
| `${category}` | 技术领域（原型-A1 专用） | `frontend` / `backend` / `mobile` |
| `${agent}` | Agent slug | `libu` / `bingbu` / ... |

## 迁移策略（双轨并行）

- **阶段 1（v2.0.0 落地）**：YAML 为权威，旧 `workflow/contracts.md` 加 DEPRECATED 提示但保留只读
- **阶段 2（3 个月内）**：逐步迁移所有 Agent 的 SKILL.md，Load Order 改读 YAML
- **阶段 3（3-6 个月）**：删除 `workflow/contracts.md`，保留 `workflow/_archive/contracts.v1.md` 永久归档

## 版本历史

详见 `schema/versioning.yaml` 的 `_changelog` 段。

| 版本 | 日期 | 变更摘要 |
|---|---|---|
| v1.0.0 | 2026-06-16 | 初始版本（Markdown，364 行） |
| v2.0.0 | 2026-07-03 | 拆分为 8 个 YAML + README，新增 KG 契约与校验规则 |