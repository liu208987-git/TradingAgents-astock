"""统一流水线配置加载器。先读 config/unified_pipeline.yaml，不存在则用默认值。"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_CONFIG_PATH = _PROJECT_ROOT / "config" / "unified_pipeline.yaml"

_DEFAULTS: dict[str, Any] = {
    "stock_analysis_dir": str(_PROJECT_ROOT.parent / "stock-analysis"),
    "stock_analysis_python": sys.executable,
    "tradingagents_logs_dir": str(Path.home() / ".tradingagents" / "logs"),
    "output_dir": str(_PROJECT_ROOT / "output"),
    "supplement_dir": str(_PROJECT_ROOT / "output" / "supplement"),
    "unified_dir": str(_PROJECT_ROOT / "output" / "unified"),
    "reports_dir": str(_PROJECT_ROOT / "output" / "reports"),
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
        except Exception as exc:
            print(f"[config warning] 配置文件读取失败，使用默认配置: {exc}")

    # 解析 YAML 中的 ~ 和相对路径
    _path_keys = ("stock_analysis_dir", "tradingagents_logs_dir",
                  "output_dir", "supplement_dir", "unified_dir", "reports_dir")
    for key in _path_keys:
        val = config.get(key, "")
        if isinstance(val, str):
            if val.startswith("~/"):
                config[key] = str(Path.home() / val[2:])
            elif not Path(val).is_absolute():
                config[key] = str((_PROJECT_ROOT / val).resolve())
    # stock_analysis_python: 允许 "python" 等 PATH 命令名
    sap = config.get("stock_analysis_python", "")
    if isinstance(sap, str) and sap.startswith("~/"):
        config["stock_analysis_python"] = str(Path.home() / sap[2:])

    # 确保 test_stocks 是 tuple 列表
    stocks = config.get("test_stocks", [])
    if stocks and isinstance(stocks[0], dict):
        config["test_stocks"] = [(s["code"], s["name"]) for s in stocks]

    _cache = config
    return config
