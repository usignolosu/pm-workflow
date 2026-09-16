# HEARTBEAT 模板（v3.4 · 1 份 + 角色变量注入）

> v3.4 优化：HEARTBEAT.md 模板化
> 每份 HEARTBEAT.md 只需包含"角色特定段"，其他 4 段（事件触发表 / 打回 / 交付 / KG 缓存预热）都在本模板里
> 详见 [Obsidian · 角色说明](工作流体系/角色说明.md#heartbeat-模板)

## 共享段（4 段，所有角色通用）

### 触发方式（共享）

| 触发事件 | 入口 | 说明 |
|---|---|---|
| 工作日 09:00 | ZCode 定时自动化 → `/heartbeat` | 读 HEARTBEAT 模板 + heartbeat.sh 状态摘要，输出自检报告；周一额外做 KG 盘点 |
| PM 说"心跳自检" / `/heartbeat` | `.zcode/commands/heartbeat.md` | 同上，手动触发 |
| 打回事件（PM 说"打回：XXX" / `/reject`） | scripts/reject_hook.sh | 实时追加反馈到 feedback_log/ |
| 交付事件（状态变为 DELIVERED / `/deliver`） | scripts/deliver_hook.sh | 扫描本次 REQ 所有 PM 反馈 + KG 自动入库 |
| 手动触发（PM 说"执行自进化"） | scripts/evolve.sh | 读 feedback_log/ 修订 SKILL.md |

> 时间槽说明：v3.4 之前的 morning/evening/04:00 定时槽在没有调度器的对话环境里不可执行，
> v4.0 起由 ZCode 定时自动化（工作日 09:00 心跳，周一含 KG 盘点）真实承载，见 `.zcode/config.json` 与自动化配置。

### 打回钩子（共享）
打回原因被实时记录到 feedback_log/{agent}/，作为后续进化的原始数据。连续 3 次同问题被同一 Agent 触发 → 触发自我进化。

### 交付钩子（共享）
交付时扫描本次 REQ 的审核记录，提取 PM 反馈，归档到 feedback_log/。v2.0 起自动调 ingest_to_kg.py 把画像/场景/洞察入库。

### KG 缓存预热（共享）
每个工作日开工前调一次 `bash scripts/query_kg.py --type persona,scenario,insight --scale all > /tmp/kg_cache_${date}.txt`

## 角色特定段（每份 HEARTBEAT.md 只需放这段）

### 打回场景（角色相关）
- 场景 1：[角色常见 PM 反馈]
- 场景 2：[角色常见 PM 反馈]
- ...

### 反馈归类（角色相关）
- 类型 1：[角色特有问题]
- 类型 2：[角色特有问题]

### 进化指标（角色相关）
- 指标 1：[角色 KPI]
- 指标 2：[角色 KPI]
