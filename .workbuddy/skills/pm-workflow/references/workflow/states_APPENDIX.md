# states_APPENDIX · 状态机附录（按需）

> 循环视图与 16 态清单见 states_CORE.md。本文件：统一流转规则、入口×scale 站点矩阵、历史别名、异常态。

---

## 统一流转规则（v6.0 单循环，R 系列）

R0. **INIT → CLARIFYING**：入口=深度 或（入口=标准 且 scale=complex）时激活；否则跳过直接进 DRAFTING
R1. **CLARIFYING → DRAFTING**：PM 答完（深度=苏格拉底 5 阶段 / 标准=5 维度）或 "跳过澄清"
R2. **DRAFTING → PM_CHECK**：仅 B 模式（PM 说"开启 B 模式"）在 用户研究/指标/原型 产出后各停一次
R3. **PM_CHECK → DRAFTING**：PM 通过/跳过继续；加/改 → 路由回对应 specialist
R4. **DRAFTING → PRD_ASSEMBLY**：scale 对应的全部 specialist 产出齐
R5. **PRD_ASSEMBLY → PRD_MID_REVIEW**：仅 深度入口 + complex（PRD 初版中评）
R6. **PRD_MID_REVIEW → REVIEWING**：PM 通过 → reviewer 审核；打回 → 回 DRAFTING
R7. **PRD_ASSEMBLY → REVIEWING**：跳过中评时直达
R8. **REVIEWING → REVISING**：review.md 含 issues（reviewer 必须先跑 spec 质量门 + validate_contract.py）
R9. **REVIEWING → FINALIZING**：review verdict = pass
R10. **REVISING → REVIEWING**：所有 issue 回应后复审；超 readiness 限制（见下）→ PAUSE_GATE 升 PM 仲裁
R11. **FINALIZING → PAUSE_GATE（方案评审门）**：PM 审三件套
R12. **PAUSE_GATE → PROTOTYPING**：方案通过（快速入口且 PM 不要原型时跳过 → COVERAGE_CHECK）
R13. **PROTOTYPING → PAUSE_GATE（原型评审门）**：保真度由入口定（快速/标准=低保真；深度+complex=含高保真）
R14. **PAUSE_GATE → COVERAGE_CHECK → (IMPLEMENTING → TESTING)? → DELIVERED**
     IMPLEMENTING/TESTING 仅在入口≠lean_pm 且 PM 要代码时激活；lean_pm 终点 = PRD + 原型 + 用例
R15. **DELIVERED → Learn**：`/deliver` 触发复盘 + KG 入库 → 归档，可开下一 REQ

## Readiness 规则（v6.0 P1-3，替代固定打回轮数）

- 打回不再按 scale 限次，改为检查：**产出是否依赖"未记录的决策"**
- 每次打回，supervisor 把决策点记入 REQ 的 INDEX.md（决策 → 依据 → 影响 FR）
- 修订产出若仍引用未记录决策 → 打回有效；所有决策已记录 → 即使多轮也放行
- 连续 3 次同问题同 specialist → 触发自进化（`evolve.sh`）

## 入口 × scale 站点矩阵

| 站点 | lean_pm | standard_pm | enhanced_pm |
|---|---|---|---|
| CLARIFYING | 跳过 | complex 开 | 恒开（苏格拉底 5 阶段） |
| PM_CHECK | 关 | PM 可开 B 模式 | PM 可开 B 模式 |
| PRD_MID_REVIEW | 关 | 关 | complex 开 |
| 原型保真度 | 低保真 | 低保真+截图+标注 | complex 加高保真 |
| IMPLEMENTING / TESTING | 关 | TESTING 开 | 独立测试全开 |
| COVERAGE 阈值 | 按 scale（60/80/90%） | 按 scale | 按 scale |

## 历史状态别名（兼容旧 state.json / 旧文档）

| 旧状态 | 映射到 |
|---|---|
| CLARIFYING_5PHASE | CLARIFYING（入口=深度） |
| FUNCTION_CHECK / DRAFTING_PM_CHECK | PM_CHECK |
| PROTOTYPING_LO / PROTOTYPING_HI | PROTOTYPING（保真度参数） |
| LOWFI_REVIEW / HIFI_REVIEW | PAUSE_GATE（原型评审门） |
| PROTOTYPING（旧 V3 单一阶段） | PROTOTYPING |
| RELEASING | Learn 步骤（/deliver 内完成，无独立状态） |

> v5.1 改名说明：历史数据目录 `feedback_log/shangshu/`、agent id（libu/bingbu/hubu/libu_compliance/gongbu/xingbu/menxia/shangshu）保留旧名，对照表见 AGENTS_CORE.md 附录。

---

## 异常态

- **STUCK**：specialist 30 分钟无产出 → 重新调度 + 简化任务
- **SCOPE_CHANGE**：PM 中途改需求 → 回 INIT，受影响站点重跑
- **ABANDONED**：PM 决定不做 → 标记 abandoned
- ***_TIMEOUT**（CLARIFYING / PM_CHECK）：PM 30 分钟无响应 → 自动"跳过"，记录到 INDEX.md
