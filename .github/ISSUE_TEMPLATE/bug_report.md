---
name: Bug 报告
about: 报告工作流 bug（机器门/契约/截图脚本异常）
title: "[BUG] "
labels: ["bug", "needs-triage"]
assignees: []
---

## 复现步骤

1. 在 WorkBuddy 会话里说：「……」
2. 跑命令：
   ```bash
   # 你跑的脚本/命令
   ```
3. 观察到的现象：……

## 期望

（你期望发生什么）

## 实际

（实际发生了什么）

## 环境

- **OS**：macOS / Linux / Windows（版本）
- **WorkBuddy 版本**：……
- **Python**：……（`python3 --version`）
- **Node**：……（`node --version`）
- **工作流版本**：v……（见 `SKILL.md` 顶部）

## 自检输出

```bash
$PY .workbuddy/skills/产品自动化工作流/scripts/self_check.py
```

（粘贴完整输出）

## 契约校验输出（如适用）

```bash
$PY .workbuddy/skills/产品自动化工作流/scripts/validate_contract.py --file <PRD 路径> --agent bingbu --scale complex --strictness strict --merged-prd
```

## 截图 / 日志

（如适用）

## 备注

（其它上下文）