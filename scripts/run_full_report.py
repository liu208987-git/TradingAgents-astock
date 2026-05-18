"""
Stage 3.6: 总控脚本 — 一站式生成统一 HTML 报告

流程: snapshot → 找 TA 日志 → render HTML
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_SCRIPT = ROOT / "scripts" / "run_stock_analysis_snapshot.py"
RENDER_SCRIPT = ROOT / "scripts" / "render_unified_html.py"

# ── 已知问题 warning 模板 ──────────────────────────────────────────
KNOWN_WARNINGS = [
    ("mootdx_finance_unpack", "mootdx finance 'not enough values to unpack' — 自动降级，不影响分析"),
    ("akshare_push2_proxy", "akshare push2.eastmoney.com 代理超时/ConnectionResetError — 已降级"),
    ("deepseek_structured_output", "deepseek-reasoner 不支持 tool_choice — structured output 降级 free text"),
]


def run_step(step: int, total: int, label: str, cmd: list[str], cwd: Path | None = None) -> bool:
    """运行一个步骤，返回是否成功."""
    print(f"[{step}/{total}] {label} ...")
    result = subprocess.run(
        cmd, cwd=cwd or ROOT,
        capture_output=True, text=True, timeout=300,
        encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        print(f"  失败 (exit {result.returncode})")
        if result.stderr:
            stderr_tail = result.stderr.strip()[-500:]
            if stderr_tail:
                print(f"  stderr: {stderr_tail}")
        return False
    # 打印最后几行输出
    stdout = result.stdout or ""
    stdout_lines = stdout.strip().split("\n")
    for line in stdout_lines[-3:]:
        if line.strip():
            print(f"  {line.strip()}")
    return True


def find_latest_ta_log(code: str) -> Path | None:
    """自动查找最新的 TradingAgents full_states_log."""
    try:
        from tradingagents.dataflows.pipeline_config import get_config
        log_dir = Path(get_config()["tradingagents_logs_dir"]) / code / "TradingAgentsStrategy_logs"
    except Exception:
        log_dir = Path.home() / ".tradingagents" / "logs" / code / "TradingAgentsStrategy_logs"
    if not log_dir.exists():
        return None
    logs = sorted(log_dir.glob("full_states_log_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return logs[0] if logs else None


def get_html_path(code: str) -> Path:
    return ROOT / "output" / "reports" / f"{code}_unified.html"


def main() -> None:
    parser = argparse.ArgumentParser(description="一站式生成统一 HTML 研究报告")
    parser.add_argument("code", help="6位股票代码")
    parser.add_argument("--name", default="", help="股票名称")
    parser.add_argument("--skip-snapshot", action="store_true", help="跳过 stock-analysis 数据采集")
    parser.add_argument("--ta-result", default="", help="手动指定 TA 日志路径")
    args = parser.parse_args()

    code = args.code.strip().zfill(6)
    name = args.name or code
    warnings: list[str] = []

    total_steps = 2 if args.skip_snapshot else 3
    current = 0

    # Step 1: Snapshot
    if not args.skip_snapshot:
        current += 1
        ok = run_step(current, total_steps, "更新 supplement 数据",
                      [sys.executable, str(SNAPSHOT_SCRIPT), code])
        if not ok:
            print("[warning] snapshot 部分失败，继续尝试生成报告")
            warnings.append(KNOWN_WARNINGS[1][1])  # akshare 相关
    else:
        print("[skip] 跳过 snapshot")

    # Step 2: 找 TA 日志
    current += 1
    if args.ta_result:
        ta_path = Path(args.ta_result)
        print(f"[{current}/{total_steps}] 使用指定 TA 日志: {ta_path}")
    else:
        ta_path = find_latest_ta_log(code)
        if ta_path:
            print(f"[{current}/{total_steps}] 找到最新 TA 日志: {ta_path}")
        else:
            print(f"[{current}/{total_steps}] 错误: 未找到 {code} 的 TradingAgents 日志")
            print("  请先在 tradingagents-web 中运行完整分析")
            sys.exit(1)

    if not ta_path.exists():
        print(f"  错误: 日志文件不存在: {ta_path}")
        sys.exit(1)

    # Step 3: Render HTML
    current += 1
    try:
        from tradingagents.dataflows.pipeline_config import get_config
        sa_json = str(Path(get_config()["stock_analysis_dir"]) / "output" / f"data_{code}.json")
    except Exception:
        sa_json = str(ROOT.parent / "stock-analysis" / "output" / f"data_{code}.json")
    render_cmd = [
        sys.executable, str(RENDER_SCRIPT), code,
        "--name", name,
        "--ta-result", str(ta_path),
        "--sa-json", sa_json,
    ]
    ok = run_step(current, total_steps, "生成统一 HTML 报告", render_cmd)

    # 结果
    html_path = get_html_path(code)
    print()
    if ok and html_path.exists():
        print(f"完成! HTML: {html_path}")
        print(f"大小: {html_path.stat().st_size:,} bytes")
    else:
        print(f"HTML 生成可能失败，检查 output/reports/ 目录")
        print(f"MD/JSON 文件在 output/unified/ 目录")

    # 记录已知 warnings
    if warnings:
        print(f"\n已知 warning ({len(warnings)}):")
        for w in warnings:
            print(f"  - {w[:120]}")

    # 时间戳
    print(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
