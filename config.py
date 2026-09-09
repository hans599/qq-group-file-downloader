"""读取 config.toml，向其他模块暴露配置变量。"""
import os
import tomllib

_BASE = os.path.dirname(os.path.abspath(__file__))
_TOML = os.path.join(_BASE, "config.toml")

if not os.path.exists(_TOML):
    raise SystemExit(
        "未找到 config.toml。请先复制示例配置并填入你的真实值：\n"
        "  cp config.example.toml config.toml\n"
        "（config.toml 含敏感信息，已被 .gitignore 忽略，不会提交到 git）"
    )

with open(_TOML, "rb") as f:
    _C = tomllib.load(f)

OB = _C.get("onebot", {})
WS_URL = OB.get("ws_url", "ws://127.0.0.1:3001/onebot/v11/ws")
ACCESS_TOKEN = OB.get("access_token", "")
GROUP_IDS = OB.get("group_ids", []) or []

LOG = _C.get("log", {})
LOG_FILE = LOG.get("file", os.path.join(_BASE, "monitor.log"))
LOG_LEVEL = LOG.get("level", "DEBUG")
