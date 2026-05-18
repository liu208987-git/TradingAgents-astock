# A股多Agent投研工作台 V0.1

本仓库是基于 [TradingAgents-Astock](https://github.com/simonlin1212/TradingAgents-astock) 的增强版 fork，新增 stock-analysis 补充数据接入、quality_flags 数据质量防护和统一 HTML 报告流水线，整合了 [stock-analysis](https://github.com/mingli30119/stock-analysis) 的补充数据与 HTML 报告能力。

> 本项目仅供学习研究与技术演示，不构成任何投资建议。

---

## 核心能力

- **7 Agent 多空辩论**: 市场/情绪/新闻/基本面/政策/游资/解禁 → 质量门控 → 牛熊辩论 → 风控 → 最终决策
- **补充数据接入**: 从 stock-analysis 拉取 11 个补充数据 blocks（股本/股东/主营/分红/融资融券/业绩预告等）
- **数据质量防护**: suspect(可疑)/stale(过旧)/empty(为空) 三级标记 + Agent prompt 强制降权
- **统一 HTML 报告**: 10 步完整报告含 K 线图/ECharts/Agent 分析/补充数据/质量提示
- **一键命令**: `python scripts/run_full_report.py 600519 --name 贵州茅台`
- **5 股回归通过**: 茅台/宁德/比亚迪/平安/中芯国际

---

## 依赖项目

本项目运行时主要依赖 stock-analysis；a-stock-data 作为数据源参考项目，核心能力已由 TradingAgents-Astock 桥接。

| 项目 | 路径 | 用途 |
|------|------|------|
| [stock-analysis](https://github.com/mingli30119/stock-analysis) | `../stock-analysis/` | 补充数据采集 + HTML 渲染 |
| [a-stock-data](https://github.com/simonlin1212/a-stock-data) | `../a-stock-data/` | 数据源参考（核心能力已桥接） |

```bash
git clone https://github.com/mingli30119/stock-analysis.git
git clone https://github.com/simonlin1212/a-stock-data.git
cd stock-analysis && pip install akshare pandas numpy
```

---

## 快速开始

### 1. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY=sk-你的key
```

### 2. 采集补充数据（免费，约 2 分钟）

```bash
pip install akshare pandas numpy   # stock-analysis 依赖
python scripts/run_stock_analysis_snapshot.py 600519
```

### 3. 运行 Agent 分析（需要 LLM API，约 3-5 分钟）

```bash
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
tradingagents-web

# Linux/macOS
source .venv/bin/activate
tradingagents-web
```
浏览器打开 http://localhost:8501，输入股票代码开始分析。

### 4. 生成统一 HTML 报告

```bash
# 已有分析结果 → 跳过数据采集
python scripts/run_full_report.py 600519 --name 贵州茅台 --skip-snapshot

# 完整流程（含采集）
python scripts/run_full_report.py 300750 --name 宁德时代

# 自动找最新日志
python scripts/render_unified_html.py 600519 --name 贵州茅台 --auto-latest

# 回归测试
python scripts/test_unified_pipeline.py
```

### 输出文件

```
output/
├── supplement/     # 补充数据 JSON + quality_flags
├── unified/        # 统一 MD + JSON
└── reports/        # 最终 HTML 报告
```

TradingAgents 分析结果: `~/.tradingagents/logs/{code}/TradingAgentsStrategy_logs/`

---

## 整合层文件

| 文件 | 作用 |
|------|------|
| `scripts/run_stock_analysis_snapshot.py` | stock-analysis 数据采集 + 提取 |
| `tradingagents/dataflows/supplemental_stock_analysis.py` | 中文摘要 + quality_flags |
| `scripts/render_unified_html.py` | 统一 HTML 报告生成 |
| `scripts/run_full_report.py` | 总控脚本（一条命令） |
| `scripts/test_unified_pipeline.py` | 5 股回归测试 |

### Agent 层修改

| 文件 | 改动 |
|------|------|
| `tradingagents/agents/utils/agent_utils.py` | 新增 `@tool get_supplemental_data` |
| `tradingagents/graph/trading_graph.py` | fundamentals/lockup ToolNode 接入 |
| `tradingagents/agents/analysts/fundamentals_analyst.py` | 工具 + prompt + 质量约束 |
| `tradingagents/agents/analysts/lockup_watcher.py` | 工具 + prompt + 质量约束 |

---

## 全链路

```
stock-analysis 采集 → supplement JSON + quality_flags
  → get_supplemental_data (@tool)
    → fundamentals/lockup Agent 调用
      → suspect/stale 质量降权
        → full_states_log
          → render_unified_html.py
            → unified HTML (Step 0-9, 61-87KB)
```

---

## 配置

`config/unified_pipeline.yaml` — 路径、质量参数、测试列表。首次使用从 example 复制：

```bash
cp config/unified_pipeline.example.yaml config/unified_pipeline.yaml
```

---

## 许可证

本项目基于 [Apache License 2.0](LICENSE)。

整合的第三方项目：
- **TradingAgents-Astock** — Apache 2.0 (c) simonlin1212
- **stock-analysis** — MIT (c) mingli30119
- **a-stock-data** — Apache 2.0 (c) simonlin1212
- **上游 TradingAgents** — Apache 2.0 (c) TauricResearch

详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

---

## 免责声明

本项目仅用于学习、研究与数据分析流程演示，不构成任何投资建议。所有数据来自第三方公开接口，可能延迟、缺失或错误。使用者应自行核验数据并承担投资决策后果。
