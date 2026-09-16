# 06_原型 SKILL · 角色入口（拆分后）

> v3.4 拆分：A1/A2/A3/B_dev 4 个角色单独文件，按需加载
> Codex 调度原型时按角色加载对应文件

## 快速链接

- 📄 [A1_solution.md](A1_solution.md) — 方案文档
- 🎨 [A2_prototype.md](A2_prototype.md) — 低保真原型
- 📷 [A3_screenshot.md](A3_screenshot.md) — 截图与标注索引
- 💻 [B_dev.md](B_dev.md) — 代码实施

## 拆分原则

- **按角色拆分**：每个文件 ~50-60 行，单一职责
- **共享段**（自检清单 + Guardrails + Scale + Load Order）保留在 SKILL.md
- **角色段**（A1/A2/A3/B）按角色独立

---
- [ ] 代码可启动（README 第一步就能跑）

## 提示词模式
"作为原型，设计以下需求的技术方案并制作原型：[需求]。输出 05_solution.md 和 prototype/ 目录。"

## 提示词模式
"作为 {角色名}，分析以下需求：[需求描述]。严格按 SKILL.md 输出 {产物文件}。"

---

## 产出防线（Guardrails）

### 通用约束（所有 Agent 必须遵守）

详见 （7 条权威定义）。

### 本 Agent 专用防线

- 技术方案必须注明每个组件/依赖的许可证类型（MIT/Apache/GPL/商业）。不得推荐无许可的闭源组件。
- 原型必须至少覆盖所有 P0 功能的交互流程。不得省略 P0 核心流程。
- **设计 token 约束（g015）**：HTML/方案中出现的设计色值必须在 contracts/design_tokens.yaml 内，硬编码 hex = 打回。
- **产出二分（v6.0）**：原型交付必须含 DESIGN.md + EXPERIENCE.md，缺任一 = 方案评审门不收。

---

## 需求分级适配（Scale-aware）

当前需求的 scale 等级在 state.json 的 scale 字段中定义。

不同 scale 的输出差异：

- light：不参与起草阶段。跳过方案设计和原型。
- standard：出方案文档（简述）+ 低保真原型
- complex：出完整方案 + 数据模型 + 低保真原型 + 核心流程动效

---

## 上下文装载顺序（Load Order）

> v2.0 新增：第 0 步查技术组件库。详见 `contracts/schema/load_order.yaml#gongbu`

开始工作前按以下顺序依次读取文件：

**方案阶段（A1）**：
0. **查知识图谱**（v2.0 新增，standard/complex 必走）
   ```bash
   bash scripts/query_kg.py --type tech_component --category ${category}
   ```
   拿到历史技术选型、许可证清单、坑点库（如"某些 SDK 在 iOS 18 崩溃"）。至少 1 个 counter_example（"反例：用了 GPL 库导致商业化踩坑"）。
1. 读取 01-04 全部上游产物
2. 读取 `contracts/README.md`（重点读 contracts/schema/guardrails.yaml 的通用防线 + g105/g106 原型专用）

**原型阶段（A2）**：
1. 读取 final_prd.md
2. 读取 05_solution.md
3. **读取 `contracts/design_tokens.yaml`**（v6.0：所有颜色/字号/间距/圆角必须引用 token，硬编码 hex = g015 打回）
4. 读取 `contracts/README.md`

**原型阶段产出（v6.0 P3-2，HTML 之外必交两份文档）**：
- **DESIGN.md**（视觉规范）：颜色/排版/间距/组件清单，全部标注 token 名（如 primary=blue-600）
- **EXPERIENCE.md**（行为规范）：页面状态机（加载/空/错误/成功）、异常流（断网/超时/空数据）、关键交互流程
- **冲突仲裁**：DESIGN/EXPERIENCE 文档与 HTML mockup 冲突时，以文档为准（BMAD 规则）

**代码实施（B）**：
1. 读取 final_prd.md
2. 读取 prototype/
