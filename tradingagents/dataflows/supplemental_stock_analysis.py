"""
Stage 1: 补充数据摘要模块
读取 supplement JSON → 生成 LLM 可读的中文摘要（≤ 2000 token）。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# Windows GBK 终端兼容
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

SUPPLEMENT_DIR = Path(r"C:\Users\liu\TradingAgents-astock\output\supplement")
SNAPSHOT_SCRIPT = Path(r"C:\Users\liu\TradingAgents-astock\scripts\run_stock_analysis_snapshot.py")


def _ensure_supplement_json(ticker: str) -> Path | None:
    """确保补充 JSON 存在，不存在则调 snapshot 脚本生成。"""
    json_path = SUPPLEMENT_DIR / f"{ticker}_stock_analysis_blocks.json"
    if json_path.exists():
        return json_path

    print(f"[supplement] 补充 JSON 不存在，调用 snapshot 脚本生成...")
    result = subprocess.run(
        [sys.executable, str(SNAPSHOT_SCRIPT), ticker],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0 or not json_path.exists():
        print(f"[supplement] snapshot 失败: {result.stderr[-500:]}")
        return None
    return json_path


# ── 各 block 摘要函数（字段名基于 stock-analysis 实际输出）─────────

def _fmt_val(v) -> str:
    """安全格式化值，处理 None 和 float."""
    if v is None:
        return "-"
    if isinstance(v, float):
        if abs(v) >= 1e8:
            return f"{v/1e8:.1f}亿"
        if abs(v) >= 1e4:
            return f"{v/1e4:.0f}万"
        return f"{v:.2f}"
    return str(v)


def _summarize_share_structure(items: list) -> str:
    """股本结构变动摘要."""
    if not items:
        return ""
    lines = ["## 股本结构变动"]
    for r in items[:10]:
        date = r.get("变更日期", "")
        reason = r.get("变动原因", "")
        total = _fmt_val(r.get("总股本", ""))
        lines.append(f"- {date}: {reason}（总股本 {total}）")
    return "\n".join(lines)


def _summarize_zygc(items: list) -> str:
    """主营业务构成摘要."""
    if not items:
        return ""
    lines = ["## 主营业务构成"]
    sorted_items = sorted(
        items,
        key=lambda x: float(str(x.get("主营收入", 0)).replace(",", "") or 0),
        reverse=True,
    )
    seen = set()
    for r in sorted_items:
        cat = r.get("分类类型", "")
        name = r.get("主营构成", "")
        key = f"{cat}/{name}"
        if key in seen:
            continue
        seen.add(key)
        revenue = _fmt_val(r.get("主营收入", ""))
        ratio = r.get("收入比例", "")
        ratio_str = f"{float(ratio)*100:.1f}%" if ratio else ""
        lines.append(f"- [{cat}] {name}: 收入 {revenue}, 占比 {ratio_str}")
        if len(seen) >= 10:
            break
    return "\n".join(lines)


def _summarize_top10(items: list, label: str) -> str:
    """十大股东/流通股东摘要."""
    if not items:
        return ""
    lines = [f"## {label}"]
    for r in items[:10]:
        name = r.get("股东名称", "")
        shares = _fmt_val(r.get("持股数", ""))
        ratio = r.get("占总股本持股比例", r.get("持股比例", ""))
        ratio_str = f"{ratio}%" if ratio else ""
        change = r.get("增减", "")
        change_str = f" ({change})" if change else ""
        lines.append(f"- {name}: {shares}股, {ratio_str}{change_str}")
    return "\n".join(lines)


def _summarize_dividend(items: list) -> str:
    """历史分红摘要."""
    if not items:
        return ""
    lines = ["## 历史分红"]
    for r in items[:10]:
        date = r.get("公告日期", "")
        div = _fmt_val(r.get("派息", ""))
        sg = r.get("送股", 0)
        zz = r.get("转增", 0)
        status = r.get("进度", "")
        extra = f"送{sg}/转{zz}" if (sg or zz) else ""
        lines.append(f"- {date}: 派息 {div}, {extra} [{status}]")
    return "\n".join(lines)


def _summarize_margin(items: list, quality: dict | None = None) -> str:
    """融资融券摘要，取最近 10 条."""
    if not items:
        return ""
    is_suspect = quality and quality.get("status") == "suspect" if quality else False

    lines = ["## 融资融券（最近 10 个交易日）"]
    if is_suspect:
        lines.append("> 以下数据疑似全市场 ETF/非个股标的，仅供参考，不作为该股票融资趋势依据")

    recent = items[:10]
    for r in recent:
        date = r.get("信用交易日期", "")
        name = r.get("标的证券简称", "")
        rz_bal = _fmt_val(r.get("融资余额", ""))
        rq_qty = _fmt_val(r.get("融券余量", ""))
        lines.append(f"- {date} [{name}]: 融资余额 {rz_bal}, 融券余量 {rq_qty}")

    if not is_suspect and len(recent) >= 5:
        first_rz = recent[-1].get("融资余额", 0) or 0
        last_rz = recent[0].get("融资余额", 0) or 0
        try:
            if float(str(last_rz)) > float(str(first_rz)):
                lines.append("趋势：融资余额近 5 日增加")
            else:
                lines.append("趋势：融资余额近 5 日减少")
        except (ValueError, TypeError):
            pass
    return "\n".join(lines)


def _summarize_fund_hold(items: list) -> str:
    """基金持仓摘要."""
    if not items:
        return ""
    lines = ["## 基金持仓"]
    for r in items[:10]:
        fund = r.get("基金名称", r.get("name", ""))
        ratio = r.get("持股比例", r.get("ratio", ""))
        lines.append(f"- {fund}: {ratio}")
    return "\n".join(lines)


def _summarize_recommend(items: list) -> str:
    """机构推荐评级摘要."""
    if not items:
        return ""
    lines = ["## 机构推荐评级"]
    for r in items[:10]:
        org = r.get("机构", r.get("org", r.get("券商", "")))
        rating = r.get("评级", r.get("rating", ""))
        target = r.get("目标价", r.get("target", ""))
        lines.append(f"- {org}: {rating} (目标价 {target})" if target else f"- {org}: {rating}")
    return "\n".join(lines)


def _summarize_yjyg(items: list) -> str:
    """业绩预告摘要."""
    if not items:
        return ""
    lines = ["## 业绩预告"]
    for r in items[:10]:
        name = r.get("股票简称", "")
        indicator = r.get("预测指标", "")
        content = r.get("业绩变动", "")
        if isinstance(content, str) and len(content) > 200:
            content = content[:200] + "..."
        lines.append(f"- [{name}] {indicator}: {content}")
    return "\n".join(lines)


def _summarize_yjkb(items: list) -> str:
    """业绩快报摘要."""
    if not items:
        return ""
    lines = ["## 业绩快报"]
    for r in items[:10]:
        period = r.get("报告期", r.get("period", ""))
        revenue = r.get("营业收入", r.get("revenue", ""))
        profit = r.get("净利润", r.get("profit", ""))
        lines.append(f"- {period}: 营收 {revenue}, 净利 {profit}")
    return "\n".join(lines)


def _summarize_gdhs(items: list, quality: dict | None = None) -> str:
    """股东户数变动摘要."""
    if not items:
        return ""
    is_stale = quality and quality.get("status") == "stale" if quality else False

    lines = ["## 股东户数变动（最近 10 期）"]
    if is_stale:
        lines.append("> 数据较旧（最新日期距今超过2年），仅作历史参考，不代表当前筹码状态")

    for r in items[:10]:
        date = r.get("股东户数统计截止日", "")
        holders = _fmt_val(r.get("股东户数-本次", ""))
        change_pct = r.get("股东户数-增减比例", "")
        change_str = f"{change_pct:+.1f}%" if isinstance(change_pct, (int, float)) else f"{change_pct}"
        lines.append(f"- {date}: {holders}户 ({change_str})")

    if not is_stale and len(items) >= 3:
        first_h = items[-1].get("股东户数-本次", 0) or 0
        last_h = items[0].get("股东户数-本次", 0) or 0
        try:
            if float(str(last_h)) < float(str(first_h)):
                lines.append("趋势：股东户数减少（筹码集中）")
            else:
                lines.append("趋势：股东户数增加（筹码分散）")
        except (ValueError, TypeError):
            pass
    return "\n".join(lines)


# ── 主摘要函数 ──────────────────────────────────────────────────────

_SUMMARIZERS = {
    "share_structure": _summarize_share_structure,
    "zygc": _summarize_zygc,
    "top10": lambda items: _summarize_top10(items, "十大股东"),
    "top10_free": lambda items: _summarize_top10(items, "十大流通股东"),
    "dividend": _summarize_dividend,
    "margin": _summarize_margin,
    "fund_hold": _summarize_fund_hold,
    "recommend": _summarize_recommend,
    "yjyg": _summarize_yjyg,
    "yjkb": _summarize_yjkb,
    "gdhs": _summarize_gdhs,
}


def get_stock_analysis_supplement(ticker: str) -> str:
    """获取补充数据的中文摘要，适合 LLM 上下文消费。

    Args:
        ticker: 6 位股票代码，如 '600519'

    Returns:
        中文摘要字符串，≤ 2000 token
    """
    ticker = ticker.strip().zfill(6)

    json_path = _ensure_supplement_json(ticker)
    if json_path is None:
        return f"[补充数据] {ticker} 补充数据暂不可用（采集失败）"

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    blocks: dict = data.get("blocks", {})
    empty_blocks: list = data.get("empty_blocks", [])
    quality_flags: dict = data.get("quality_flags", {})

    sections: list[str] = []
    sections.append(f"# {ticker} 补充数据摘要\n")

    # margin 和 gdhs 需要传入 quality 信息
    _QUALITY_KEYS = {"margin", "gdhs"}

    for key in _SUMMARIZERS:
        items = blocks.get(key, [])
        if not items:
            continue  # 空 block 跳过
        try:
            qf = quality_flags.get(key) if key in _QUALITY_KEYS else None
            summary = _SUMMARIZERS[key](items, qf) if qf else _SUMMARIZERS[key](items)
            if summary:
                sections.append(summary)
                sections.append("")
        except Exception as exc:
            sections.append(f"[{key} 摘要生成异常: {exc}]")

    # ── 数据质量提示 ────────────────────────────────────────────────
    suspect_keys = [k for k, v in quality_flags.items() if v.get("status") == "suspect"]
    stale_keys = [k for k, v in quality_flags.items() if v.get("status") == "stale"]
    empty_keys = [k for k, v in quality_flags.items() if v.get("status") == "empty"]

    if suspect_keys or stale_keys or empty_keys:
        sections.append("## 数据质量提示")
        for k in suspect_keys:
            sections.append(f"- **{k}** 标记为可疑：{quality_flags[k].get('reason', '')}")
        for k in stale_keys:
            sections.append(f"- **{k}** 标记为过旧：{quality_flags[k].get('reason', '')}")
        for k in empty_keys:
            sections.append(f"- **{k}** 为空：接口未返回数据")
        sections.append("")
        sections.append("分析时请注意：标记为可疑(suspect)或过旧(stale)的数据"
                        "必须降权处理，不得作为强结论依据。")

    return "\n".join(sections)


# ── CLI 测试入口 ─────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) > 1:
        code = sys.argv[1]
    else:
        code = "600519"
    summary = get_stock_analysis_supplement(code)
    print(summary)
    print(f"\n---\n预估 token 数: {len(summary) // 2} ~ {len(summary) // 3}")


if __name__ == "__main__":
    main()
