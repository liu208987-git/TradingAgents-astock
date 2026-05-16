"""
Stage 3.6D: 回归测试脚本 — 验证 5 只股票已有产物，不重跑 LLM。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

TEST_STOCKS = [
    ("600519", "贵州茅台"),
    ("300750", "宁德时代"),
    ("002594", "比亚迪"),
    ("601318", "中国平安"),
    ("688981", "中芯国际"),
]

SUPPLEMENT_DIR = Path(r"C:\Users\liu\TradingAgents-astock\output\supplement")
UNIFIED_DIR = Path(r"C:\Users\liu\TradingAgents-astock\output\unified")
REPORTS_DIR = Path(r"C:\Users\liu\TradingAgents-astock\output\reports")
TA_LOG_BASE = Path(r"C:\Users\liu\.tradingagents\logs")
SA_DATA_DIR = Path(r"C:\Users\liu\stock-analysis\output")


def check(code: str, name: str) -> dict:
    r = {"code": code, "name": name}

    # 1. SA JSON
    sa = SA_DATA_DIR / f"data_{code}.json"
    r["sa_json"] = sa.exists()
    r["sa_size"] = sa.stat().st_size if sa.exists() else 0

    # 2. Supplement JSON
    supp = SUPPLEMENT_DIR / f"{code}_stock_analysis_blocks.json"
    r["supp"] = supp.exists()
    if supp.exists():
        with open(supp, encoding="utf-8") as f:
            d = json.load(f)
        bc = d.get("block_counts", {})
        r["supp_filled"] = sum(1 for v in bc.values() if v > 0)
        r["supp_total"] = len(bc)
        r["supp_quality"] = "quality_flags" in d
        r["supp_empty"] = d.get("empty_blocks", [])

    # 3. TA log
    log_dir = TA_LOG_BASE / code / "TradingAgentsStrategy_logs"
    if log_dir.exists():
        logs = sorted(log_dir.glob("full_states_log_*.json"))
        r["ta_log"] = len(logs) > 0
        r["ta_log_count"] = len(logs)
    else:
        r["ta_log"] = False
        r["ta_log_count"] = 0

    # 4. Unified MD
    md = UNIFIED_DIR / f"{code}_unified.md"
    r["md"] = md.exists()
    r["md_size"] = md.stat().st_size if md.exists() else 0

    # 5. Unified JSON
    uj = UNIFIED_DIR / f"{code}_unified.json"
    r["ujson"] = uj.exists()

    # 6. HTML
    html = REPORTS_DIR / f"{code}_unified.html"
    r["html"] = html.exists()
    r["html_size"] = html.stat().st_size if html.exists() else 0

    # 7. HTML content check (Step 0-9)
    if html.exists():
        with open(html, encoding="utf-8") as f:
            content = f.read()
        steps_found = []
        for i in range(10):
            if f"Step {i}" in content or f"step{i}" in content.lower():
                steps_found.append(i)
        r["html_steps"] = len(steps_found)
        r["html_steps_ok"] = r["html_steps"] >= 8

    return r


def main() -> None:
    print("=" * 60)
    print("统一投研流水线回归测试")
    print("=" * 60)
    print()

    all_ok = True
    for code, name in TEST_STOCKS:
        r = check(code, name)
        issues = []

        if not r["sa_json"]:
            issues.append("SA JSON 缺失")
        if not r["supp"]:
            issues.append("supplement JSON 缺失")
        if not r["ta_log"]:
            issues.append("TA 日志缺失")
        if not r["html"]:
            issues.append("HTML 缺失")
        elif r.get("html_steps_ok") is False:
            issues.append(f"HTML Step 区块不足 ({r.get('html_steps', 0)}/10)")

        status = "OK" if not issues else f"ISSUES: {', '.join(issues)}"
        if issues:
            all_ok = False

        print(f"[{status}] {code} {name}")
        print(f"  SA: {r['sa_size']//1024}KB | "
              f"Supp: {r.get('supp_filled', 0)}/{r.get('supp_total', 0)} | "
              f"TA logs: {r['ta_log_count']} | "
              f"HTML: {r['html_size']//1024}KB | "
              f"Steps: {r.get('html_steps', 0)}")
        if r.get("supp_empty"):
            print(f"  空 blocks: {r['supp_empty']}")
        if r.get("supp_quality"):
            print(f"  quality_flags: OK")
        if not r.get("supp_quality") and r["supp"]:
            print(f"  quality_flags: MISSING")

    print()
    print("=" * 60)
    print(f"结果: {'全部通过' if all_ok else '存在问题，见上'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
