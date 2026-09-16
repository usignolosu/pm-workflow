---
name: 产品自动化工作流
description: 产品需求到 PRD + 原型 + 测试用例的自动化工作流。当用户提出产品想法/需求/改动，需要系统化地产出 PRD 文档、低保真/高保真原型、用户旅程图、业务流程图与测试用例时使用。覆盖三种模式（轻量/常规/复杂）、四处人工确认门、13 角色智能体编队、机器契约校验与知识图谱追溯。触发词：产品工作流、PRD、产品需求、画原型、用户旅程图、功能表、产品自动化。
---

# 产品自动化工作流（v7.0.0 · 合并统一版）

> 一句话需求 → 背景调研 → 行业调研与用例转写 → 场景梳理 + 用户旅程图 → 功能表 → 低保真原型 → 高保真原型 + 完整 PRD + 测试用例 → QA 评审。
> 全程在 WorkBuddy 会话内闭环，本地文档不出机；高危环节暂停请求用户确认。

> **v7.0.0 合并说明**：本技能已合并姊妹仓「姊妹工作流仓库」（`$HOME/Documents/姊妹工作流仓库`）的工程化资产——契约校验、状态机、知识图谱、18 个脚本。
> 那 8 个 `references/roles/*/SKILL.md` **不是** WorkBuddy Skill，只是「角色工作说明书」的文件命名；调度 = 换提示词，不启动进程。

---

## 0. 启动引导（每次进入必读）

进入本技能后，**第一件事**向用户确认本次使用的模式（轻量 / 常规 / 复杂）。可调用 `AskUserQuestion`：

- **轻量**：小改动，无需背景调研，仅保留最必要角色。跳过 ②③。
- **常规**：普通任务，可能涉及已有功能点，标准编队，轻量检索。
- **复杂**：大范围需求，需研究历史资料，全量编队，深度检索 + 知识图谱追溯。

**同时确认正交开关 `deliver_code`**（是否产出可运行代码）：
- `true`：⑦ 之后继续出代码 + 测试报告（对应原 示例仓库的 standard/complex 完整链路）
- `false`：只出文档 + 原型，不写代码（对应原 示例仓库的 `lean_pm` 模式）

确认后，调用 `TaskCreate` 登记本次运行的角色任务（见 §6），并创建运行目录 `runs/<run-id>/`（run-id = 日期+序号，如 `20260715-01`），写入 `execution-log.md`。

随后按 §2 的 8 阶段主流程推进。

---

## 1. 角色编队（13 常驻 + 复杂模式 3 扩展）

| 角色 | 阶段 | 职责 | 轻量 | 常规 | 复杂 |
|------|------|------|:---:|:---:|:---:|
| **主编排**（supervisor） | 全程 | 调度、状态机、归档。不写业务内容 | ✓ | ✓ | ✓ |
| 调研员 | ② | 内部知识库检索、历史资料/模板检索 | — | ✓ | ✓ |
| 行业分析 | ③ | 联网竞品/行业调研 | — | ✓ | ✓ |
| 用例转写 | ③ | 调研结果 → 标准用户用例 | — | ✓ | ✓ |
| **用户研究与场景** | ④ | 画像 + 场景卡 + 用户故事地图 + 用户旅程图 | ✓ | ✓ | ✓ |
| 功能设计 | ⑤ | 产品功能表（模块/功能点/RICE/边界） | ✓ | ✓ | ✓ |
| 指标 | ⑤ | 北极星、过程指标、价值评估 | — | ✓ | ✓ |
| 合规 | ⑤ | 合规审查 | — | ✓ | ✓ |
| 原型 | ⑥⑦ | 低保真线框 → 高保真 React 代码 + HTML 预览 | ✓ | ✓ | ✓ |
| PRD | ⑦ | 14 模块 PRD（§6 须「页面截图 + 功能说明」） | ✓ | ✓ | ✓ |
| **评审 critic** | 阶段间 | **独立审核、可打回**。必须独立判断，不能放水 | — | ✓ | ✓ |
| 测试 | ⑦ | 测试用例集 + 验收标准，与功能表映射 | — | ✓ | ✓ |
| QA | ⑧ | 终审：缺口分析 + **来源标注** | — | ✓ | ✓ |
| 架构师 / 竞品分析 / SME | 复杂 | 复杂模式额外上场，加强评审深度 | — | — | ✓ |

> **评审 critic 与 QA 的分工**（易混淆，勿合并）：critic 是**中途独立打回**，QA 是**终审 + 来源标注**。
> 同一会话内「角色切换」为主（轻量/常规串行）；复杂模式用 `Agent` 工具**真·分身并行**（见 §5）。

---

## 2. 主流程（8 阶段 + 4 人工门 + 机器门）

