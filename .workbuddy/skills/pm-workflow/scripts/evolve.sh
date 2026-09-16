#!/bin/bash
# 触发自我进化（04:00 那个时间槽）
# 用法：./scripts/evolve.sh [agent_name]

AGENT="$1"
TODAY=$(date +%Y%m%d)

if [ -z "$AGENT" ]; then
  echo "用法: $0 <agent_name>"
  echo "进化所有 agent: $0 all"
  exit 1
fi

LOG_DIR="evolution_log"
mkdir -p "$LOG_DIR"

if [ "$AGENT" = "all" ]; then
  echo "=== 触发全部 agent 自我进化 ==="
  for d in agents/specialists/*/ agents/supervisor+reviewer/*/; do
    [ -f "$d/HEARTBEAT.md" ] || continue
    AGENT_NAME=$(basename "$d")
    LOG_FILE="$LOG_DIR/${AGENT_NAME}_${TODAY}.md"
    echo "  $AGENT_NAME -> $LOG_FILE"
    echo "# $AGENT_NAME 自我进化日志 $TODAY" > "$LOG_FILE"
    echo "" >> "$LOG_FILE"
    echo "## 变更摘要" >> "$LOG_FILE"
    echo "- 待 Codex 对话中执行" >> "$LOG_FILE"
  done
  echo ""
  echo "日志目录: $LOG_DIR/"
else
  LOG_FILE="$LOG_DIR/${AGENT}_${TODAY}.md"
  echo "=== $AGENT 自我进化 ==="
  echo "# $AGENT 自我进化日志 $TODAY" > "$LOG_FILE"
  echo "在 Codex 对话中读取 agents/.../$AGENT/HEARTBEAT.md 的 04:00 段执行" >> "$LOG_FILE"
  echo "日志: $LOG_FILE"
fi
