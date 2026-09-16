# A2_prototype · 低保真原型角色

> 原型 A2：方案评审门通过后
> 详细调度协议见 SKILL.md

---

## 角色 A2：低保真原型（方案评审门通过后）

### 触发条件
方案评审门 verdict = pass。在此之前不产出一行原型代码。

### 输入
已通过的方案文档 + final_prd.md

### 输出
两个：
1. `deliverables/REQ-XXX/01_drafted/05_solution.md`（更新版）
2. `deliverables/REQ-XXX/01_drafted/prototype/` 目录

### 05_solution.md 必须包含
- **API 契约定义**：每个端点必须给出完整 JSON 出参结构、降级策略、超时设置、缓存策略
- **降级/兜底策略**：每个依赖外部接口的模块必须写明数据源不可用时的降级链路（如：主数据源 → 第三方适配器 → 模拟数据）
- **离线容错**：无网络环境下每个 API 的行为说明
- **技术决策日志（TDL）**：至少记录数据源选型、持久化方案、离线容错策略、最低运行时版本

- 技术选型（前端/后端/存储/中间件）
- 数据模型（ER 图或表结构）
- API 列表（端点 + 入参 + 出参 + 错误码）
- 关键依赖（外部服务/SDK/库）
- 技术风险（与战略风险清单交叉验证）

### 知识图谱引用（v2.0 新增，standard/complex 必填）

在 05_solution.md 末尾添加 `## 知识图谱引用` 段：

```markdown
## 知识图谱引用
```yaml
kg_refs:
  - entity_id: REQ-XXX.TECH.NNN
    role: template | reference | counter_example
    note: 引用理由
```
```
