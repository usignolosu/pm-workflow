#!/bin/bash
# status.sh — 任务总览面板（薄壳，调用 render_dashboard.py）
#
# v4.0 重写：v3.0 之前是 22 行 grep 脚本（重复打印、无计数）。
# 现在只是 render_dashboard.py 的薄壳。
#
# 用法：
#   ./scripts/status.sh             # 终端面板
#   ./scripts/status.sh --obsidian # 写入 Obsidian 笔记
#   ./scripts/status.sh --json     # 输出 JSON

set -e
cd "$(dirname "$0")/.."

# 透传所有参数
exec python3 scripts/render_dashboard.py "$@"