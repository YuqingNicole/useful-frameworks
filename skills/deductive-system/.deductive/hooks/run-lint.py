#!/usr/bin/env python3
"""
run-lint.py — 编辑后即时 lint 反馈

触发时机: PostToolUse, matcher: Edit|Write
职责: 对刚修改的文件运行 lint，结果作为提醒注入上下文（不阻断）

设计原则:
  - 只提醒不阻断（A3': 验证在接受时强制，不在编辑时）
  - fail-open: 任何异常静默跳过
  - DISABLED 优先
"""

import sys
import os
import json
import subprocess
import time

DEDUCTIVE_DIR = ".deductive"
DISABLED_FILE = os.path.join(DEDUCTIVE_DIR, "DISABLED")
CONFIG_FILE = os.path.join(DEDUCTIVE_DIR, "config.json")
LOG_DIR = os.path.join(DEDUCTIVE_DIR, "logs")


def log(message: str):
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        with open(os.path.join(LOG_DIR, "run-lint.log"), "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {message}\n")
    except Exception:
        pass


def main():
    # ── Kill switch ──
    if os.path.exists(DISABLED_FILE):
        sys.exit(0)

    # ── 读取 stdin 事件 ──
    try:
        event = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    # ── 提取文件路径 ──
    tool_input = event.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    if not file_path:
        sys.exit(0)

    # 转为相对路径（Hook CWD = content-system/）
    try:
        rel_path = os.path.relpath(file_path, os.getcwd())
    except ValueError:
        rel_path = file_path

    # 只 lint src/ 下的 Python 文件
    if not rel_path.endswith(".py") or not rel_path.startswith("src/"):
        sys.exit(0)

    # 检查文件是否存在（可能是新建文件的路径还未写入）
    if not os.path.exists(rel_path):
        sys.exit(0)

    # ── 读取配置 ──
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception:
        sys.exit(0)

    lint_commands = config.get("lint_commands", [])
    if not lint_commands:
        sys.exit(0)

    # ── 运行 lint ──
    issues = []
    for cmd_template in lint_commands:
        cmd = f"{cmd_template} {rel_path}"
        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=15,
                cwd=os.getcwd()
            )
            output = proc.stdout.strip()
            if output and "All checks passed" not in output:
                issues.append(output)
        except Exception as e:
            log(f"lint error for {rel_path}: {e}")

    # ── 输出提醒（仅在有问题时） ──
    if issues:
        hint = f"⚠️ lint 发现问题:\n" + "\n".join(issues[:5])  # 最多5条
        result = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": hint
            }
        }
        log(f"lint issues for {rel_path}: {len(issues)} items")
        json.dump(result, sys.stdout)

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        try:
            log(f"UNHANDLED: {e}")
        except Exception:
            pass
        sys.exit(0)
