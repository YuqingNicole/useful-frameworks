export default function Home() {
  const frameworks = [
    {
      category: "🎯 产品框架",
      description: "产品经理必备的方法论和工具",
      items: [
        "PRD 写作框架 - SPACE-prd-writer",
        "优先级排序 - RICE/ICE/Kano 模型",
        "竞品分析 - 四维拆解法",
        "实验设计 - A/B 测试完整方案",
        "路线图规划 - 里程碑设计"
      ]
    },
    {
      category: "📊 研究方法",
      description: "用户研究和数据分析方法论",
      items: [
        "问卷设计 - 避坑指南",
        "数据分析 - 指标拆解 + 归因",
        "用户调研 - 定性研究方法",
        "埋点设计 - 事件规范",
        "复盘报告 - 结构化总结"
      ]
    },
    {
      category: "🧠 决策框架",
      description: "投资和商业决策工具",
      items: [
        "投资决策 - 多视角备忘录",
        "价值评估 - 四维评分模型",
        "风险判断 - 流动性指标",
        "市场情绪 - 5 核心指标",
        "BTC 底部模型 - 6 维判断"
      ]
    },
    {
      category: "📈 分析模型",
      description: "财报和市场分析框架",
      items: [
        "财报深挖 - 16 模块分析",
        "市场情绪 - 机构/散户监控",
        "宏观流动性 - 风险预警",
        "价值投资 - ROE/现金流/护城河",
        "技术分析 - RSI/MVRV 等"
      ]
    },
    {
      category: "✍️ 内容创作",
      description: "写作和内容生产工具",
      items: [
        "人性化改写 - 去 AI 味",
        "社交内容 - 多平台适配",
        "设计风格 - Variant 方法论",
        "原型设计 - 截图转 HTML",
        "评审模拟 - 多角色视角"
      ]
    },
    {
      category: "🎨 前端设计",
      description: "界面逻辑和信息架构设计",
      items: [
        "前端逻辑设计 - 四层信息深度模型",
        "MECE 原则 - 信息分类不重不漏",
        "渐进式披露 - 按深度递进展示",
        "施耐德曼法则 - 概览优先缩放筛选",
        "容器决策树 - 交互组件选择"
      ]
    },
    {
      category: "🛡️ 开发质量",
      description: "AI 开发质量守护系统",
      items: [
        "演绎法系统 - AI 不跳步、改动不被破坏",
        "三层防线 - CLAUDE.md + 意图识别 + 门禁测试",
        "规则覆盖率 - 自动追踪需求守卫状态",
        "意图识别 - 检测用户犹豫语气",
        "验收测试 - commit 时确定性验证"
      ]
    },
    {
      category: "🔧 技术工具",
      description: "开发和技术相关工具",
      items: [
        "GitHub 操作 - gh CLI 封装",
        "天气查询 - wttr.in/Open-Meteo",
        "网页抓取 - 内容提取",
        "Obsidian - 笔记管理",
        "健康检查 - 安全加固"
      ]
    }
  ]

  return (
    <main className="container">
      <header>
        <h1>Useful Frameworks</h1>
        <p className="subtitle">好用的框架和工具集合，持续更新</p>
      </header>

      <div className="grid">
        {frameworks.map((fw, index) => (
          <div key={index} className="card">
            <h2>{fw.category}</h2>
            <p>{fw.description}</p>
            <ul>
              {fw.items.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <footer>
        <p>由 Nicole 维护 · 部署于 Vercel</p>
      </footer>
    </main>
  )
}
