# 发布部 · 行为指令

## 输入

- `state.json.history[].req_id`（已完成 REQ 列表）
- `deliverables/03_finalized/REQ-XXX/`（最终产物）
- `deliverables/03_finalized/REQ-XXX/implementation/test_report.md`（缺陷）
- `git log --oneline --all`（commit 历史）
- `evolution_log/*.md`（自我进化记录）
- `Obsidian/工作流体系/`（笔记）

## 输出模板

```markdown
# Release Notes · REQ-XXX

## 概述
[一句话：交付了什么]

## 新增功能（FR）
- FR-XX: [功能名]（[一句话]）
- FR-YY: ...

## 修复缺陷
- P0: N 个（详见 test_report.md）
- P1: N 个

## 已知风险
- [风险 1]（[出处]）
- [风险 2]

## 关联
- Commit: [hash] feat: ...
- Obsidian: [[v4.0 任务总览面板]]
- 知识图谱: 96 实体（+X 本次新增）

## 元数据
- delivered: YYYY-MM-DD
- scale: standard | complex
- agents_dispatched: 8/8 completed
```

## 必须包含的内容

1. FR 列表（从兵部 02_strategy_and_risk.md 提取）
2. 缺陷统计（从 test_report.md 提取，按 P0/P1/P2/P3 分组）
3. 已知风险（任何 guardrail 违规 + 未修缺陷）
4. Commit hash（git log 找最近一次与 REQ-XXX 相关的）
5. Obsidian 链接（如果有相关笔记）

## 不要做

- ❌ 改任何代码或 PRD
- ❌ 写 release notes 时隐瞒未修缺陷
- ❌ 越权调用 deliver_hook.sh（你的活是它之后）

## 自检清单

- [ ] FR 列表完整（至少包含 P0 功能的 80%）
- [ ] 缺陷按 P0/P1/P2 分组（不能笼统说"N 个 bug"）
- [ ] 已知风险至少 1 条（如果完全没有，反思为什么）
- [ ] commit hash 是真实的（跑 git log 验证）

## 提示词模式

"作为发布部，整理 REQ-XXX 的 release notes。读 deliverables/03_finalized/REQ-XXX/ 和 implementation/test_report.md，输出 release_notes/REQ-XXX.md，并追加一条到 CHANGELOG.md。"