#!/bin/bash
# 交付事件钩子 — 扫描 REQ 反馈并归档 + v2.0 自动入库 KG
# 用法：./scripts/deliver_hook.sh <req_id>
set -e
# Route X：活动需求目录改指 runs/<run-id>/（不再读根级 归档需求产出/）
RUNS_DIR="$(cd "$(dirname "$0")/../runs" && pwd)"
REQ_ID="$1"
REVIEW_FILE="$RUNS_DIR/$REQ_ID/02_reviewed/review.md"
REJECT_LOG="feedback_log/_delivery_$REQ_ID.md"

echo "# $REQ_ID 交付复盘" > "$REJECT_LOG"
echo "- 交付日期: $(date +%Y-%m-%d)" >> "$REJECT_LOG"

if [ -f "$REVIEW_FILE" ]; then
  grep -E "P0|P1|打回|verdict" "$REVIEW_FILE" | while read line; do
    echo "- $line" >> "$REJECT_LOG"
  done
fi

echo "复盘记录已写入 $REJECT_LOG"

# -----------------------------------------------------------------------------
# v2.0 新增：DELIVERED 时自动入库到知识图谱
# -----------------------------------------------------------------------------
echo ""
echo "📦 v2.0 自动入库知识图谱..."
if [ -f "$RUNS_DIR/$REQ_ID/01_drafted/01_user_research.md" ]; then
  python3 scripts/ingest_to_kg.py --req "$REQ_ID" --mode semi-auto
else
  echo "⚠️ 无 01_user_research.md，跳过 KG 入库"
fi

# -----------------------------------------------------------------------------
# v2.0 新增：写 evolution_log 记录本次入库
# -----------------------------------------------------------------------------
echo "$(date +%Y-%m-%d): DELIVERED $REQ_ID - KG 自动入库完成" >> evolution_log/_auto_ingest.log

# -----------------------------------------------------------------------------
# v4.0 新增：交付后自动渲染 Obsidian 任务总览
# -----------------------------------------------------------------------------
python3 scripts/render_dashboard.py --obsidian 2>&1 || echo "⚠️ Obsidian 渲染失败（不影响交付）"

echo ""
echo "✅ deliver_hook.sh 完成"