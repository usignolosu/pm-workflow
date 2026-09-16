#!/bin/bash
# bug_fix.sh — bug 修复工作流（v4.1）
#
# 启动 bug 修复流程：state.json 加 bug_fix_in_progress 字段，
# 路由给原型（修复）→ 审计（回归测试）→ 关闭。
#
# 用法：
#   bash scripts/bug_fix.sh <REQ-ID> <BUG-ID> [P0|P1|P2]
#   bash scripts/bug_fix.sh --list       # 列出当前 REQ 的所有 bug
#   bash scripts/bug_fix.sh --close <BUG-ID>  # 关闭 bug

set -e
cd "$(dirname "$0")/.."

# Route X+：过程留痕写到工作区根，避免随 Skill 包分发出去（消除 CWD 依赖）
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

# 解析 state.json 路径：优先 runs/<REQ_ID>/state.json；REQ_ID 缺失时扫描含该 bug 的 run
resolve_state() {
  if [ -n "$REQ_ID" ] && [ -f "$RUNS_DIR/$REQ_ID/state.json" ]; then
    echo "$RUNS_DIR/$REQ_ID/state.json"; return
  fi
  local f
  f=$(grep -rl "\"bug_id\": \"$BUG_ID\"" "$RUNS_DIR"/*/state.json 2>/dev/null | head -1)
  echo "${f:-$RUNS_DIR/${REQ_ID:-REQ-000}/state.json}"
}

LIST_FLAG=""
CLOSE_FLAG=""
REQ_ID=""
BUG_ID=""
SEVERITY=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --list) LIST_FLAG="list"; shift ;;
    --close) CLOSE_FLAG="close"; BUG_ID="$2"; shift 2 ;;
    --help|-h)
      echo "用法:"
      echo "  bash scripts/bug_fix.sh <REQ-ID> <BUG-ID> [P0|P1|P2]"
      echo "  bash scripts/bug_fix.sh --list [REQ-ID]"
      echo "  bash scripts/bug_fix.sh --close <BUG-ID>"
      exit 0
      ;;
    *)
      if [ -z "$REQ_ID" ]; then
        REQ_ID="$1"
      elif [ -z "$BUG_ID" ]; then
        BUG_ID="$1"
      elif [ -z "$SEVERITY" ]; then
        SEVERITY="$1"
      fi
      shift
      ;;
  esac
done

STATE="$(resolve_state)"

# === --list 模式 ===
if [ "$LIST_FLAG" = "list" ]; then
  echo "🐛 当前 REQ 的缺陷列表："
  echo ""
  for tr in "$RUNS_DIR"/REQ-*/03_finalized/implementation/test_report.md; do
    if [ ! -f "$tr" ]; then continue; fi
    REQ=$(basename $(dirname $(dirname $tr)))
    echo "=== $REQ ==="
    grep -E "P[0-3]|BUG|缺陷" "$tr" | head -10
    echo ""
  done
  exit 0
fi

# === --close 模式 ===
if [ "$CLOSE_FLAG" = "close" ]; then
  if [ -z "$BUG_ID" ]; then
    echo "ERROR: --close 必须指定 BUG-ID"
    exit 1
  fi

  python3 - << PYEOF
import json
from pathlib import Path
from datetime import datetime

state = json.loads(Path("$STATE").read_text(encoding="utf-8"))
bug_id = "$BUG_ID"

# 查找 bug
bugs = state.get("bug_fix_in_progress", [])
if isinstance(bugs, dict):
    bugs = [bugs]
closed = False
for b in bugs:
    if b.get("bug_id") == bug_id:
        b["status"] = "closed"
        b["closed_at"] = datetime.now().isoformat()
        closed = True
        print(f"✅ Bug {bug_id} 已关闭")
        break

if not closed:
    print(f"⚠️ Bug {bug_id} 未在 bug_fix_in_progress 中，可能已关闭")

# 写入 bug_history
history = state.setdefault("bug_history", [])
history.append({
    "bug_id": bug_id,
    "req_id": "$(echo $BUG_ID | cut -d: -f1)",
    "status": "closed",
    "closed_at": datetime.now().isoformat(),
})

Path("$STATE").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
print("✅ state.json 已更新")
PYEOF
  exit 0
fi

# === 启动新 bug 修复 ===
if [ -z "$REQ_ID" ] || [ -z "$BUG_ID" ]; then
  echo "ERROR: 必须提供 REQ-ID 和 BUG-ID"
  echo "  示例: bash scripts/bug_fix.sh 示例REQ-B BUG-001 P0"
  exit 1
fi

if [[ ! "$SEVERITY" =~ ^P[0-3]$ ]]; then
  echo "ERROR: 严重程度必须是 P0/P1/P2/P3，当前: $SEVERITY"
  exit 1
fi
# 兜底默认值（如果用户没传）
SEVERITY="${SEVERITY:-P2}"

echo "🐛 启动 bug 修复流程"
echo "   REQ:     $REQ_ID"
echo "   BUG-ID:  $BUG_ID"
echo "   Severity: $SEVERITY"
echo ""

# 读 test_report.md 找 bug 详情（Route X：改指 runs/<run-id>/）
TR_PATH="$RUNS_DIR/$REQ_ID/03_finalized/implementation/test_report.md"
if [ -f "$TR_PATH" ]; then
  echo "📄 找到 test_report.md，bug 详情："
  grep -A 3 "$BUG_ID" "$TR_PATH" | head -5
  echo ""
fi

# 更新 state.json
python3 - << PYEOF
import json
from pathlib import Path
from datetime import datetime

state = json.loads(Path("$STATE").read_text(encoding="utf-8"))

bug = {
    "bug_id": "$BUG_ID",
    "req_id": "$REQ_ID",
    "severity": "$SEVERITY",
    "status": "fixing",
    "started_at": datetime.now().isoformat(),
    "fixed_at": None,
    "verified_at": None,
    "assignee": "gongbu",  # 原型修复
}

# bug_fix_in_progress 字段
current = state.get("bug_fix_in_progress")
if current is None:
    state["bug_fix_in_progress"] = [bug]
elif isinstance(current, dict):
    state["bug_fix_in_progress"] = [current, bug]
elif isinstance(current, list):
    # 避免重复
    if not any(b.get("bug_id") == bug["bug_id"] for b in current):
        current.append(bug)

# next_action 更新
state["next_action"] = f"原型修复 {bug['bug_id']} ({bug['severity']})"

Path("$STATE").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
print("✅ state.json 已更新：bug_fix_in_progress =", state["bug_fix_in_progress"])
PYEOF

echo ""
echo "📋 下一步："
echo "   1. 原型按 BUG-ID 在 $TR_PATH 找修复点"
echo "   2. 修复代码 + 提交 commit: 'fix($BUG_ID): ...'"
echo "   3. 审计回归测试 + 更新 test_report.md"
echo "   4. 关闭 bug: bash scripts/bug_fix.sh --close $BUG_ID"
