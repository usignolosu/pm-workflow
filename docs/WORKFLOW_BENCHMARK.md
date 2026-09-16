# 工作流对标报告 · GitHub 主流框架对比与合并后方案（v7.0.0）

> **生成**：2026-09-13（示例仓库 v5.1） → 2026-09-16（v7.0.0 合并版）
> **触发**：PM 决策"参考 GitHub 其他产品工作流做对比，目标：精简代码/流程、提升输出内容和原型设计"
> **调研范围**：BMAD Method、GitHub Spec Kit、Agent OS、Kiro、OpenSpec、Task Master、MetaGPT、v0/设计 token 生态
> **关键决定**：v7.0.0 合并两套工作流后定稿（本工作区 B 仓为唯一存活仓，示例仓库转只读归档）

---

## 一、框架横向对比

| 框架 | 流程形态 | 规模自适应 | 输出质量机制 | 原型/UX 位置 |
|---|---|---|---|---|
| **我们 v7.0.0** | 单循环 + 3 规模 × `deliver_code` 开关 | ✅ 3 规模 + 1 正交开关 | **20 机器 Guardrail + 宪法 8 条 + EARS + KG 必填 + 反例防模板污染** | 低/高保真两阶段 + 截图评审 |
| **BMAD** (53k★) | **单循环** Clarify→Plan→Build&Verify→Learn，三入口 | ✅ 行业标杆：小改动直进 Build | readiness gate（查未记录决策依赖） | DESIGN.md+EXPERIENCE.md 二分，文档优先于 mockup |
| **Spec Kit** (136k★) | constitution→specify→clarify→plan→tasks→implement | 小修不走 SDD，直接 issue/PR | **checklist="unit tests for English"** + analyze 跨制品一致性 | — |
| **Agent OS** (5.4k★) | Standards→Specs→Plans 三层 | — | **按需注入相关标准**（不全量塞 context） | — |
| **Kiro** | requirements(EARS)→design→tasks | **Quick Spec** 一次生成跳审批门 | EARS 结构化验收；steering 常驻上下文 | Design-First 可反向（先架构图后需求） |
| **Task Master** (28k★) | parse-prd→tasks→复杂度分析→拆解 | — | **PRD 可执行性度量**（复杂度报告） | — |
| **MetaGPT** (70k★) | SOP 流水线 | — | PRD 含竞品分析+数据结构+API 规范 | — |
| **v0 生态** | 原型即产品 | — | 硬编码色值=code smell，token 校验 | **三层 token**（primitive→semantic→component）+ Design Mode 迭代 |

**核心洞察**：我们最强的部分（机器防线 + 宪法 + EARS + KG 沉淀 + 反例防模板污染）在业界是**领先的**——Spec Kit 的 checklist 和 Kiro 的 EARS 我们都有，**而且我们做了硬约束**（机器门自动跑）。
真正的差距仍在三处：**流程沉重感**（BMAD 已证明单循环是主流）、**spec→任务的断链**（Task Master 的复杂度分析我们没有）、**原型缺设计系统约束**（v0 生态的 token 纪律我们未引入）。

---

## 二、v5.1 → v7.0.0 已落地的优化

### 轴 1：精简流程/代码（状态 24→1 状态机 + 4 门 + 机器门自动跑）

**P1-1 单循环改造**（学 BMAD，最大收益）→ **已落地**

| 维度 | v5.1 | v7.0.0 |
|---|---|---|
| 流程形态 | 3 mode（lean_pm/standard/enhanced）+ 24 状态机 | **单循环 + 3 规模 × `deliver_code` 开关** |
| 门 | 5 硬门 + 4 软门（9 道打断） | **4 人工门 + 机器门自动跑**（≤4 次打断） |
| 状态 | 24 状态 + 根 `state.json` | `runs/<run-id>/execution-log.md` |

### 轴 2：补强防漏（19→20 guardrail + KG 必填）

**P2-1 新增 `g014` KG 必填**（学 Spec Kit 的跨制品一致性）→ **已落地**

- `g014`：standard / complex 规模 `kg_refs` 必填；至少 1 条 `role: counter_example` 防模板污染
- `g001`：禁止裸百分比（无来源数据声明）—— **示例需求中实际抓到 13 处**（如佣金万 2.5、滑点 0.1%、自定目标值 100%），证明此防线**有效**

**P2-2 PRD 模板 14 模块**（吸收 示例仓库 4 项补强）→ **已落地**

- §6 截图标注索引表（按功能点）
- §7.0 成功指标（含北极星 + 过程指标 + 价值评估）
- §11 EARS 句式强制
- §14.0 开放问题表（待决项 + 责任人 + 截止时间）