```
① 需求输入与澄清
   模式识别（系统判定 + 用户确认）→ 苏格拉底式澄清（每次 1 问：背景→角色→场景→功能→边界）
   └ 产出：模式结论 + deliver_code 开关 + 澄清结论
② 背景调研（轻量跳过）
   内部知识库混合检索；复杂模式叠加知识图谱追溯
③ 行业调研 + 用例转写（轻量跳过）
   联网调研/竞品 → 标准用例集
④ 场景梳理 → 用户故事地图 + 用户旅程图
   ⏸ 人工门 1：确认场景、用户故事地图、用户旅程图
⑤ 生成产品功能表（RICE 优先级）+ 指标 + 合规
   ⏸ 人工门 2：确认功能表与方案
⑥ 生成低保真原型（线框 + 交互说明）
   ⏸ 人工门 3：确认原型（通过后锁定截图标注编号）
⑦ 并行产出：PRD ∥ 高保真原型 ∥ 测试用例
   高保真原型生成后，先用 `scripts/gen_screenshots.js` 渲染各页面截图到 `screenshots/`，
   PRD §6 以「截图 + 功能说明」嵌入
   deliver_code=true 时额外：实施 → 代码 + 测试报告
⑧ QA 评审 + 缺口分析 + 来源标注
   ⏸ 人工门 4：交付验收
```

各阶段产物模板见 `references/templates/`，澄清/生成提示词见 `references/prompts/`，流程与状态机细节见 `references/workflow/`。

---

## 3. 三模式裁剪 × deliver_code 开关

| 维度 | 轻量 | 常规 | 复杂 |
|------|------|------|------|
| ②③④ 调研 | 跳过 | 轻量检索 | 深度 + 图谱 + 历史 PRD 追溯 |
| 参与角色 | 5 | 14 | 14 + 3 扩展 |
| 人工门 | 合并为 2 次 | 4 次 | 4 次 + 阶段中审 |
| 优先级 | P0/P1/P2 | RICE | RICE |
| 产物 | 简版 PRD + 原型 | 标准 PRD + 低/高保真 + 用例 | 完整 PRD + 高保真 + 用例 + 影响面分析 |

**`deliver_code` 开关**（正交，与三模式自由组合）：
- `false`（原 示例仓库 `lean_pm`）：止于 ⑦，只交付文档 + 原型
- `true`：⑦ 之后继续实施与测试，产出可运行代码 + 测试报告

---

## 4. 确认门与回退规则（HITL）

### 人工门（4 个，必须用户拍板）

| 门 | 时点 | 确认内容 |
|---|---|---|
| 1 · 场景与旅程 | ④ 后 | 场景卡、用户故事地图、用户旅程图 |
| 2 · 功能表与方案 | ⑤ 后 | 功能表、指标、合规 |
| 3 · 原型 | ⑥ 后 | 低保真原型；**通过后锁定截图标注编号** |
| 4 · 交付验收 | ⑧ 后 | 完整交付物 |

### 机器门（自动跑，失败即打回，不征求同意）

| 校验 | 命令 | 内容 |
|---|---|---|
| 契约校验 | `python scripts/validate_contract.py --req <ID> --agent <角色> --scale <规模> --strictness strict` | 20 条 guardrails |
| Spec 质量门 | 随契约校验第 10 步 | EARS 可测性 / user story / FR 编号唯一 / 接口契约 |
| 项目宪法 | `contracts/constitution.yaml` | 8 条原则（人工对照） |
| 链路自检 | `python scripts/self_check.py` | 脚本链路 10 项 |

### 高危暂停（除上述门之外，出现即暂停）
① 覆盖/写入已有知识库 ② 删除操作 ③ 发布原型 ④ 大范围功能变更

### 回退规则
- 用户选「修改」→ 回退到该产物生成阶段重做（如门 2 拒绝 → 回 ⑤ 改功能表）
- 用户选「回退」→ 整体退到上一人工门重新走
- 标注编号锁定后变更：标 `SCOPE_CHANGE` → 解锁 → 重新出截图与标注 → 重审重锁

---

## 5. 执行模型（混合：常规串行 + 复杂并行）

- **轻量 / 常规**：单会话内角色切换串行，靠角色标签 + 任务看板呈现。
- **复杂**：用 `Agent` 工具真·分身并行——②/③ 调研（调研员∥行业分析∥用例转写 并发）、⑦ 产出（PRD∥高保真∥用例 并发），主流程汇总。
- **统一状态契约**：每个 agent 上报 `agent / state(pending→running→done/blocked/revision) / doing / output / 来源 / 耗时`。
- **注意**：④⑤⑥ 全模式必走，图示时必须保留所有模式共用的串行阶段，只高亮并行点。

---

## 6. 可观测性（起点即建立）

1. **任务看板（TaskCreate/TaskUpdate）**：为每个上场角色登记任务，状态 `pending→in_progress→completed`。
2. **定期进度汇报**：按阶段/定时汇总进展与下一步；复杂并行时收敛各 agent 中间结果。
3. **执行留痕**：每次运行生成 `runs/<run-id>/execution-log.md`，按时间追加每个 agent 的状态/产出/来源/异常。
4. **进度提示**（每阶段切换时输出）：进度条 + 当前阶段 + 下一步 + 待答问题 + 预估剩余。
5. 状态写入由 `scripts/report_status.py` 辅助。

---

## 7. 脚本用法（本地，数据不出机）

