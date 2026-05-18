"""统一流水线配置加载器。先读 config/unified_pipeline.yaml，不存在则用默认值。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml  # noqa: F401


_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "unified_pipeline.yaml"

_DEFAULTS: dict[str, Any] = {
    "stock_analysis_dir": "C:/Users/liu/stock-analysis",
    "stock_analysis_python": "E:/python/python.exe",
    "tradingagents_logs_dir": "C:/Users/liu/.tradingagents/logs",
    "output_dir": "C:/Users/liu/TradingAgents-astock/output",
    "supplement_dir": "C:/Users/liu/TradingAgents-astock/output/supplement",
    "unified_dir": "C:/Users/liu/TradingAgents-astock/output/unified",
    "reports_dir": "C:/Users/liu/TradingAgents-astock/output/reports",
    "quality": {
        "margin_check_rows": 3,
        "stale_days": 730,
    },
    "test_stocks": [
        ("600519", "贵州茅台"),
        ("300750", "宁德时代"),
        ("002594", "比亚迪"),
        ("601318", "中国平安"),
        ("688981", "中芯国际"),
    ],
    "known_warnings": [
        "mootdx finance 'not enough values to unpack' — 自动降级",
        "akshare push2.eastmoney.com 代理超时 — 已降级",
        "deepseek-reasoner 不支持 tool_choice — free text 降级",
    ],
}

_cache: dict[str, Any] | None = None


def get_config() -> dict[str, Any]:
    """获取流水线配置（带缓存）。"""
    global _cache
    if _cache is not None:
        return _cache

    config = dict(_DEFAULTS)
    if _CONFIG_PATH.exists():
        try:
            with open(_CONFIG_PATH, encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f)
            if yaml_data and isinstance(yaml_data, dict):
                config.update(yaml_data)
        except Exception:
            pass  # 配置文件损坏时静默降级到默认值

    # 确保 test_stocks 是 tuple 列表
    stocks = config.get("test_stocks", [])
    if stocks and isinstance(stocks[0], dict):
        config["test_stocks"] = [(s["code"], s["name"]) for s in stocks]

    _cache = config
    return config
