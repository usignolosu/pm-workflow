# gates_CORE · 5 硬审批门（Codex 必读）

> 软门 + 增强模式 4 新门见 gates_APPENDIX.md

---

# 审批门 — 人类介入点

```
起草 → 审核 → FINALIZING(主编排合并方案文档)
  |
🚦 方案评审门 — PM 审查完整方案（Specialists产出 + final_prd）
  | 通过 → 原型出原型
  | 打回 → 对应 Agent 修订
  |
  → 原型出截图+标注索引（新步骤）
  |
🚦 原型评审门 — PM 审查截图+标注索引+原型
  | 通过 → 编号锁定，原型研发
  | 改标注 → 回 PROTOTYPING 修正标注编号
```
  |
  研发 → 测试 → 交付
```

两个评审门的分工：方案评审门看"做什么和怎么做"，原型评审门看"长什么样"。前者决定是否值得做，后者决定是否按这个方向做。

## 硬审批门（必须停下来等人）

### 澄清门 — 状态 CLARIFYING（v3.1 新增）
- **位置**：主编排建档（INIT）之后、调度Specialists起草（DRAFTING）之前
- **前置条件**：scale=complex 默认开；scale=standard 由 PM 说"开启澄清门"才开；scale=light 默认关
- **触发**：主编排读 `workflow/clarification_questions.yaml` + `initial_request.md`（如有）+ 查 KG，生成 5 维度问题清单写到 `deliverables/01_drafted/REQ-XXX/01_clarifications.md`
- **等待**：PM 主动答 5 个维度（背景/核心问题/预期范围/场景/用户）
- **PM 可能的回复**：
  - "回答 N：维度 = 答复" 或 "✅ 答完了" → 标 `clarification_pending=null`，`clarification_skipped=false`，进 DRAFTING
  - "跳过澄清" → 标 `clarification_pending=null`，`clarification_skipped=true`，用默认值进 DRAFTING
  - "清单再看一下" → 重新展示问题清单，不修改 state
  - 30 分钟无响应 → 自动跳过，标 `clarification_skipped: "timeout"`
- **谁有权**：PM（唯一）
- **与战略门区别**：战略门在 INIT **之前**（complex 专属），问"是否拆多个 REQ"；澄清门在 INIT **之后**，问"5 维度需求内容"
- **与 B 模式 PM-Check 区别**：澄清门在 DRAFTING **之前**，PM-Check 在 DRAFTING **中**。两者并存不替代
- **历史 REQ 豁免**：REQ-001~004 自动 `clarification_skipped=true`，校验器不报错

### 方案评审门 — 状态 FINALIZING 之后
- **位置**：主编排合并完全部方案文档（final_prd.md + 所有 01_drafted/ 产物）之后
- **前置条件**：评审组审核 verdict 为 pass
- **等待**：PM 审查完整的方案文档包
- **PM 审查内容**：
  - 用户研究产出：用户画像是否准确
  - 战略产出：功能清单是否完整，竞品/风险是否合理
  - 指标产出：验收标准是否可衡量，核心指标是否正确
  - 合规产出：合规风险是否可接受
  - 原型产出：技术方案是否可行（仅方案文档，无原型）
  - 主编排产出：final_prd.md 整体是否与 PM 意图一致
- **PM 可能的回复**：
  - "通过"：进入原型设计阶段（原型出截图+标注索引+原型 HTML）
  - "打回：XXX"：回 DRAFTING，仅修订 PM 提到的 Agent 的产出
  - "改需求：XXX"：回 INIT，标 SCOPE_CHANGE
  - "不做这个了"：标 ABANDONED

### 原型评审门 — 状态 PROTOTYPING 之后
- **位置**：原型产出的截图（screenshots/）+ 标注索引表（annotation.md）+ 原型（prototype/）完成后
- **等待**：PM 审查原型
- **PM 可能的回复**：
  - "通过"：进入研发实施
  - "改标注：XXX" → 回 PROTOTYPING 修正对应标注编号，不修改功能逻辑
  - "打回：XXX"：回 PROTOTYPING 修正对应标注编号或原型
  - "改需求：XXX"：回 INIT，标 SCOPE_CHANGE
  - "不做这个了"：标 ABANDONED

### 战略门 — 状态 INIT 之前
- **位置**：主编排识别到需求可能涉及：
  - 跨产品/跨业务线
  - 重大架构变更
  - 涉及多个现有 REQ 的关联
  - 投入超过阈值（由 PM 自定义）
- **动作**：停下来问 PM "这个需求是否要拆成多个 REQ"
- **不通过**：直接进 INIT，但标记 `risk: strategic`

### 冲突门 — REVISING 超过 3 轮
- **位置**：评审组与起草 Agent 持续分歧
- **动作**：停下来请 PM 仲裁，给出双方意见
- **PM 决定**：采纳评审组 / 采纳起草方 / 折中

## 门控的实现

主编排在执行 `git commit` 之前必须检查：
1. 当前状态是否在硬审批门上 -> 停下来输出"等待 PM 审查"，并给出当前产物路径
2. 是否有 SCOPE_CHANGE 标记 -> 走回炉流程
3. 方案评审门未通过前，原型不产出一行原型代码（原型 SKILL.md 的"角色 A"分为两段：A1 方案文档 / A2 原型）
4. B 模式下 DRAFTING 中途遇到 PM 校验点 → 停下来，输出"等待 PM"，记录到 INDEX.md
5. PM 校验 30 分钟无响应 → 自动"跳过"，继续 DRAFTING

## PM 的快速指令

PM 可以随时用这些短语：
- "通过" / "OK" / "下一阶段" -> 当前审批门通过
- "打回：XXX" -> 当前审批门打回，附修改指引
- "改：XXX" -> SCOPE_CHANGE
- "暂停" -> 冻结当前 REQ
- "继续" -> 恢复
- "跳过这一步" -> 跳过当前 Agent（风险自担）
- "重来" -> 整个 REQ 推到 INIT
- "方案已看，下一步" -> 方案评审门的快捷通过，跳过原型评审直入 IMPLEMENTING
- "方案OK，出原型看看" -> 方案评审门通过，进原型设计
- "原型OK，开干" -> 原型评审门通过，进研发

### v4.0.1 新增：mode=lean_pm 适配说明

`mode=lean_pm`（v3.3 5 步精简模式）下，上述指令语义变化：

| 指令 | standard/enhanced 模式 | **lean_pm 模式** |
|---|---|---|
| "通过" / "OK" / "下一阶段" | 进入下一阶段（含原型评审/研发/测试） | 直接进 DELIVERED 终点（lean_pm 总步数 = 5） |
| "方案已看，下一步" | 跳过原型评审直入 IMPLEMENTING | **不适用**（lean_pm 不进研发） |
| "原型OK，开干" | 原型评审门通过，进研发 | **不适用**（lean_pm 终点 = 原型 + 用例，不是代码） |
| "跳过原型" | 跳过原型评审门 | **不适用**（lean_pm 不走原型评审门） |

**结论**：lean_pm 模式下 PM 只在"方案评审门"做一次决策，通过即 DELIVERED。

---

