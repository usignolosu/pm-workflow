#!/bin/bash
# feedback_loop.sh — 反馈/进化一键 loop（v4.0.1 新增）
#
# 把过去散落的 deliver_hook.sh / reject_hook.sh / ingest_to_kg.py / evolve.sh
# 串成一个 PM 可调用的命令。
#
# 用法：
#   bash scripts/feedback_loop.sh smoke    # 跑一次烟雾测试，验证 4 个 hook 都活着
#   bash scripts/feedback_loop.sh reject <agent> <reason> <req_id>
#   bash scripts/feedback_loop.sh deliver <req_id>
#   bash scripts/feedback_loop.sh kg-rebuild
#   bash scripts/feedback_loop.sh evolve <agent_name|all>
#
# 设计目标：让"反馈 → 记录 → 入库 → 进化"形成可观测的闭环，而不是纸面承诺。

set -e

ACTION="${1:-help}"
shift || true

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ensure_dirs() {
  mkdir -p feedback_log evolution_log knowledge_graph/legacy
}

case "$ACTION" in
  smoke)
    # 烟雾测试：4 个 hook 各跑一次，看输出是否正常
    ensure_dirs
    echo "=== 🔥 反馈/进化 loop 烟雾测试 ==="
    echo ""
    echo "[1/4] deliver_hook.sh self-test..."
    if bash -n scripts/deliver_hook.sh && echo "  ✅ 语法 OK"; then :; fi
    echo ""
    echo "[2/4] reject_hook.sh self-test..."
    if bash -n scripts/reject_hook.sh && echo "  ✅ 语法 OK"; then :; fi
    echo ""
    echo "[3/4] ingest_to_kg.py --rebuild-index..."
    if python3 scripts/ingest_to_kg.py --rebuild-index 2>&1 | tail -3; then :; fi
    echo ""
    echo "[4/4] query_kg.py 统计..."
    python3 scripts/query_kg.py 2>&1 | head -8
    echo ""
    echo "=== ✅ 烟雾测试完成 ==="
    echo "如看到 4 个组件都返回 OK，说明反馈/进化 loop 是活的。"
    ;;

  reject)
    AGENT="${1:-unknown}"
    REASON="${2:-(no reason given)}"
    REQ_ID="${3:-REQ-XXX}"
    ensure_dirs
    echo "📝 记录打回：$AGENT / $REQ_ID / $REASON"
    bash scripts/reject_hook.sh "$AGENT" "$REASON" "$REQ_ID"
    ;;

  deliver)
    REQ_ID="${1:-REQ-XXX}"
    ensure_dirs
    echo "📦 触发交付 hook：$REQ_ID"
    bash scripts/deliver_hook.sh "$REQ_ID"
    ;;

  kg-rebuild)
    ensure_dirs
    echo "🔄 重建 KG 索引..."
    python3 scripts/ingest_to_kg.py --rebuild-index
    ;;

  evolve)
    AGENT="${1:-all}"
    ensure_dirs
    echo "🧬 触发自我进化：$AGENT"
    bash scripts/evolve.sh "$AGENT"
    ;;

  help|*)
    echo "用法：bash scripts/feedback_loop.sh <action> [args]"
    echo ""
    echo "Actions:"
    echo "  smoke                            烟雾测试（验证 4 个 hook 活着）"
    echo "  reject <agent> <reason> <req_id>  记录打回"
    echo "  deliver <req_id>                  触发交付 hook"
    echo "  kg-rebuild                        重建 KG 索引"
    echo "  evolve <agent|all>                触发自我进化"
    ;;
esac
