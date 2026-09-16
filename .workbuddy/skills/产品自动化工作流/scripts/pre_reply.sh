#!/usr/bin/env bash
# scripts/pre_reply.sh — 回复级自检一键包装
#
# 两种调用方式：
#   1) stdin 模式（runtime 透传）
#      echo '{"reply":"...","had_tool_calls":false}' | bash scripts/pre_reply.sh
#   2) 参数模式（手工自检）
#      bash scripts/pre_reply.sh --reply "回到主线" --no-tool-call --pending 改AGENTS.md
#      bash scripts/pre_reply.sh --reply "我现在执行" --no-tool-call
#
# 退出码：0 = 放行 / 2 = 拦截

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CHECKER="$PROJECT_ROOT/runtime/pre_reply_check.py"

if [[ ! -f "$CHECKER" ]]; then
  echo "ERROR: $CHECKER not found" >&2
  exit 1
fi

# stdin 模式：原样透传
if [[ $# -eq 0 ]]; then
  python3 "$CHECKER"
  exit $?
fi

# 参数模式：转 JSON 喂给 checker
python3 - "$CHECKER" "$@" <<'PY'
import json, sys, subprocess

checker = sys.argv[1]
args = sys.argv[2:]

reply = ""
had_tool_calls = False
pending = []

i = 0
while i < len(args):
    a = args[i]
    if a == "--reply":
        reply = args[i + 1]; i += 2
    elif a in ("--had-tool-call", "--tool-call"):
        had_tool_calls = True; i += 1
    elif a in ("--no-tool-call", "--no-tool"):
        had_tool_calls = False; i += 1
    elif a == "--pending":
        pending = args[i + 1:]
        break
    else:
        print(f"unknown arg: {a}", file=sys.stderr); sys.exit(1)

payload = json.dumps({
    "reply": reply,
    "had_tool_calls": had_tool_calls,
    "pending_tasks": pending,
}, ensure_ascii=False)

r = subprocess.run(["python3", checker], input=payload, capture_output=True, text=True)
print(r.stdout, end="")
if r.stderr:
    print(r.stderr, end="", file=sys.stderr)
sys.exit(r.returncode)
PY