> 全部脚本需 Python 依赖，见工作区根 `requirements.txt`（**至少 PyYAML**）。
> 受管 Python：`$HOME/.workbuddy/binaries/python/versions/3.13.12/bin/python3`

**产出链路（B 原有）**

| 脚本 | 用途 | 调用时机 |
|---|---|---|
| `scripts/ingest.py` | 本地文档 → 解析 → 向量化 | 首次使用或资料更新 |
| `scripts/retrieve.py` | 混合检索 + rerank | ② 背景调研 |
| `scripts/build_graph.py` | 实体关系抽取 → 知识图谱 | 复杂模式 |
| `scripts/gen_prototype.py` | 低保真 JSON → 高保真 React + HTML | ⑥⑦ |
| `scripts/gen_screenshots.js` | 高保真 HTML → 各页面 PNG（需系统 Chrome，puppeteer-core） | ⑦ 原型渲染后、PRD 写入前 |
| `scripts/report_status.py` | 写入 `execution-log.md` | 每个 agent 交接时 |
| `scripts/self_check.py` | 链路自检 10 项 | 环境验证 |

**工程化支撑（A 迁入）**

| 脚本 | 用途 |
|---|---|
| `scripts/validate_contract.py` | **契约校验**（20 条 guardrails + spec 质量门） |
| `scripts/query_kg.py` | 知识图谱查询 / 统计 |
| `scripts/ingest_to_kg.py` | 需求产物入库知识图谱 |
| `scripts/new_requirement.sh` | 新建需求目录骨架 |
| `scripts/status.sh` / `heartbeat.sh` | 任务总览 / 心跳自检 |
| `scripts/clarify.py` | 澄清门问题生成 |
| `scripts/render_dashboard.py` | 看板渲染 |
| `scripts/guardrail_checkers.py` | guardrail 检查器 |
| 其余 | `bug_fix.sh` `deliver_hook.sh` `evolve.sh` `feedback_loop.sh` `feedback_log_check.py` `pre_commit_gate_check.py` `pre_reply.sh` `reject_hook.sh` `state_context.py` `render_cards.js` |

> **路径约定**：脚本的 `ROOT` 指向**工作区根**（`工作流-产品/`）。
> 历史需求归档在 `归档需求产出/<REQ-ID>/{01_drafted,02_reviewed,03_finalized}/`。

运行示例：
```bash
PY=$HOME/.workbuddy/binaries/python/versions/3.13.12/bin/python3
$PY .workbuddy/skills/产品自动化工作流/scripts/validate_contract.py --req REQ-001 --agent hubu --scale standard --strictness strict
$PY .workbuddy/skills/产品自动化工作流/scripts/query_kg.py
```

> ⚠️ **`gen_screenshots.js` 的两个前置条件**（手工调用易漏）：
> 1. `puppeteer-core` 不在脚本目录下解析，**必须先设 env**
>    `NODE_PATH=$HOME/.workbuddy/binaries/node/workspace/node_modules`，否则报
>    `Cannot find module 'puppeteer-core'`（`self_check.py` 内部已设，手工跑会漏）。
> 2. 需系统 Chrome；可用 `CHROME_PATH` 覆盖。
>
> **切屏兼容性**：脚本按 `go / show / select / nav / switchPage / goTo` 逐个探测页面切屏函数，
> 再退化到 `active` 类切换与内联 `display`。**不要把某个原型的函数名写死进脚本**——
> 示例A原型用 `go()`、示例B原型用 `select()`、`gen_prototype.py` 产出用 `show()`。
> 出图后脚本会校验「字节数是否重复」，重复即 WARN（提示切屏未生效）。

---

## 8. 产出目录约定

```
工作流-产品/
├── runs/<run-id>/                     # 本次运行过程留痕
│   ├── execution-log.md
│   ├── clarify.md  research.md  scenarios.md  journey-map.md  story-map.md
│   ├── feature-table.md  wireframe.md  prd.md  test-cases.md
│   ├── prototype/                     # 高保真 React 代码 + index.html
│   └── screenshots/                   # 页面截图（PRD §6 引用）
├── <需求名>需求产出/                   # 可见交付副本（长期归口）
├── 归档需求产出/<REQ-ID>/              # 历史归档（示例仓库迁入，保留原编号）
├── contracts/                          # 契约（宪法/guardrails/spec_checklist）
└── knowledge_graph/                    # 知识图谱
```

---

## 9. 启动检查清单

- [ ] 确认模式（轻量/常规/复杂）+ `deliver_code` 开关
- [ ] 建 `runs/<run-id>/` 与 `execution-log.md`
- [ ] 登记角色任务到任务看板
- [ ] ① 澄清 → ② 调研(如需) → ③ 用例(如需)
- [ ] ④ 场景 + 两张图 → **人工门 1**
- [ ] ⑤ 功能表 + 指标 + 合规 → **人工门 2**（机器门随跑）
- [ ] ⑥ 低保真 → **人工门 3**（通过后锁定标注编号）
- [ ] ⑦ PRD + 高保真 + 用例（+ 代码，若 `deliver_code=true`）
- [ ] ⑧ QA 评审 + 来源标注 → **人工门 4** → 归档到 `<需求名>需求产出/`
