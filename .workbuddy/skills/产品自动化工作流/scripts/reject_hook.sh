#!/bin/bash
# 打回事件钩子 — 实时追加反馈到 feedback_log
# 用法：./scripts/reject_hook.sh <agent_name> <reason> <req_id>
set -e
AGENT="$1"
REASON="$2"
REQ_ID="$3"
TODAY=$(date +%Y-%m-%d)
LOG_DIR="feedback_log/$AGENT"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/${TODAY}.md"

echo "# $TODAY 打回记录" >> "$LOG_FILE"
echo "- REQ: $REQ_ID" >> "$LOG_FILE"
echo "- 原因: $REASON" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# 更新打回计数器
COUNT_FILE="feedback_log/$AGENT/_reject_count"
echo $(($(cat "$COUNT_FILE" 2>/dev/null || echo 0) + 1)) > "$COUNT_FILE"
echo "反馈已记录到 $LOG_FILE"
