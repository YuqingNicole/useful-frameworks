# 演绎法系统（Deductive System）

基于 Claude Code Hooks 的 AI 开发质量守护系统。

## 它做什么

当你用 AI（Claude Code）开发项目时，这个系统确保：

1. **AI 不跳步** — 先展示规则、提验收要点、等你确认，再写代码
2. **改动不被破坏** — 每次 commit 自动运行验收测试，失败则阻止提交
3. **进度可见** — 自动追踪规则覆盖率，告诉你哪些需求有守卫、哪些裸奔
4. **你的犹豫被尊重** — AI 意图识别检测你的不确定语气，不会把"应该对吧"当成"确认"

## 核心设计原理

```
用确定性规则约束概率性 AI

T3（AI无推理能力）→ 测试验证用确定性 Python，不靠 AI 判断
T5（AI自信编造）→ 用户确认验收要点后 AI 才能写代码
R4（Prompt即程序）→ 工作流编码为 CLAUDE.md 指令
C5（API不可靠）→ gate-commit 零外部依赖
```

## 安装

### 1. 复制文件到你的项目

```bash
cp -r .deductive/ /your/project/.deductive/
cp -r .claude/ /your/project/.claude/
```

### 2. 配置 Claude Code Hooks

在 `~/.claude/settings.json` 的 `hooks` 字段中添加：

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 .deductive/hooks/check-intent.py",
            "timeout": 10
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .deductive/hooks/gate-commit.py",
            "if": "Bash(git commit*)"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .deductive/hooks/run-lint.py"
          }
        ]
      }
    ]
  }
}
```

### 3. 编辑规则

修改 `.deductive/acs/rules.json`，将规则替换为你的项目需求。

### 4. 选择模式

编辑 `.deductive/config.json`：

```json
{
  "mode": "observe"   // observe: 测试失败只提醒
                      // enforce: 测试失败阻止提交
}
```

## 文件结构

```
.deductive/
├── config.json              # 模式配置（observe/enforce）
├── state.json               # 实时状态（自动更新）
├── acs/
│   └── rules.json           # 规则注册表（你的需求清单）
├── hooks/
│   ├── gate-commit.py       # commit 门禁 + 覆盖率计算
│   ├── run-lint.py          # 编辑后即时 lint
│   └── check-intent.py      # 用户意图识别（AI驱动）
├── evidence/                # 验证存档（自动写入）
└── logs/                    # 执行日志

.claude/
└── CLAUDE.md                # AI 行为约束（演绎法工作流）

tests/
└── test_ac_*.py             # 验收测试（头部 # @covers: 规则ID）
```

## 使用方式

你什么都不用做。它是自动的。

| 你做什么 | 系统做什么 |
|---------|----------|
| 给 AI 任务 | AI 自动展示规则、提验收要点 |
| 说"确认" | AI 开始写代码 |
| 说"应该对吧" | AI 追问你哪里不确定 |
| 看 commit 输出 | 看到覆盖率和下次建议 |
| 切 enforce 模式 | 测试不过就不让提交 |

### commit 输出示例

```
✅ [演绎系统] 6 AC 通过 | 19/39 规则有守卫 (49%)
   建议下次覆盖: N2(日1000+), N6(大模型原理), N7(道)
```

## 写验收测试

每个测试文件头部声明覆盖的规则：

```python
# @covers: N4, D84, R5
"""
AC-002: 语义保真检查
验收要点:
  1. D84 初始化时加载 embedding 客户端
  2. 检查结果包含 embedding_used 字段
"""

def test_d84_uses_embedding():
    ...
```

gate-commit.py 自动扫描 `@covers` 标记，计算规则覆盖率。

## 设计文档

### 三层防线

```
第1层: CLAUDE.md — 约束 AI 对话行为（先规则、后确认、再代码）
第2层: check-intent.py — AI 意图识别，检测用户犹豫
第3层: gate-commit.py — commit 时确定性验证（AC 测试 + 覆盖率）
```

### LLM 原理对齐

| 原理 | 对策 |
|------|------|
| T3 无推理能力 | gate-commit 用确定性 Python 验证，不靠 AI |
| T5 自信编造 | 用户确认验收要点后才写代码；意图识别防止误判确认 |
| R4 Prompt即程序 | 工作流编码为 CLAUDE.md 显式指令 |
| C5 API不可靠 | gate-commit 零外部依赖；check-intent 降级为关键词匹配 |

## License

MIT
