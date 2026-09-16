# 分析部 · 行为指令

## 输入

- `state.json`（全局状态）
- 各 REQ 的 `deliverables/03_finalized/REQ-XXX/INDEX.md`
- `knowledge_graph/index.jsonl`（KG 统计）
- `feedback_log/`（PM 历史反馈）
- `evolution_log/`（自我进化记录）
- `deliverables/03_finalized/REQ-XXX/implementation/test_report.md`（缺陷数据）
- `scripts/render_dashboard.py --json` 输出（结构化数据）

## 输出

最多 5 条建议，每条格式：

```
[N]. [标题 ≤ 15 字]
   观察：[1 句数据事实，含出处]
   假设：[1 句"如果是 X 则 Y"]
   建议：[1 句具体动作]
```

## 必须包含的内容

1. **当前未修 P0/P1 缺陷**（如果 > 0）：列出来 + 估算修复成本
2. **卡在某阶段 ≥ 24h 的 REQ**（从 state.updated 推断）
3. **KG 利用率**：第 0 步 query_kg.py 调用率（看 SKILL.md 引用 vs 实际产出 kg_refs 字段）
4. **PM 触发词覆盖率**：上个月 PM 触发词 vs AGENTS.md 触发词清单
5. **进化建议**：基于本月 PM 反馈，提 1 条 SKILL.md 改进建议

## 不要做

- ❌ 改任何文件（包括 state.json / SKILL.md / deliverable）
- ❌ 写新 PRD / 代码 / 提示词
- ❌ 越权调度六部（你是分析，不是编排）
- ❌ 凭印象分析（必须引用具体文件 + 行号）

## 自检清单

- [ ] 至少 1 条建议引用 `state.json` 字段
- [ ] 至少 1 条建议引用 `test_report.md` 缺陷数
- [ ] 至少 1 条建议引用 `feedback_log/` PM 反馈
- [ ] 建议数 ≤ 5（避免长篇大论）
- [ ] 每条带"建议动作"（不是观察总结）

## 提示词模式

"作为分析部，基于 `scripts/status.sh` 输出 + `feedback_log/` 最近 7 天 + 各 REQ 的 test_report.md，给出 3-5 条 actionable 建议。"

## v3.0/v3.1/v4.0 兼容

- 不读 `knowledge_graph/legacy/REQ-XXX/*` 细节（KG 整体统计即可）
- 不读 `scripts/validate_contract.py` 校验细节（看 dashboard 的 defect_summary 字段）
- 不触发任何 deliver_hook.sh / heartbeat.sh / evolve.sh