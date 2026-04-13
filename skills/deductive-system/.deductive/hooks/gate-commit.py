#!/usr/bin/env python3
"""
gate-commit.py — 演绎法系统核心 Hook (v2)

触发时机: PreToolUse, matcher: Bash, if: Bash(git commit*)

职责:
  1. 运行所有 AC 测试
  2. 扫描 @covers 标记，计算规则覆盖率
  3. 更新 state.json（活状态）
  4. 写入 evidence/（验证存档）
  5. 顺序锁：修改 src/ 时必须同时修改/新增 test_ac_*

设计原则:
  - T3(无推理): 全部逻辑为确定性 Python，零 LLM 调用
  - T5(自信编造): 只信测试结果，不信 AI 自述
  - C5(不可靠): 零外部依赖，fail-open
  - DISABLED 优先: .deductive/DISABLED 存在即跳过
"""

import sys
import os
import json
import glob
import re
import subprocess
import time

# ============================================================
# 常量
# ============================================================
DEDUCTIVE_DIR = ".deductive"
DISABLED_FILE = os.path.join(DEDUCTIVE_DIR, "DISABLED")
CONFIG_FILE = os.path.join(DEDUCTIVE_DIR, "config.json")
RULES_FILE = os.path.join(DEDUCTIVE_DIR, "acs", "rules.json")
STATE_FILE = os.path.join(DEDUCTIVE_DIR, "state.json")
LOG_DIR = os.path.join(DEDUCTIVE_DIR, "logs")
EVIDENCE_DIR = os.path.join(DEDUCTIVE_DIR, "evidence")
LOG_FILE = os.path.join(LOG_DIR, "gate-commit.log")


def log(message: str):
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {message}\n")
    except Exception:
        pass


def output_allow(reason: str = "", context: str = ""):
    result = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"}}
    if context:
        result["hookSpecificOutput"]["additionalContext"] = context
    json.dump(result, sys.stdout)
    sys.exit(0)


def output_deny(reason: str):
    result = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "reason": reason}}
    json.dump(result, sys.stdout)
    sys.exit(2)


# ============================================================
# 规则覆盖率计算
# ============================================================
def scan_covers(test_pattern: str) -> dict:
    """扫描 test_ac_*.py 文件中的 @covers 声明，构建 规则→测试 映射。"""
    covers_map = {}  # rule_id → [test_file, ...]
    test_files = sorted(glob.glob(test_pattern))

    for tf in test_files:
        try:
            with open(tf, "r", encoding="utf-8") as f:
                header = f.read(1000)  # 只读前 1000 字符
            # 匹配 # @covers: N1, D79, T3
            match = re.search(r"#\s*@covers:\s*(.+)", header)
            if match:
                rule_ids = [r.strip() for r in match.group(1).split(",")]
                for rid in rule_ids:
                    covers_map.setdefault(rid, []).append(os.path.basename(tf))
        except Exception:
            pass

    return covers_map


