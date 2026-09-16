# Changelog

产品自动化工作流的所有显著变更均记录于此。格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

---

## [v7.0.0] - 2026-09-16

### 重大变更（MAJOR · 破坏性架构）

合并两两套工作流（示例仓库 v5.1/v6.0 + B 仓 v7.0.0）后定稿。

#### 形态
- **独立 CLI → Skill 形态**：从 `.workbuddy/skills/产品自动化工作流/SKILL.md` 加载，由 WorkBuddy 项目级调度
- 无独立进程、无 MCP spawn，**会话内 agent 内扮演多角色**

#### 角色
- **三省六部 8 agent → 13 常驻 + 3 复杂扩展**
  - 13 常驻：主编排 + 调研员 + 行业分析 + 用例转写 + 用户研究 + 功能设计 + 指标 + 合规 + 策略风控 + 原型 + 测试 + PRD + 评审 critic + QA
  - 3 复杂扩展：法律顾问 + 资深架构师 + 用户研究员（仅 complex 激活）

#### 规模
- **3 mode（lean_pm/standard/enhanced）→ 3 规模（lightweight/standard/complex）× 1 开关 `deliver_code`**
- `deliver_code`：`false`（默认，止于 PRD + 原型）/ `true`（继续实施改造 + 测试报告）

#### 门
- **5 硬门 + 4 软门（9 道打断）→ 4 人工门 + 机器门自动跑（≤4 次打断）**
- 机器门：`validate_contract.py` 在 ⑦ 末与 ⑧ 自动触发，不占打断次数

#### Guardrail
- **19 → 20 条**：新增 `g014 KG 必填`（standard/complex 必填 kg_refs，至少 1 条 `role: counter_example` 防模板污染）

#### KG
- **22 实体（仅 guardrail）→ 128 实体**（合并 示例仓库 + 本工作区演化）

#### PRD 模板
- **10 章 → 14 模块**：吸收 示例仓库 4 项补强（§7.0 成功指标 / §14.0 开放问题 / §6 截图标注索引表 / §11 EARS 句式强制）

### 修复
- `gen_screenshots.js` 切屏函数不再写死 `go()`，按 `go/show/select/nav/switchPage/goTo` 逐个探测（修复前 3/3 张同图 → 修复后 0/3）
- `gen_prototype.py` spec 字段错（`screens` vs `pages`）不再静默成功，缺 `pages` 即报错退出
- `render_cards.js` ROOT 路径少算 1 层（原 `__dirname/..` → 修正为 `__dirname/../../../../`）

### 文档
- `docs/FLOW_DIAGRAM.md`：v5.1→v7.0.0 关键变化表 + 13 角色表 + 4 门
- `docs/cards/card-1~8.html`：8 张小红书卡片全面重写
- `docs/WORKFLOW_BENCHMARK.md`：v7.0.0 对标 BMAD / Spec Kit / Kiro / Task Master / MetaGPT / v0 生态
- `docs/KG_GUIDE.md`：5 类实体 + 反例防模板污染

### 实战验证
- 示例需求（run-id `demo-20260101`）一次跑通：
  - 契约校验收敛 16/4 → 18/2 → **20/0 PASS**
  - 7 张原型截图 md5 全异
  - 共打回 5 项（`g001` 抓出 13 处裸百分比、`g014` 缺反例、§6 缺截图、§11 主观表述、§13 里程碑编号错位）

---

## [v6.0] - 2026-09（已废弃）

v6.0（24 状态机 + 3 mode + 入口选择器）已合并入 v7.0.0。

---

## [v5.1] - 2026-09（已废弃）

v5.1（三省六部 8 agent）已合并入 v7.0.0。

---

[Unreleased]: #v8 候选（design token check / readiness gate / spec complexity），见 docs/WORKFLOW_BENCHMARK.md §五