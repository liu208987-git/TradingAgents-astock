"""
Stage 3: 统一 HTML 报告生成器

读取 TradingAgents 分析结果 + stock-analysis 补充数据 → 生成综合 HTML 报告。
第一版：手动指定输入文件，命令行运行。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Windows GBK 终端兼容
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# ── 路径配置 ────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
STOCK_ANALYSIS_DIR = ROOT.parent / "stock-analysis"
STOCK_ANALYSIS_SRC = STOCK_ANALYSIS_DIR / "src"
sys.path.insert(0, str(STOCK_ANALYSIS_SRC))

OUTPUT_DIR = ROOT / "output"
UNIFIED_DIR = OUTPUT_DIR / "unified"
REPORTS_DIR = OUTPUT_DIR / "reports"

# ── 报告章节模板 ────────────────────────────────────────────────────

_REPORT_SECTIONS = [
    ("market_report", "## Step 1: 市场技术分析"),
    ("sentiment_report", "## Step 2: 市场情绪分析"),
    ("news_report", "## Step 3: 新闻舆情分析"),
    ("fundamentals_report", "## Step 4: 基本面分析"),
    ("policy_report", "## Step 5: 政策分析"),
    ("hot_money_report", "## Step 6: 游资与资金信号"),
    ("lockup_report", "## Step 7: 解禁与股权结构"),
]


def build_unified_md(ta_data: dict, sa_blocks: dict, code: str, name: str) -> str:
    """生成综合 Markdown 报告."""
    lines = [
        f"# {code} {name} 多Agent综合研究报告",
        "",
        f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> 交易日期：{ta_data.get('trade_date', '')}",
        "",
        "---",
        "",
        "## Step 0: 最终决策",
        "",
        ta_data.get("final_trade_decision", ""),
        "",
        "---",
        "",
    ]

    # 7 个 Agent 报告
    for key, title in _REPORT_SECTIONS:
        content = ta_data.get(key, "")
        if content:
            lines.append(title)
            lines.append("")
            # 截断过长的单行（保留表格和列表）
            lines.append(content[:3000] if len(content) > 3000 else content)
            lines.append("")
            lines.append("---")
            lines.append("")

    # 辩论与风控
    debate = ta_data.get("investment_debate_state", {})
    if debate:
        lines.append("## Step 8: 多空辩论与风险评估")
        lines.append("")
        judge = debate.get("judge_decision", "")
        if judge:
            lines.append(str(judge)[:2000])
        risk = ta_data.get("risk_debate_state", {})
        if risk:
            risk_judge = risk.get("judge_decision", "")
            if risk_judge:
                lines.append("")
                lines.append(str(risk_judge)[:2000])
        lines.append("")
        lines.append("---")
        lines.append("")

    # 补充数据摘要（从 SA blocks 生成简要版）
    lines.append("## Step 9: stock-analysis 补充数据")
    lines.append("")

    # 主营构成
    zygc = sa_blocks.get("zygc", [])
    if zygc:
        lines.append("### 主营业务构成")
        sorted_items = sorted(
            zygc,
            key=lambda x: float(str(x.get("主营收入", 0)).replace(",", "") or 0),
            reverse=True,
        )[:5]
        for r in sorted_items:
            cat = r.get("分类类型", "")
            name_item = r.get("主营构成", "")
            revenue = r.get("主营收入", "")
            ratio = r.get("收入比例", "")
            lines.append(f"- [{cat}] {name_item}: {revenue} ({ratio})")
        lines.append("")

    # 十大股东
    top10 = sa_blocks.get("top10", [])
    if top10:
        lines.append("### 十大股东")
        for r in top10[:5]:
            lines.append(f"- {r.get('股东名称', '')}: {r.get('持股数', '')}股, {r.get('占总股本持股比例', '')}%")
        lines.append("")

    # 分红
    dividend = sa_blocks.get("dividend", [])
    if dividend:
        lines.append("### 近期分红")
        for r in dividend[:5]:
            lines.append(f"- {r.get('公告日期', '')}: 派息 {r.get('派息', '')}, [{r.get('进度', '')}]")
        lines.append("")

    # 业绩预告
    yjyg = sa_blocks.get("yjyg", [])
    if yjyg:
        lines.append("### 业绩预告")
        for r in yjyg[:3]:
            content = str(r.get("业绩变动", ""))[:200]
            lines.append(f"- [{r.get('预测指标', '')}] {content}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 数据质量提示")
    lines.append("")
    lines.append("本报告整合了 TradingAgents 多Agent 分析结果和 stock-analysis 补充数据。")
    lines.append("部分补充数据（融资融券、股东户数等）可能存在数据污染或过旧问题，已在分析中降权处理。")
    lines.append("")
    lines.append("> 本报告由 AI 自动生成，仅供学习研究，不构成投资建议。")

    return "\n".join(lines)


def build_unified_json(sa_raw: dict, code: str, name: str) -> dict:
    """生成 html_renderer 兼容的 JSON.

    原 SA JSON 只有 {"blocks": {...}}，缺少 code/name 顶层字段。
    basic_info 可能为空，从外部注入公司名。
    """
    blocks = sa_raw.get("blocks", {})

    # 如 basic_info 为空，注入最小版本供 html_renderer 使用
    if not blocks.get("basic_info"):
        blocks["basic_info"] = [
            {"item": "股票简称", "value": name},
            {"item": "股票代码", "value": code},
        ]

    # 注入分析日期
    blocks["_analysis_date"] = datetime.now().strftime("%Y-%m-%d")

    return {
        "code": code,
        "name": name,
        "blocks": blocks,
    }


def _find_latest_ta_log(code: str) -> Path | None:
    """自动查找最新的 TradingAgents full_states_log JSON."""
    log_dir = Path(f"C:/Users/liu/.tradingagents/logs/{code}/TradingAgentsStrategy_logs")
    if not log_dir.exists():
        return None
    logs = sorted(log_dir.glob("full_states_log_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return logs[0] if logs else None


def _find_sa_json(code: str) -> Path | None:
    """自动查找 stock-analysis data JSON."""
    path = Path(f"C:/Users/liu/stock-analysis/output/data_{code}.json")
    return path if path.exists() else None


def main() -> None:
    parser = argparse.ArgumentParser(description="生成统一 HTML 研究报告")
    parser.add_argument("code", help="6位股票代码，如 600519")
    parser.add_argument("--name", default="", help="股票名称，如 贵州茅台")
    parser.add_argument("--ta-result", default="", help="TradingAgents full_states_log JSON 路径")
    parser.add_argument("--sa-json", default="", help="stock-analysis data JSON 路径")
    parser.add_argument("--auto-latest", action="store_true", help="自动查找最新 TA 日志和 SA JSON")
    args = parser.parse_args()

    code = args.code.strip().zfill(6)
    name = args.name or code

    # 确定 TA 结果路径
    ta_path = Path(args.ta_result) if args.ta_result else None
    if args.auto_latest or not ta_path:
        auto_ta = _find_latest_ta_log(code)
        if auto_ta:
            ta_path = auto_ta
            print(f"[render] 自动找到 TA 日志: {ta_path}")
        elif not args.ta_result:
            print(f"[render] 错误: 未找到 {code} 的 TradingAgents 日志，请先运行分析")
            sys.exit(1)

    # 确定 SA JSON 路径
    sa_path = Path(args.sa_json) if args.sa_json else None
    if args.auto_latest or not sa_path:
        auto_sa = _find_sa_json(code)
        if auto_sa:
            sa_path = auto_sa
            print(f"[render] 自动找到 SA JSON: {sa_path}")
        elif not args.sa_json:
            print(f"[render] 错误: 未找到 {code} 的 stock-analysis JSON，请先运行 stock_full_report.py")
            sys.exit(1)

    # 读取输入
    print(f"[render] 读取 TA 结果: {ta_path}")
    with open(ta_path, encoding="utf-8") as f:
        ta_data = json.load(f)

    print(f"[render] 读取 SA 数据: {sa_path}")
    with open(sa_path, encoding="utf-8") as f:
        sa_raw = json.load(f)

    # 创建输出目录
    UNIFIED_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # 生成 MD
    md_content = build_unified_md(ta_data, sa_raw.get("blocks", {}), code, name)
    md_path = UNIFIED_DIR / f"{code}_unified.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"[render] MD 已生成: {md_path} ({len(md_content)} chars)")

    # 生成兼容 JSON
    unified_json = build_unified_json(sa_raw, code, name)
    json_path = UNIFIED_DIR / f"{code}_unified.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(unified_json, f, ensure_ascii=False, default=str)
    print(f"[render] JSON 已生成: {json_path}")

    # 调用 html_renderer 生成 HTML
    print("[render] 调用 html_renderer.generate_html ...")
    try:
        from html_renderer import generate_html  # noqa: E402
        html_path = generate_html(code, str(md_path), str(json_path))
        # generate_html 返回文件路径或写入到 stock-analysis 目录，
        # 复制到我们的 reports 目录
        if html_path and Path(html_path).exists():
            import shutil
            dest = REPORTS_DIR / f"{code}_unified.html"
            shutil.copy(html_path, dest)
            print(f"[render] HTML 已生成: {dest}")
        else:
            print("[render] HTML 生成可能失败，检查 stock-analysis/output/ 目录")
    except Exception as exc:
        print(f"[render] HTML 生成异常: {exc}")
        print("[render] MD 和 JSON 已正常生成，可手动调用 html_renderer")


if __name__ == "__main__":
    main()