def compute_coverage(rules_file: str, covers_map: dict, test_results: dict) -> dict:
    """计算规则覆盖率和满足率。"""
    try:
        with open(rules_file, "r", encoding="utf-8") as f:
            rules_data = json.load(f)
    except Exception:
        return {"total": 0, "covered": 0, "green": 0, "uncovered_ids": []}

    rules = rules_data.get("rules", {})
    total = len(rules)
    covered = 0
    green = 0
    uncovered_ids = []

    for rule_id, rule in rules.items():
        if rule_id in covers_map:
            covered += 1
            rule["ac_test"] = ", ".join(covers_map[rule_id])
            # 检查覆盖该规则的测试是否全通过
            all_pass = all(
                test_results.get(tf, False)
                for tf in covers_map[rule_id]
            )
            if all_pass:
                green += 1
                rule["status"] = "green"
                rule["verified_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            else:
                rule["status"] = "red"
        else:
            rule["ac_test"] = None
            rule["status"] = "uncovered"
            uncovered_ids.append(rule_id)

    # 回写 rules.json
    try:
        with open(rules_file, "w", encoding="utf-8") as f:
            json.dump(rules_data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return {
        "total": total,
        "covered": covered,
        "green": green,
        "uncovered_ids": uncovered_ids,
    }


# ============================================================
# 状态更新
# ============================================================
def update_state(state_file: str, coverage: dict, test_file_count: int, all_passed: bool):
    """更新 state.json（活状态）。"""
    state = {
        "status": "green" if all_passed else "red",
        "total_acs": test_file_count,
        "total_verified": coverage["green"],
        "total_rules": coverage["total"],
        "rules_covered": coverage["covered"],
        "rules_green": coverage["green"],
        "coverage_pct": round(coverage["covered"] / max(coverage["total"], 1) * 100, 1),
        "satisfaction_pct": round(coverage["green"] / max(coverage["total"], 1) * 100, 1),
        "uncovered_rules": coverage["uncovered_ids"],
        "last_verified_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "current_crystallization": None,
    }
    try:
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ============================================================
# 证据存档
# ============================================================
def write_evidence(evidence_dir: str, coverage: dict, test_output: str, duration_ms: int):
    """写入验证证据。"""
    try:
        os.makedirs(evidence_dir, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        evidence = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "duration_ms": duration_ms,
            "coverage": coverage,
            "test_output_tail": test_output[-500:] if len(test_output) > 500 else test_output,
        }
        with open(os.path.join(evidence_dir, f"{ts}.json"), "w", encoding="utf-8") as f:
            json.dump(evidence, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ============================================================
# 顺序锁：修改 src/ 必须有 AC 测试
# ============================================================
def check_sequence_lock(mode: str) -> str | None:
    """检查是否修改了 src/ 但未修改/新增 test_ac_*。返回提醒/阻止文本或 None。"""
    try:
        staged = subprocess.run(
            "git diff --cached --name-only",
            shell=True, capture_output=True, text=True, timeout=10,
        )
        files = staged.stdout.strip().split("\n") if staged.stdout.strip() else []

        has_src_change = any(f.startswith("src/") or "/src/" in f for f in files)
        has_ac_change = any("test_ac_" in f for f in files)

        if has_src_change and not has_ac_change:
            msg = "修改了 src/ 生产代码但未新增/修改 AC 测试"
            if mode == "enforce":
                return f"⛔ [顺序锁] {msg}。请先写 AC 测试再改代码。"
            else:
                return f"⚠️ [顺序锁·观察] {msg}"
    except Exception:
        pass
    return None


# ============================================================
# 主逻辑
# ============================================================
def main():
    # ── Kill switch ──
    if os.path.exists(DISABLED_FILE):
        log("DISABLED file exists, allowing")
        sys.exit(0)

    # ── 读取配置 ──
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        log(f"config read error: {e}, allowing (fail-open)")
        sys.exit(0)

    mode = config.get("mode", "observe")
    test_command = config.get("test_command", "python3 -m pytest")
    test_pattern = config.get("test_pattern", "tests/test_ac_*.py")
    timeout = config.get("timeout", 60)

    # ── 顺序锁检查 ──
    seq_lock_msg = check_sequence_lock(mode)

    # ── 发现 AC 测试文件 ──
    test_files = sorted(glob.glob(test_pattern))
    if not test_files:
        hint = "💡 [演绎系统] 未发现 AC 测试文件，提交放行。"
        if seq_lock_msg:
            hint += f"\n{seq_lock_msg}"
        log(f"no AC tests found (pattern={test_pattern}), allowing")
        output_allow(context=hint)

    # ── 运行测试 ──
    cmd = f"{test_command} {' '.join(test_files)} --tb=short -q"
    log(f"running: {cmd}")

    start = time.time()
    try:
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout, cwd=os.getcwd())
        duration_ms = int((time.time() - start) * 1000)
        exit_code = proc.returncode
        stdout = proc.stdout.strip()
    except subprocess.TimeoutExpired:
        log(f"test timeout ({timeout}s), allowing (fail-open)")
        output_allow(context=f"⚠️ [演绎系统] 测试超时({timeout}s)，提交已放行。")
    except Exception as e:
        log(f"test execution error: {e}, allowing (fail-open)")
        sys.exit(0)

    all_passed = (exit_code == 0)

    # ── 扫描 @covers + 计算覆盖率 ──
    covers_map = scan_covers(test_pattern)

    # 构建测试文件通过/失败映射
    test_results = {}
    for tf in test_files:
        basename = os.path.basename(tf)
        # 简单判断: 如果整体通过则全通过，否则检查具体文件
        test_results[basename] = all_passed  # 简化：全局 pass/fail

    coverage = {"total": 0, "covered": 0, "green": 0, "uncovered_ids": []}
    if os.path.exists(RULES_FILE):
        coverage = compute_coverage(RULES_FILE, covers_map, test_results)

    # ── 更新 state.json ──
    update_state(STATE_FILE, coverage, len(test_files), all_passed)

    # ── 写入 evidence ──
    write_evidence(EVIDENCE_DIR, coverage, stdout, duration_ms)

    log(f"mode={mode} exit={exit_code} files={len(test_files)} duration={duration_ms}ms "
        f"coverage={coverage['covered']}/{coverage['total']} green={coverage['green']}")

    # ── 构建输出信息 ──
    cov_pct = round(coverage["covered"] / max(coverage["total"], 1) * 100)
    sat_pct = round(coverage["green"] / max(coverage["total"], 1) * 100)

    if all_passed:
        context = (
            f"✅ [演绎系统] {len(test_files)} AC 通过 ({duration_ms}ms)"
            f" | {coverage['covered']}/{coverage['total']} 规则有守卫 ({cov_pct}%)"
        )
        if coverage["uncovered_ids"]:
            # 建议下次覆盖的规则（显示前3条）
            suggest = coverage["uncovered_ids"][:3]
            try:
                with open(RULES_FILE, "r", encoding="utf-8") as f:
                    rd = json.load(f)
                suggest_names = [f"{rid}({rd['rules'][rid]['name']})" for rid in suggest if rid in rd.get("rules", {})]
            except Exception:
                suggest_names = suggest
            remaining = len(coverage["uncovered_ids"]) - 3
            context += f"\n   建议下次覆盖: {', '.join(suggest_names)}"
            if remaining > 0:
                context += f" (+{remaining}条)"
        if seq_lock_msg and "⚠️" in seq_lock_msg:
            context += f"\n   {seq_lock_msg}"
        log("all passed, allowing")
        output_allow(context=context)
    else:
        fail_lines = [l for l in stdout.split("\n") if "FAILED" in l or "ERROR" in l]
        test_output = stdout[-500:] if len(stdout) > 500 else stdout

        if mode == "observe":
            context = (
                f"💡 [演绎系统·观察模式]\n\n"
                f"AC 测试结果 ({duration_ms}ms):\n{test_output}\n\n"
                f"规则覆盖 {coverage['covered']}/{coverage['total']} ({cov_pct}%)"
                f" | 满足率 {sat_pct}%\n"
                f"observe 模式，提交已放行。"
            )
            if seq_lock_msg:
                context += f"\n{seq_lock_msg}"
            log(f"observe mode, tests failed but allowing")
            output_allow(context=context)
        else:
            reason = (
                f"⛔ [演绎系统] 提交被阻止\n\n"
                f"AC 测试未通过 ({duration_ms}ms):\n{test_output}\n\n"
                f"规则覆盖 {coverage['covered']}/{coverage['total']} ({cov_pct}%)"
                f" | 满足率 {sat_pct}%\n"
                f"请修复后重新提交。临时跳过: touch .deductive/DISABLED"
            )
            log(f"enforce mode, blocking commit")
            output_deny(reason)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        try:
            log(f"UNHANDLED EXCEPTION: {e}")
        except Exception:
            pass
        sys.exit(0)
