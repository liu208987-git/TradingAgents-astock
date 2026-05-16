"""
Stage 1: 补充数据采集脚本
调用 stock-analysis 生成全量 JSON，提取 TradingAgents 缺失的 11 个 blocks。
"""
from __future__ import annotations

import json
import subprocess
import sys

# Windows GBK 终端兼容
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── 路径配置 ────────────────────────────────────────────────────────
STOCK_ANALYSIS_PYTHON = r"E:\python\python.exe"  # 系统 Python（stock-analysis 无独立 venv）
STOCK_ANALYSIS_DIR = Path(r"C:\Users\liu\stock-analysis")
STOCK_ANALYSIS_SCRIPT = STOCK_ANALYSIS_DIR / "stock_full_report.py"

OUTPUT_DIR = Path(r"C:\Users\liu\TradingAgents-astock\output\supplement")

TARGET_BLOCKS = [
    "share_structure",   # 股本结构变动
    "zygc",              # 主营业务构成
    "top10",             # 十大股东
    "top10_free",        # 十大流通股东
    "dividend",          # 历史分红
    "margin",            # 融资融券
    "fund_hold",         # 基金持仓（akshare 可能为空）
    "recommend",         # 机构推荐评级（东财接口可能为空）
    "yjyg",              # 业绩预告
    "yjkb",              # 业绩快报
    "gdhs",              # 股东户数变动
]

# ── 数据截断配置：每 block 最多保留行数 ────────────────────────────
MAX_ROWS = {
    "share_structure": 15,
    "zygc": 15,
    "top10": 10,
    "top10_free": 10,
    "dividend": 15,
    "margin": 15,
    "fund_hold": 20,
    "recommend": 20,
    "yjyg": 50,
    "yjkb": 50,
    "gdhs": 15,
}


def ensure_stock_analysis_json(code: str) -> Path | None:
    """确保 stock-analysis 的 data_{code}.json 存在。不存在则调脚本生成。"""
    json_path = STOCK_ANALYSIS_DIR / "output" / f"data_{code}.json"

    if json_path.exists():
        print(f"[snapshot] 复用已有 JSON: {json_path}")
        return json_path

    print(f"[snapshot] JSON 不存在，正在调用 stock_full_report.py {code} ...")
    result = subprocess.run(
        [STOCK_ANALYSIS_PYTHON, str(STOCK_ANALYSIS_SCRIPT), code],
        cwd=STOCK_ANALYSIS_DIR,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        print(f"[snapshot] 采集失败 (exit {result.returncode})")
        print(result.stderr[-800:])
        return None

    print("[snapshot] 采集完成")
    return json_path


def run_snapshot(code: str) -> dict | None:
    code = code.strip().zfill(6)

    json_path = ensure_stock_analysis_json(code)
    if json_path is None:
        return None

    with open(json_path, encoding="utf-8") as f:
        raw = json.load(f)

    all_blocks = raw.get("blocks", {})

    # 构建输出
    supplement_blocks: dict[str, list] = {}
    block_counts: dict[str, int] = {}
    empty_blocks: list[str] = []

    for key in TARGET_BLOCKS:
        items = all_blocks.get(key, [])
        if not isinstance(items, list):
            items = []
        count = len(items)
        block_counts[key] = count

        # 截断
        limit = MAX_ROWS.get(key, 15)
        trimmed = items[:limit] if count > limit else items

        supplement_blocks[key] = trimmed
        if count == 0:
            empty_blocks.append(key)

    # ── 数据质量检测 ────────────────────────────────────────────────
    quality_flags: dict[str, dict] = {}

    # margin: 检查是否为当前股票标的
    margin_items = supplement_blocks.get("margin", [])
    if margin_items:
        margin_suspect = True
        for r in margin_items[:3]:
            sc_code = str(r.get("标的证券代码", ""))
            if sc_code == code:
                margin_suspect = False
                break
        if margin_suspect:
            quality_flags["margin"] = {
                "status": "suspect",
                "reason": "标的证券代码非当前股票，疑似全市场ETF/非个股融资融券数据，不用于个股融资结论",
            }
    else:
        quality_flags["margin"] = {"status": "empty", "reason": "接口未返回数据"}

    # gdhs: 检查最新日期距今是否超过 2 年
    gdhs_items = supplement_blocks.get("gdhs", [])
    if gdhs_items:
        newest_date_str = gdhs_items[0].get("股东户数统计截止日", "")
        stale = True
        if newest_date_str:
            try:
                newest_date = datetime.fromisoformat(str(newest_date_str).replace("Z", "+00:00"))
                if datetime.now(timezone.utc) - newest_date < timedelta(days=730):
                    stale = False
            except (ValueError, TypeError):
                pass
        if stale:
            quality_flags["gdhs"] = {
                "status": "stale",
                "reason": f"最新数据日期 {newest_date_str} 距今超过2年，仅作历史参考",
            }
    else:
        quality_flags["gdhs"] = {"status": "empty", "reason": "接口未返回数据"}

    # 已记录为空的 blocks
    for key in empty_blocks:
        quality_flags[key] = {"status": "empty", "reason": "接口未返回数据"}

    output = {
        "code": code,
        "source": "stock-analysis",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "block_counts": block_counts,
        "empty_blocks": empty_blocks,
        "quality_flags": quality_flags,
        "blocks": supplement_blocks,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{code}_stock_analysis_blocks.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, default=str)

    filled = sum(1 for v in block_counts.values() if v > 0)
    flagged = [(k, v.get("status")) for k, v in quality_flags.items()
               if v.get("status") in ("suspect", "stale")]
    print(f"[snapshot] OK  {out_path}")
    print(f"[snapshot] {filled}/{len(TARGET_BLOCKS)} blocks 有数据, "
          f"空字段: {empty_blocks if empty_blocks else '无'}")
    if flagged:
        flag_str = ", ".join(f"{k}({s})" for k, s in flagged)
        print(f"[snapshot] 质量问题: {flag_str}")

    return output


def main() -> None:
    if len(sys.argv) > 1:
        code = sys.argv[1]
    else:
        code = "600519"
    run_snapshot(code)


if __name__ == "__main__":
    main()
