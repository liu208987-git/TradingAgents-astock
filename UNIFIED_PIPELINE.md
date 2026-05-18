# 统一 A 股投研流水线 V0.1

三项目整合：TradingAgents-Astock（主分析引擎）+ stock-analysis（补充数据+HTML报告）+ a-stock-data（数据源参考）

---

## 依赖项目

| 项目 | 路径 | 角色 |
|------|------|------|
| TradingAgents-Astock | `C:\Users\liu\TradingAgents-astock\` | 主项目，多 Agent 分析 + Web UI |
| stock-analysis | `C:\Users\liu\stock-analysis\` | 补充数据采集 + HTML 渲染 |
| a-stock-data | `C:\Users\liu\a-stock-data\` | 数据源参考（已被 TradingAgents 桥接） |

---

## 快速开始

### 前提条件

1. TradingAgents 已安装并可正常运行（`tradingagents-web` 可用）
2. stock-analysis 已克隆到本地，`stock_full_report.py` 可运行
3. DeepSeek API Key 已配置在 `.env`
4. 已在 `tradingagents-web` 中至少完成一次完整分析（生成 full_states_log）

### 一键生成 HTML 报告

```bash
cd C:\Users\liu\TradingAgents-astock
.venv\Scripts\activate

# 已有分析结果 → 跳过数据采集
python scripts/run_full_report.py 600519 --name 贵州茅台 --skip-snapshot

# 完整流程（含 stock-analysis 数据采集，约 2 分钟）
python scripts/run_full_report.py 300750 --name 宁德时代

# 快速回归测试（验证 5 只股票产物是否完整）
python scripts/test_unified_pipeline.py
```

### 单独使用各模块

```bash
# 仅采集补充数据
python scripts/run_stock_analysis_snapshot.py 600519

# 仅生成 HTML（自动找最新日志）
python scripts/render_unified_html.py 600519 --name 贵州茅台 --auto-latest

# 查看补充数据摘要
python -c "from tradingagents.dataflows.supplemental_stock_analysis import get_stock_analysis_supplement; print(get_stock_analysis_supplement('600519'))"
```

---

## 输出文件

| 文件 | 路径 | 说明 |
|------|------|------|
| supplement JSON | `output/supplement/{code}_stock_analysis_blocks.json` | 11 个补充 blocks + quality_flags |
| 统一 MD | `output/unified/{code}_unified.md` | Step 0-9 完整报告 |
| 统一 JSON | `output/unified/{code}_unified.json` | html_renderer 兼容格式 |
| 统一 HTML | `output/reports/{code}_unified.html` | 最终可视化报告（61-87KB） |

TradingAgents 分析结果：
```
C:\Users\liu\.tradingagents\logs\{code}\TradingAgentsStrategy_logs\full_states_log_{date}.json
```

---

## 全链路流程

```
stock-analysis 采集 (stock_full_report.py)
  → supplement JSON + quality_flags (run_stock_analysis_snapshot.py)
    → 中文摘要 (supplemental_stock_analysis.py)
      → get_supplemental_data 工具 (agent_utils.py)
        → fundamentals_analyst / lockup_watcher 调用
          → full_states_log (TradingAgents)
            → render_unified_html.py
              → unified HTML (Step 0-9)
```

---

## 已测试股票

| 代码 | 名称 | SA JSON | Supp | TA Log | HTML | Agent 调用 | 质量降权 |
|------|------|:------:|:----:|:------:|:----:|:---------:|:--------:|
| 600519 | 贵州茅台 | ✓ | 8/11 | ✓ | 76KB | ✓ | ✓ |
| 300750 | 宁德时代 | ✓ | 8/11 | ✓ | 78KB | ✓ | ✓ |
| 002594 | 比亚迪 | ✓ | 8/11 | ✓ | 81KB | ✓ | ✓ |
| 601318 | 中国平安 | ✓ | 7/11 | ✓ | 87KB | ✓ | ✓ |
| 688981 | 中芯国际 | ✓ | 8/11 | ✓ | 75KB | ✓ | ✓ |

---

## 数据质量防护

- `margin`（融资融券）：检测标的证券代码是否匹配，不匹配 → `suspect`，降权处理
- `gdhs`（股东户数）：检测最新日期是否过期 >2 年 → `stale`，仅历史参考
- `fund_hold`/`recommend`/`yjkb`：采集失败 → `empty`，跳过不编造
- Agent prompt 内置质量约束，不得根据 suspect/stale 数据做强结论

---

## 已知 Warning

| # | 问题 | 频率 | 影响 |
|---|------|------|------|
| 1 | mootdx finance "not enough values to unpack" | 5/5 | 自动降级 |
| 2 | akshare push2.eastmoney.com 代理超时 | 5/5 | 有降级 |
| 3 | deepseek-reasoner 不支持 tool_choice | 4/5 | free text 降级 |

这些 warning 不影响最终报告生成。

---

## 配置文件

`config/unified_pipeline.yaml` — 路径、质量参数、测试股票列表

---

## 整合层文件清单（5 个新增）

| 文件 | 作用 |
|------|------|
| `scripts/run_stock_analysis_snapshot.py` | 调 stock-analysis 采集 + 提取补充 blocks |
| `tradingagents/dataflows/supplemental_stock_analysis.py` | 中文摘要生成 + quality_flags |
| `scripts/render_unified_html.py` | 统一 HTML 报告生成器（含 --auto-latest） |
| `scripts/run_full_report.py` | 总控脚本（一键 snapshot → HTML） |
| `scripts/test_unified_pipeline.py` | 5 股回归测试 |

## Agent 层修改（4 个文件）

| 文件 | 改动 |
|------|------|
| `tradingagents/agents/utils/agent_utils.py` | 新增 `@tool get_supplemental_data` |
| `tradingagents/graph/trading_graph.py` | fundamentals/lockup ToolNode 接入 |
| `tradingagents/agents/analysts/fundamentals_analyst.py` | import + tools + prompt + 质量约束 |
| `tradingagents/agents/analysts/lockup_watcher.py` | import + tools + prompt + 质量约束 |

---

## 版本

- **V0.1** — 2026-05-16
- Git tag: `v0.1-unified-pipeline`
- 5 只股票 + 5 层整合 + 全链路验证通过