### 轴 3：原型与设计系统（v0 token 纪律）

**P3-1 三层 token**（primitive→semantic→component）→ **部分落地**
- 原型阶段已要求「色值必须引用 `design_tokens`」（合并条款），但尚未自动校验
- 短板：缺 token 自动校验脚本（`scripts/design_token_check.py` 待补）

**P3-2 高保真原型必带截图**（PRD §6 强制）→ **已落地**
- 14 个功能点 × 至少 1 张截图
- 切屏函数兼容性（`go/show/select/nav/switchPage/goTo`）由 `gen_screenshots.js` 探测
- 字节数重复即 WARN 防回归

---

## 三、与 BMAD 的差距（按优先级）

| # | BMAD 做法 | 我们现状 | 差距 |
|---|---|---|---|
| 1 | **readiness gate**：起草前查未记录决策依赖 | 起草前查 KG（覆盖度有限） | 中——需补 readiness 门 |
| 2 | **DESIGN.md + EXPERIENCE.md** 二分 | 单 prototype + screenshots | 小——文档格式可演进 |
| 3 | **小改动直进 Build** | 3 规模切换仍走全部阶段 | 小——lightweight 模式可进一步裁剪 |
| 4 | **三入口** | 单循环 + 模式路由器 | **无差距**（更灵活） |

---

## 四、与 Spec Kit / Kiro 的差距

| # | 做法 | 我们的现状 | 差距 |
|---|---|---|---|
| 1 | Spec Kit **checklist** | 我们的 `test-cases.md` | **无差距**（更细） |
| 2 | Kiro **EARS** | 已强制（模板铁律） | **无差距** |
| 3 | Kiro **steering 常驻上下文** | KG 按需检索（`ingest.py` + `retrieve.py`） | 中——大需求可能遗漏 |
| 4 | Kiro **Design-First 反向** | 当前单向前进 | 小——可作 v2 选项 |

---

## 五、v8 候选（P2-P3，需 PM 决策）

| # | 改进 | 借鉴自 | 投入 | 收益 |
|---|---|---|---|---|
| C1 | `scripts/design_token_check.py` | v0 | 1d | 防色值硬编码 code smell |
| C2 | `scripts/readiness_check.py`（起草前查未记录决策依赖） | BMAD | 2d | 减少中途中评次数 |
| C3 | `scripts/spec_complexity.py`（PRD 可执行性度量） | Task Master | 3d | 早期发现规格过大 |
| C4 | `Lightweight` 模式进一步裁剪到「3 角色 / 2 阶段 / 0 中评」 | BMAD | 1d | 小改动体验再提升 |
| C5 | `runs/` 跨需求检索（`scripts/find_pattern.py`） | — | 2d | 跨需求经验沉淀 |

---

## 六、合并前后数据对比

| 指标 | v5.1（示例仓库） | v7.0.0（合并 B） |
|---|---|---|
| 工作流版本 | v5.1（独立 CLI） | **v7.0.0**（Skill） |
| 角色数 | 8（三省六部） | **13 常驻 + 3 扩展** |
| 形态 | 独立 CLI 工具 | **WorkBuddy 项目级 Skill** |
| 状态 | 24 状态机 | 单循环 + 4 门 + 机器门自动跑 |
| 验证 | 19 guardrail + 19 spec | **20 guardrail + spec 质量门** |
| KG 实体 | 22（仅 guardrail） | **128** |
| 校验器 | `validate_contract.py`（19/19 自述） | `validate_contract.py`（实测 16/4、13/7，**CHANGELOG 自述与实测不符**） |
| 已交付 REQ | 5（001/002/004/005 + 003 ABANDONED） | 5（保留原状未修） + **6 个新增需求产出**（示例A / 示例B / 示例 / etc） |

> ⚠️ **示例仓库可信度提示**（v7.0.0 合并时核实）：示例仓库 CHANGELOG 自述「19/19 PASS」**复现不出来**（实测 16/4 fail）。说明 示例仓库的 5 个 REQ 其实都没过全检，KG 号称 128 实体但 `entities/` 目录只有 22 个 guardrail，其余 106 条仅索引无实体文件。**但**校验器本身是真家伙（实战中能抓 `g001` 无来源标注、`g004` 末尾「等」、`g008` 缺边界条件、`g012` 缺算法边界），值得迁。

---

*本对标报告由「产品自动化工作流 v7.0.0」系统产出 · 2026-09-16 · 与 `.workbuddy/skills/产品自动化工作流/SKILL.md` §11 同步*