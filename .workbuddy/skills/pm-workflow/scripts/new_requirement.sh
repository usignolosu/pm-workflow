#!/bin/bash
# v3.2 新增：--mode 参数（standard_pm | enhanced_pm）
# v4.0.1 新增：--merged-prd 参数（PM 选择走"合并稿"模式而非"分文件"模式）
# 用法：./scripts/new_requirement.sh "REQ-标题" [scale] [options]
#   scale: light | standard | complex（默认 standard）
#   --clarify | --no-clarify 覆盖 scale-dependent 默认
#   --mode standard_pm | enhanced_pm | lean_pm（默认 standard_pm，旧行为）
#   --step 1..6 指定 enhanced 模式当前从哪步开始
#   --merged-prd                走 prd.md 合并稿模式（不创建 01_user_research.md 等子文件）

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

TITLE="$1"
SCALE="${2:-standard}"
CLARIFY_FLAG=""
MODE="standard_pm"           # v3.2 新增：默认走 V3 旧行为
START_STEP=""
MERGED_PRD=""                # v4.0.1 新增：合并稿模式标志

# 解析可选 flag
for arg in "$@"; do
  case "$arg" in
    --clarify) CLARIFY_FLAG="clarification" ;;
    --no-clarify) CLARIFY_FLAG="none" ;;
    --mode=*) MODE="${arg#--mode=}" ;;
    --step=*) START_STEP="${arg#--step=}" ;;
    --merged-prd) MERGED_PRD="true" ;;
  esac
done

if [ -z "$TITLE" ]; then
  echo "用法: $0 \"需求标题\" [light|standard|complex] [options]"
  echo "  示例: $0 \"登录功能优化\" light"
  echo "  示例: $0 \"租车系统\" complex"
  echo "  示例: $0 \"内部知识库\" standard --clarify"
  echo "  示例: $0 \"企业智能客服\" complex --mode enhanced_pm"
  echo "  示例: $0 \"新项目\" standard --merged-prd"
  echo "  选项:"
  echo "    --clarify | --no-clarify        强制/跳过澄清门"
  echo "    --mode=standard_pm|enhanced_pm|lean_pm  PM 介入模式（v3.2）"
  echo "    --step=N                        enhanced 模式从第 N 步开始"
  echo "    --merged-prd                    合并稿模式（v4.0.1）：不创建 01_~05_ 子文件，"
  echo "                                    Specialists产物合入 prd.md 单文件"
  exit 1
fi

# 校验 mode
if [ "$MODE" != "standard_pm" ] && [ "$MODE" != "enhanced_pm" ] && [ "$MODE" != "lean_pm" ]; then
  echo "⚠️ mode 必须是 standard_pm / enhanced_pm / lean_pm，已重置为 standard_pm"
  MODE="standard_pm"
fi

if [ "$SCALE" != "light" ] && [ "$SCALE" != "standard" ] && [ "$SCALE" != "complex" ]; then
  echo "⚠️ scale 必须是 light / standard / complex，已重置为 standard"
  SCALE="standard"
fi

