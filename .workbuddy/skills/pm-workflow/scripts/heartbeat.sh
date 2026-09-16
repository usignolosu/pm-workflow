#!/bin/bash
# heartbeat.sh — 心跳自检的本地状态摘要（v4.0 接线版）
# 定时触发：由 ZCode 自动化（工作日 09:00）或 PM 说"心跳自检"调用
# 用法：./scripts/heartbeat.sh
set -e

echo "=== 💓 心跳自检 · 状态摘要 ==="
echo "时间: $(date '+%Y-%m-%d %H:%M %A')"
echo ""

# 1. 当前需求状态
if [ -f state.json ]; then
  echo "--- 当前状态（state.json）---"
  python3 -c "
import json
s = json.load(open('state.json'))
p = s.get('progress', {})
print(f\"  REQ: {s.get('current_req')} | phase: {s.get('phase')} | scale: {s.get('scale')} | mode: {s.get('mode')}\")
print(f\"  进度: {p.get('percent', '?')}% | {p.get('current_step_human', '')}\")
print(f\"  下一步: {p.get('next_action', '')}\")
if s.get('bug_fix_in_progress'):
    print(f\"  ⚠️ bug 修复进行中: {s['bug_fix_in_progress']}\")
"
else
  echo "  ⚠️ state.json 不存在"
fi
echo ""

# 2. 未收尾的 REQ（01_drafted 里非 DELIVERED 的）
echo "--- 进行中 / 暂停的 REQ ---"
for idx in 归档需求产出/*/01_drafted/INDEX.md; do
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
