# Third-Party Notices

This project integrates and depends on the following open-source projects.

---

## TradingAgents-Astock

- **Repository:** https://github.com/simonlin1212/TradingAgents-astock
- **License:** Apache License 2.0
- **Author:** simonlin1212
- **Role in this project:** Multi-agent analysis engine, Web UI, A-stock data vendor layer
- **Modifications made:**
  - `web/app.py` — Default LLM provider changed to DeepSeek
  - `web/pdf_export.py` — Added Windows CJK font paths
  - `web/components/report_viewer.py` — PDF export graceful fallback
  - `tradingagents/agents/utils/agent_utils.py` — Added `get_supplemental_data` tool
  - `tradingagents/graph/trading_graph.py` — Added supplement tool to ToolNodes
  - `tradingagents/agents/analysts/fundamentals_analyst.py` — Supplement tool + quality constraints in prompt
  - `tradingagents/agents/analysts/lockup_watcher.py` — Supplement tool + quality constraints in prompt

---

## stock-analysis

- **Repository:** https://github.com/mingli30119/stock-analysis
- **License:** MIT License
- **Author:** mingli30119
- **Role in this project:** Supplemental data blocks, HTML report renderer (`html_renderer.py`)
- **Modifications made:** None (used as-is via subprocess and `sys.path` import)

---

## a-stock-data

- **Repository:** https://github.com/simonlin1212/a-stock-data
- **License:** Apache License 2.0
- **Author:** simonlin1212
- **Role in this project:** Data source reference (core capabilities already bridged into TradingAgents-Astock's `tradingagents/dataflows/a_stock.py`)
- **Modifications made:** None (used as reference only)

---

## Upstream TradingAgents

- **Repository:** https://github.com/TauricResearch/TradingAgents
- **License:** Apache License 2.0
- **Role:** Original multi-agent trading framework that TradingAgents-Astock is forked from

---

## Data Sources

This project retrieves A-share market data from the following public/free sources:

| Source | Type | Notes |
|--------|------|-------|
| mootdx | TCP (port 7709) | K-line, order book, financial snapshots |
| akshare | Python library | Financial statements, news, reports, industry data |
| Tencent Finance | HTTP | PE/PB, market cap, turnover, limit prices |
| East Money | HTTP | Research reports, stock news |
| Sina Finance | HTTP | Daily K-line, minute data |
| Tonghuashun (10jqka) | HTTP | Hot stock topics, northbound capital flow |
| Baidu Stock | HTTP | Concept sector attribution, fund flow |
| CNINFO | HTTP (via akshare) | Full-text announcements |

All data sources are free and do not require API keys (except iwencai for NL report search, which is optional and not used in the current pipeline).

---

## Disclaimer

This project is for educational and research purposes only. It does not constitute investment advice. All data comes from third-party public interfaces and may be delayed, missing, or erroneous. Users should independently verify data and bear all consequences of investment decisions.
