# 贡献指南

> 感谢你考虑为 **Pm Workflow** 贡献代码或文档。本项目以 MIT 协议开源，欢迎 PR、Issue、Discussion。

---

## 一、行为准则

- **尊重**所有贡献者，文明讨论
- **就事论事**——针对代码与方案，不针对个人
- **用证据说话**——PR 请附实测数据（self_check 输出、契约校验结果、截图等）

---

## 二、提什么最欢迎

按优先级：

| 类型 | 价值 | 难度 |
|---|---|---|
| 🐛 **Bug 报告**（机器门/契约/截图脚本异常） | 高 | 低 |
| 📖 **文档改进**（中英文不一致、示例补全） | 中 | 低 |
| 🛡 **新增 guardrail**（如 `g021`）| 高 | 中 |
| 🎨 **新增 8 阶段角色 / 模板**（如 `metrics_value` 实操模板）| 高 | 中 |
| ⚡ **性能优化**（截图脚本、知识图谱查询）| 中 | 中 |
| 🔧 **新脚本**（如 `scripts/design_token_check.py`、`scripts/readiness_check.py`——v8 候选） | 高 | 高 |

> **不欢迎**：把工作流改成独立 Web 应用 / 引入重型技术栈（LangGraph/FastAPI/Next.js）——本项目刻意保持 **Skill 形态 + 零独立进程**。

---

## 三、提交规范

### 3.1 Commit Message

```
<type>(<scope>): <subject>

<body>

<footer>
```

**type**：
- `feat` 新功能 / 新角色 / 新 guardrail
- `fix` 修 bug
- `docs` 仅文档
- `refactor` 重构（不改外部行为）
- `test` 仅测试
- `chore` 构建/依赖/工具

**示例**：
```
feat(guardrails): add g021 - detect citation of abandoned REQs

g021：扫描 PRD 中对已 ABANDONED 标记 REQ 的引用，发现即 warn。
理由：避免后续需求沿用过时结论（与 g014 counter_example 同源思路）。

实测：demo-20260101 历史 PRD 触发 0 次（未引用 ABANDONED），
但 guardrail_checkers.py 测试通过。
```

### 3.2 PR 必须附的实测

任一 PR，至少跑通以下两个命令并粘贴输出：

```bash
# 1) 链路自检（必须 10/10）
PY=$HOME/.workbuddy/binaries/python/envs/default/bin/python
$PY .workbuddy/skills/pm-workflow/scripts/self_check.py

# 2) 契约校验（不得新增 fail）
$PY .workbuddy/skills/pm-workflow/scripts/validate_contract.py \
  --file .workbuddy/skills/pm-workflow/runs/self-check/sample_prd.md \
  --agent bingbu --scale complex --strictness strict --merged-prd
```

---

## 四、本地开发环境

```bash
# 1. 克隆
git clone https://github.com/<your-org>/pm-workflow.git
cd pm-workflow

# 2. 受管运行时（macOS 由 WorkBuddy 自带）
PY=$HOME/.workbuddy/binaries/python/envs/default/bin/python
NODE=$HOME/.workbuddy/binaries/node/versions/22.22.2-3/bin/node

# 3. Python 依赖
$PY -m pip install -r requirements.txt

# 4. Node 依赖（受管 workspace）
export NODE_PATH=$HOME/.workbuddy/binaries/node/workspace/node_modules

# 5. 验证
$PY .workbuddy/skills/pm-workflow/scripts/self_check.py
```

> **Linux/Windows 用户**：受管运行时路径不同。请改用 `which python3` 自行定位，并把 `self_check.py` 中固定路径改为环境变量。

---

## 五、版本发布

- 本项目遵循 **语义化版本**（SemVer）：`MAJOR.MINOR.PATCH`
- **MAJOR**：v6 → v7 这种破坏性架构变更
- **MINOR**：新增角色 / 新增 guardrail / 新增规模
- **PATCH**：bug 修复 / 文档更正

发布时：
1. 更新 `.workbuddy/skills/pm-workflow/SKILL.md` 顶部版本号
2. 更新 README 顶部 badge
3. 打 git tag：`git tag -a v7.1.0 -m "..."`
4. 在 GitHub Releases 写变更说明（参考 [CHANGELOG 样例](.workbuddy/skills/pm-workflow/runs/self-check/execution-log.md) 末尾）

---

## 六、报告 Bug

请用 GitHub Issues 提交，需附：

1. **复现步骤**（你说了什么 / 跑什么命令）
2. **期望 vs 实际**
3. **环境**（OS / Python 版本 / WorkBuddy 版本）
4. **相关日志/截图**（self_check.py 输出、契约校验输出）

模板见 `.github/ISSUE_TEMPLATE/bug_report.md`。

---

## 七、提出 Feature

如果是新 guardrail / 新角色 / 新模板类大改动，请**先开 Discussion**，
达成共识后开 Issue → 再开 PR。**避免**直接发大 PR 占用 reviewer 时间。

---

## 八、不接受的内容

- 把 v5.1 的「三省六部 / 24 状态机」带回（已被 v7.0.0 单循环取代）
- 引入任何需要独立进程的服务（FastAPI/Next.js/LangGraph server）
- 在仓库根目录放敏感数据（即使只是示例）

---

*本贡献指南受 [GitHub Open Source Guides](https://opensource.guide/) 启发。*