# gates_APPENDIX · 软门 + 增强模式（按需）

> 5 硬门见 gates_CORE.md

---

## 软审批门（自动化为主，PM 可选介入）

### DRAFTING_PM_CHECK — B 模式下 PM 渐进校验（关键软门）
- **位置**：B 模式下用户研究/指标/原型-A1 产出后
- **PM 审查内容**：
  - PM-Check 1：用户画像是否准确
  - PM-Check 2：功能清单 + 指标是否覆盖需求
  - PM-Check 3：技术方案是否可行（预审，避免方案评审门才发现）
- **PM 可能的回复**：
  - "通过" → 进下一阶段
  - "加：xxx" → 路由回对应 Agent 补内容
  - "改：xxx" → 路由回对应 Agent 修订
  - "跳过" → 自动进下一阶段
- **超时兜底**：30 分钟无响应 → 自动"跳过"
- **详细规则**：见 `workflow/pm_checks.md`

### 阶段门 — 每个阶段结束
- 默认自动推进
- PM 可以说"暂停"中断
- 中断时记录到 INDEX.md

### 心跳门 — 04:00 自我进化
- 默认自动执行
- 涉及 SKILL.md 修订时记录到 evolution_log/
- PM 可以 review evolution_log/ 决定是否回滚

## 增强型 PM 模式 4 个新门（v3.2 新增）

> **触发条件**：`state.json.mode = "enhanced_pm"`（v3.2 模式）
> 旧 V3 模式（standard_pm）继续走原方案/原型 2 门，不受影响
> 详细流转见 `workflow/states.md` 第 6 步矩阵

### lowfi_review —— 低保真原型评审门（v3.2 步骤 3）

- **位置**：PROTOTYPING_LO 之后、PRD_ASSEMBLY 之前（对应 states_APPENDIX E4-E6）
- **触发条件**：`mode=enhanced_pm` AND 原型 A2 产出 `prototype/index.html`
- **等待**：PM 审查低保真 HTML（静态页面 + 占位文本）
- **PM 审查内容**：
  - 页面布局是否清晰
  - 核心流程是否能跑通
  - 文案是否真实（不要"按钮1"/"按钮2"）
- **PM 可能的回复**：
  - "通过" → 进 PRD_ASSEMBLY（合并 PRD）
  - "改：xxx" → 路由回原型 A2 修订
  - "打回：xxx" → 重做 A2
- **超时**：30 分钟无响应 → 自动"通过"（低保真容错性高）
- **仅 complex 跑**：standard/light 跳过此门

### prd_mid_review —— PRD 中期评审门（v3.2 步骤 4，complex 专属）

- **位置**：PRD_ASSEMBLY 之后、REVIEWING 之前
- **触发条件**：`mode=enhanced_pm` AND `scale=complex`
- **等待**：PM 审查 PRD 初版（prd.md）
- **PM 审查内容**：
  - PRD 第 1-7 章内容是否完整
  - 功能清单是否覆盖所有需求
  - 验收标准是否可衡量
- **PM 可能的回复**：
  - "通过" → 进 REVIEWING（评审组审核）
  - "改：xxx" → 路由回 6 部修订 → 重新 PRD_ASSEMBLY
- **超时**：30 分钟 → 自动"通过"
- **仅 complex**：standard 跳过此门（用旧 V3 的方案评审门替代）

### hifi_review —— 高保真原型评审门（v3.2 步骤 5，complex 专属）

- **位置**：PROTOTYPING_HI 之后、COVERAGE_CHECK 之前
- **触发条件**：`mode=enhanced_pm` AND `scale=complex`
- **等待**：PM 审查高保真 HTML（含动效 + 异常流程 + 状态机对应）
- **PM 审查内容**：
  - 异常流程是否完整（断网/超时/空数据）
  - 动效是否符合预期
  - 与 PRD 第 4 章场景是否对应
- **PM 可能的回复**：
  - "通过" → 进 COVERAGE_CHECK
  - "改：xxx" → 路由回原型 A4 修订
  - "打回：xxx" → 重做 A4
- **超时**：30 分钟 → 自动"通过"
- **仅 complex**：standard/light 跳过（高保真专属）

### coverage_check —— 用例覆盖检查门（v3.2 步骤 6）

- **位置**：高保真原型通过后、IMPLEMENTING 之前
- **触发条件**：`mode=enhanced_pm`
- **等待**：审计自动跑 `scripts/coverage_check.py`（无需 PM 介入）
- **检查项**：
  - FR × TC 覆盖矩阵
  - 覆盖率阈值（按 scale）：
    - light ≥ 60%
    - standard ≥ 80%
    - complex ≥ 90%
- **通过条件**：coverage ≥ scale 阈值
- **失败回退**：coverage < 阈值 → 路由回原型/审计补用例 → 重测
- **超时**：超时视为自动通过（审计脚本，不阻塞 PM）

---

## 门控的实现

主编排在执行 `git commit` 之前必须检查：
1. 当前状态是否在硬审批门上 -> 停下来输出"等待 PM 审查"，并给出当前产物路径
2. 是否有 SCOPE_CHANGE 标记 -> 走回炉流程
3. 方案评审门未通过前，原型不产出一行原型代码（原型 SKILL.md 的"角色 A"分为两段：A1 方案文档 / A2 原型）
4. B 模式下 DRAFTING 中途遇到 PM 校验点 → 停下来，输出"等待 PM"，记录到 INDEX.md
5. PM 校验 30 分钟无响应 → 自动"跳过"，继续 DRAFTING
6. **v3.2 新增**：mode=enhanced_pm 时，步骤 3/4/5/6 各门都按上表触发