# 计算下一个 REQ 编号
LAST=$(ls "$RUNS_DIR" 2>/dev/null | grep -E '^REQ-[0-9]+$' | sort -V | tail -1 | sed 's/REQ-//' || echo "000")
NEXT=$(printf "%03d" $((10#$LAST + 1)))
REQ_ID="REQ-$NEXT"

# 建目录
mkdir -p "$RUNS_DIR/$REQ_ID/01_drafted/prototype"
mkdir -p "$RUNS_DIR/$REQ_ID/02_reviewed"
mkdir -p "$RUNS_DIR/$REQ_ID/03_finalized"

# v3.2 enhanced 模式：scale=complex 自动开苏格拉底 5 阶段
# v3.3 lean 模式：所有 scale 都开（PM 视角精简）
if [ "$MODE" = "enhanced_pm" ] && [ "$SCALE" = "complex" ]; then
  CLARIFICATION_PENDING="5phase"
  INITIAL_PHASE="CLARIFYING_5PHASE"
elif [ "$MODE" = "lean_pm" ]; then
  CLARIFICATION_PENDING="5phase"
  INITIAL_PHASE="CLARIFYING_5PHASE"
elif [ "$CLARIFY_FLAG" = "clarification" ]; then
  CLARIFICATION_PENDING="clarification"
  INITIAL_PHASE="CLARIFYING"
elif [ "$CLARIFY_FLAG" = "none" ]; then
  CLARIFICATION_PENDING="null"
  INITIAL_PHASE="INIT"
elif [ "$SCALE" = "complex" ]; then
  # scale=complex 默认开澄清门
  CLARIFICATION_PENDING="clarification"
  INITIAL_PHASE="CLARIFYING"
else
  # light/standard 默认跳过澄清门
  CLARIFICATION_PENDING="null"
  INITIAL_PHASE="INIT"
fi

# 写 INDEX.md（v3.2 加 mode 字段）
cat > "$RUNS_DIR/$REQ_ID/01_drafted/INDEX.md" <<EOT
# $REQ_ID 索引

state: $INITIAL_PHASE
scale: $SCALE
mode: $MODE
current_step: "${START_STEP:-1_clarifying}"
created: $(date +%Y-%m-%d)
title: $TITLE
pm_requirement: "$TITLE"
clarification_skipped: $([ "$CLARIFICATION_PENDING" = "null" ] && echo "true" || echo "false")
clarification_mode: $([ "$CLARIFICATION_PENDING" = "5phase" ] && echo "socratic-5phase" || echo "scale-dependent")

agents_dispatched:
  - 用户研究: pending
  - 战略: pending
  - 指标: pending
  - 合规: pending
  - 原型: pending
  - reviewer: pending
EOT

# 更新 state.json（v3.2 加 mode / current_step 字段）
# Route X：state.json 随 run 隔离在 runs/<run-id>/，不再整文件覆盖根级状态
TOTAL_STEPS=$([ "$MODE" = "lean_pm" ] && echo 5 || ([ "$MODE" = "enhanced_pm" ] && echo 6 || echo 4))
if [ "$INITIAL_PHASE" = "CLARIFYING_5PHASE" ] || [ "$INITIAL_PHASE" = "CLARIFYING" ]; then
  STEP_HUMAN="需求澄清"
  PERCENT=10
  NEXT_ACTION="请按澄清问题清单逐条回答，或说'跳过澄清'"
else
  STEP_HUMAN="PRD 草稿（Specialists并行起草）"
  PERCENT=25
  NEXT_ACTION="supervisor按 Load Order 调度Specialists起草"
fi

STATE_NEW=$(mktemp)
cat > "$STATE_NEW" <<EOT
{
  "current_req": "$REQ_ID",
  "phase": "$INITIAL_PHASE",
  "step": $([ "$INITIAL_PHASE" = "CLARIFYING_5PHASE" ] && echo '"等待 PM 苏格拉底 5 阶段"' || ([ "$INITIAL_PHASE" = "CLARIFYING" ] && echo '"等待 PM 澄清"' || echo "null")),
  "loop_count": 0,
  "gate": $([ "$INITIAL_PHASE" = "CLARIFYING_5PHASE" ] && echo '"苏格拉底门"' || ([ "$INITIAL_PHASE" = "CLARIFYING" ] && echo '"澄清门"' || echo "null")),
  "scale": "$SCALE",
  "mode": "$MODE",
  "current_step": "${START_STEP:-1_clarifying}",
  "clarification_pending": $([ "$CLARIFICATION_PENDING" = "null" ] && echo "null" || echo "\"$CLARIFICATION_PENDING\""),
  "clarification_skipped": $([ "$CLARIFICATION_PENDING" = "null" ] && echo "true" || echo "false"),
  "clarification_mode": $([ "$CLARIFICATION_PENDING" = "5phase" ] && echo '"socratic-5phases"' || echo '"scale-dependent"'),
  "updated": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "progress": {
    "current_step": "${START_STEP:-1_clarifying}",
    "current_step_human": "$STEP_HUMAN",
    "total_steps": $TOTAL_STEPS,
    "percent": $PERCENT,
    "next_action": "$NEXT_ACTION",
    "next_questions": [],
    "eta_minutes": 0
  }
}
EOT

python3 - "$STATE_NEW" <<PY
import json, sys
from pathlib import Path
new = json.load(open(sys.argv[1], encoding="utf-8"))
# Route X：state.json 随 run 隔离在 runs/<run-id>/（不再写根级）
p = Path("$RUNS_DIR") / "$REQ_ID" / "state.json"
p.parent.mkdir(parents=True, exist_ok=True)
# 同一 run 内保留历史 bug 字段（如有），否则写全新状态
old = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
for k in ("bug_fix_in_progress", "bug_history"):
    if k in old and k not in new:
        new[k] = old[k]
p.write_text(json.dumps(new, ensure_ascii=False, indent=2) + "\n")
PY
rm -f "$STATE_NEW"

echo "✅ 已创建 $REQ_ID（scale: $SCALE, mode: $MODE）"
echo "   标题: $TITLE"
echo "   INDEX: $RUNS_DIR/$REQ_ID/01_drafted/INDEX.md"
echo ""

if [ "$SCALE" == "light" ]; then
  echo "📋 轻量模式：仅调度 用户研究 + 战略 + 指标 + reviewer，跳过原型和审计"
elif [ "$SCALE" == "standard" ]; then
  echo "📋 标准模式：Specialists + reviewer全量调度"
else
  echo "📋 完整模式：Specialists + reviewer + 战略门 + 独立测试"
fi

# v3.2 mode 提示
echo ""
if [ "$MODE" = "enhanced_pm" ]; then
  echo "🚀 增强型 PM 模式（v3.2 6 步流程）"
  echo "   1. 需求澄清（5 阶段苏格拉底）→ 2. 功能确认 → 3. 低保真原型"
  echo "   4. PRD 评审 → 5. 高保真原型 → 6. 用例覆盖"
  if [ "$SCALE" = "complex" ]; then
    echo "   complex 走全 6 步"
  elif [ "$SCALE" = "standard" ]; then
    echo "   standard 走 4 步（跳过 5）"
  else
    echo "   light 仅 1 步（PRD 评审）"
  fi
fi

# 澄清门提示
echo ""
if [ "$INITIAL_PHASE" = "CLARIFYING_5PHASE" ]; then
  echo "🚦 苏格拉底 5 阶段澄清门已开（v3.2 新增）"
  echo "   supervisor将用 workflow/socratic_5phases.yaml 生成 5 阶段问题清单"
  echo "   写到 01_socratic_clarifications.md"
  echo "   请按阶段逐条回答，5 阶段全答完自动进 DRAFTING"
elif [ "$INITIAL_PHASE" = "CLARIFYING" ]; then
  echo "🚦 平面 5 维度澄清门已开（v3.1 旧版）"
  echo "   supervisor将生成 5 维度问题清单写到 01_clarifications.md"
  echo "   请回复 '回答 N：维度 = ...' 或 '✅ 答完了' 或 '跳过澄清'"
  echo ""
  echo "   调试命令：python3 scripts/clarify.py --req $REQ_ID show"
else
  echo "📋 澄清门跳过（scale=$SCALE + mode=$MODE 默认）"
  echo "   如需开启：'开启澄清门' 或重跑本脚本加 --clarify"
fi

echo ""
if [ "$MERGED_PRD" = "true" ]; then
  echo "📋 合并稿模式已启用（v4.0.1）：Specialists产出合并入 prd.md，不创建 01_~05_ 子文件"
  echo "   校验器请用: --file $RUNS_DIR/$REQ_ID/01_drafted/prd.md"
fi
echo ""
echo "下一步：supervisor自动判断是否进入澄清门，然后调度Specialists。"
