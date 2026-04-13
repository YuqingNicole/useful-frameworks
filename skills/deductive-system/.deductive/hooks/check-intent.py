#!/usr/bin/env python3
"""
check-intent.py — 意图识别 Hook（command 类型）

触发时机: UserPromptSubmit（每条用户消息）
职责: 用 AI 判断用户回复是否为明确确认，不确定时注入提醒
设计: 只提醒不阻断（exit 0），AI 根据 CLAUDE.md 规则决定是否追问

原理对齐:
  - 意图识别 = 语言理解 → AI 的核心能力（适合用 AI）
  - 测试验证 = 逻辑判断 → 确定性代码（不适合用 AI）
  - 各归其位
"""

import sys
import os
import json

def main():
    # 读取用户消息
    try:
        event = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    content = event.get("content", "").strip()

    # 长消息大概率是新任务/问题，不是回复确认，跳过
    if not content or len(content) > 50:
        sys.exit(0)

    # 用 AI 做意图识别
    intent = _recognize_intent(content)

    if intent == "UNCERTAIN":
        result = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": (
                    f"⚠️ [意图识别] 用户回复「{content}」语气不确定。"
                    f"如果你正在等确认，请追问用户哪里不确定，不要直接继续执行。"
                )
            }
        }
        json.dump(result, sys.stdout)

    # 始终 exit 0，不阻断
    sys.exit(0)


def _recognize_intent(message: str) -> str:
    """调用 AI 判断用户意图。失败时降级为关键词匹配。"""
    # 尝试 AI 识别
    try:
        import anthropic
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            # 从 .env 读取
            env_file = os.path.join(os.getcwd(), ".env")
            if os.path.exists(env_file):
                with open(env_file) as f:
                    for line in f:
                        if line.startswith("ANTHROPIC_API_KEY="):
                            api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
        if not api_key:
            return _keyword_fallback(message)

        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": (
                f'用户说了："{message}"\n'
                "判断这是明确确认还是犹豫/不确定。\n"
                "明确确认（如'确认''对''好的''可以''没问题''是的'）→ 回答 CONFIRMED\n"
                "犹豫不确定（如'应该对吧''算是吧''嗯...''可能''我猜''好吧'）→ 回答 UNCERTAIN\n"
                "只回答一个词。"
            )}],
        )
        result = resp.content[0].text.strip().upper()
        if "UNCERTAIN" in result:
            return "UNCERTAIN"
        return "CONFIRMED"

    except Exception:
        # AI 不可用时降级为关键词匹配（C5: API不可靠）
        return _keyword_fallback(message)


def _keyword_fallback(message: str) -> str:
    """降级: 关键词匹配。"""
    UNCERTAIN_MARKERS = ["应该", "吧", "可能", "大概", "算是", "好像", "我猜", "勉强", "不太", "不确定"]
    CONFIRM_WORDS = {"确认", "对", "是的", "好的", "可以", "没问题", "确定", "同意", "是", "好", "继续"}

    if message in CONFIRM_WORDS:
        return "CONFIRMED"
    if any(m in message for m in UNCERTAIN_MARKERS):
        return "UNCERTAIN"
    return "CONFIRMED"  # 默认不干预


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)  # 任何异常都不阻断
