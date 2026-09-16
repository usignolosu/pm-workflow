# states_CORE · 状态机核心（Codex 必读）

> 详细流转规则见 states_APPENDIX.md

---

# 单循环状态机（v6.0 · P1-1，学 BMAD）

> **v6.0 变化**：不再有 3 套并行流程（V3 / v3.2 六步 / v3.3 五步）。
> 所有需求走**同一条循环**，`state.json.mode` 降级为**入口选择器**——只决定循环里哪些站激活。
> 旧 mode 值（lean_pm / standard_pm / enhanced_pm）全部兼容保留，仅语义更新。
> 历史状态别名映射见 states_APPENDIX。

---

## 循环视图

```
                 ┌────────────── 打回 / 改需求（SCOPE_CHANGE 回 INIT）──────────────┐
                 ↓                                                                  │
INIT → CLARIFYING? → DRAFTING → PM_CHECK? → PRD_ASSEMBLY → PRD_MID_REVIEW?          │
                                                                    ↓               │
              REVIEWING ⇄ REVISING → FINALIZING → PAUSE_GATE(方案) ─┤               │
                                                                    ↓               │
                              PROTOTYPING → PAUSE_GATE(原型) → COVERAGE_CHECK        │
                                                                    ↓               │
                                       IMPLEMENTING? → TESTING? → DELIVERED         │
                                                                    ↓               │
                                                          Learn（KG 入库 / 复盘）→ 下一 REQ
```

带 `?` 的站 = 可选站，由入口选择器决定是否激活。所有评审门（PAUSE_GATE / *_REVIEW）都等 PM 拍板。

---

## 核心状态清单（16 态 + 4 异常态，原 24 态）

| # | 状态 | 含义 | 推进者 | 推进条件 |
|---|---|---|---|---|
| 1 | INIT | REQ 目录已建 | supervisor | PM 说"开始新需求" |
| 2 | CLARIFYING | 澄清站（深度由入口定：跳过 / 5 维度 / 苏格拉底 5 阶段） | PM | 答完 / "跳过澄清" |
| 3 | DRAFTING | Specialists 并行起草 | specialists | 产出落 01_drafted/ |
| 4 | PM_CHECK | 起草中 PM 校验（B 模式可选站） | PM | 通过 / 加 / 改 / 跳过 |
| 5 | PRD_ASSEMBLY | supervisor 合并产出 | supervisor | prd.md 落盘 |
| 6 | PRD_MID_REVIEW | PRD 中评（可选站） | PM | 通过 / 打回 |
| 7 | REVIEWING | reviewer 独立审核（含 spec 质量门） | reviewer | review.md 落盘 |
| 8 | REVISING | Specialists 按意见修订 | specialists | 所有 issue 回应 |
| 9 | FINALIZING | 合并 final_prd.md | supervisor | final_prd 落盘 |
| 10 | PAUSE_GATE | PM 评审门（方案 / 原型共用） | PM | 通过 / 打回 / 改需求 |
| 11 | PROTOTYPING | 原型站（保真度由入口定；产 DESIGN.md + EXPERIENCE.md） | 原型 specialist | prototype/ 落盘 |
| 12 | COVERAGE_CHECK | FR×TC 覆盖检查 | 审计 specialist | coverage ≥ scale 阈值 |
| 13 | IMPLEMENTING | 研发实施（可选站） | 原型 B_dev | code/ 落盘 |
| 14 | TESTING | 审计测试（可选站） | 审计 | test_report.md 落盘 |
| 15 | DELIVERED | 已交付 → 触发 /deliver | supervisor | PM 确认 |
| 16 | BUG_FIXING | 交付后修缺陷 | 原型+审计 | bug_fix_in_progress 清空 |

异常态（4）：STUCK / SCOPE_CHANGE / ABANDONED / *_TIMEOUT——定义见 states_APPENDIX。

---

## 入口选择器（mode 字段新语义）

| 入口（mode 值） | 激活的站 | 适用 |
|---|---|---|
| `lean_pm`（快速） | 跳过 CLARIFYING、PM_CHECK、PRD_MID_REVIEW；原型低保真；跳过 IMPLEMENTING/TESTING | 小需求、只要文档+原型 |
| `standard_pm`（标准，默认） | CLARIFYING 按 scale（complex 开）；原型低保真+截图；含 COVERAGE_CHECK + TESTING | 常规需求 |
| `enhanced_pm`（深度） | 全站激活：苏格拉底 5 阶段 + PM_CHECK(B) + PRD_MID_REVIEW(complex) + 高保真 + 独立测试 | 大需求、复杂工程 |

**与 scale 的组合规则**：入口决定"走多少站"，scale 决定"每站的深度"（几个 specialist、覆盖阈值、评审轮次）。
scale 与入口冲突时（如 light + enhanced_pm）：scale 优先——light 永远跳过高保真和独立测试。

---

## 触发词

| PM 触发词 | 动作 |
|---|---|
| "开始新需求：XXX" | 标准入口（standard_pm），scale 自动判定 |
| "开始新需求：XXX 快速" / "精简模式" | 快速入口（lean_pm） |
| "开始新需求：XXX complex 深度" | 深度入口（enhanced_pm） |
| "本次要增强" / "开启增强模式" | 单次 / 持续切深度入口 |
| "本 REQ 升级到 complex" | scale 升级（站点不回退，只加深） |
| "跳过原型" | 单次跳过 PROTOTYPING 站 |
