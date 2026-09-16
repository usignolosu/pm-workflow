#!/bin/bash
# heartbeat.sh — 心跳自检的本地状态摘要（v4.0 接线版）
# 定时触发：由 ZCode 自动化（工作日 09:00）或 PM 说"心跳自检"调用
# 用法：./scripts/heartbeat.sh
set -e

# Route X+：过程留痕写到工作区根，避免随 Skill 包分发出去
_pmw_detect_root() {
  # 1) 环境变量显式覆盖
  if [ -n "$PM_WORKFLOW_RUNS" ]; then
    printf '%s' "$PM_WORKFLOW_RUNS"
    return
  fi
  # 2) 从当前目录向上找 git 仓库根
  _d="$(pwd)"
  while [ "$_d" != "/" ]; do
    if [ -d "$_d/.git" ]; then
      printf '%s' "$_d"
      return
    fi
    _d="$(dirname "$_d")"
  done
  # 3) 兜底：用户 HOME 下（绝不落在 Skill 包内）
  printf '%s' "${HOME}/pm-workflow-runs"
}
RUNS_DIR="$(_pmw_detect_root)/runs"
mkdir -p "$RUNS_DIR"

echo "=== 💓 心跳自检 · 状态摘要 ==="
echo "时间: $(date '+%Y-%m-%d %H:%M %A')"
echo ""

# 1. 当前需求状态（Route X：state.json 随 run 隔离在 runs/<run-id>/）
STATE_FILE=$(ls -t "$RUNS_DIR"/*/state.json 2>/dev/null | head -1)
if [ -n "$STATE_FILE" ]; then
  echo "--- 当前状态（$STATE_FILE）---"
  python3 -c "
import json
s = json.load(open('$STATE_FILE'))
p = s.get('progress', {})
print(f\"  REQ: {s.get('current_req')} | phase: {s.get('phase')} | scale: {s.get('scale')} | mode: {s.get('mode')}\")
print(f\"  进度: {p.get('percent', '?')}% | {p.get('current_step_human', '')}\")
print(f\"  下一步: {p.get('next_action', '')}\")
if s.get('bug_fix_in_progress'):
    print(f\"  ⚠️ bug 修复进行中: {s['bug_fix_in_progress']}\")
"
else
  echo "  ⚠️ runs/ 下无 state.json（B 范式可能仅用 execution-log.md 留痕）"
fi
echo ""

# 2. 未收尾的 REQ（01_drafted 里非 DELIVERED 的）
echo "--- 进行中 / 暂停的 REQ ---"
for idx in "$RUNS_DIR"/*/01_drafted/INDEX.md; do
  req=$(basename "$(dirname "$idx")")
  st=$(grep -m1 "^state:" "$idx" | sed 's/state: *//')
  case "$st" in
    DELIVERED|ABANDONED) ;;
    *) echo "  $req → $st" ;;
  esac
done
echo ""

# 3. 最近 7 天反馈
echo "--- 最近 7 天 feedback_log ---"
FOUND=0
for f in $(find feedback_log -name "20*.md" -mtime -7 2>/dev/null); do
  FOUND=1
  echo "  $f"
done
[ "$FOUND" = "0" ] && echo "  （无）"
echo ""

# 4. KG 规模
if [ -f knowledge_graph/index.jsonl ]; then
  N=$(grep -c "" knowledge_graph/index.jsonl)
  echo "--- 知识图谱 ---"
  echo "  实体总数: ${N} , 查询: python3 scripts/query_kg.py"
fi
echo ""

echo "=== 自检动作（主编排在对话里执行）==="
echo "1. 读 agents/_TEMPLATE_HEARTBEAT.md 共享段 + 各角色 HEARTBEAT.md 角色段"
echo "2. 检查上方暂停 REQ 是否有可推进的门（如等 PM 签字则提醒 PM）"
echo "3. 反馈记录若连续 3 次同类问题 → 说'执行自进化'跑 evolve.sh"
