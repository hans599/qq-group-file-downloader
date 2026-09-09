"""QQ 群文件监控（精简版，loguru，无 Web / 无 DB）。

两个功能：
  python monitor.py          # 常驻监听：仅记录 [已连接]/[监控群]/[其他事件] 等基本信息
  python monitor.py scan     # 扫描各监控群的全部文件，并逐个给出可下载直链

依赖：NapCatQQ（OneBot 11 正向 WebSocket）+ Python + loguru + websockets。
（已精简：不再监控下载次数、谁下载、不再自动取链——取链统一由 scan 命令完成。）
"""
import argparse
import asyncio
import inspect
import json
import sys
import time
import urllib.parse

import websockets
from loguru import logger

from config import (WS_URL, ACCESS_TOKEN, GROUP_IDS, LOG_FILE, LOG_LEVEL)


# ---------- 工具 ----------
def _header_kw() -> str:
    """websockets 11+ 用 additional_headers，老版本用 extra_headers。自动兼容。"""
    sig = inspect.signature(websockets.connect)
    return "additional_headers" if "additional_headers" in sig.parameters else "extra_headers"


def _connect_kwargs(headers: dict) -> dict:
    return {_header_kw(): headers, "ping_interval": 20, "ping_timeout": 20}


def _with_fname(url: str, name: str) -> str:
    """NapCat 返回的直链 fname= 常为空，补上群文件名（URL 编码）以便下载保存正确文件名。"""
    if not name:
        return url
    p = urllib.parse.urlparse(url)
    q = urllib.parse.parse_qs(p.query)
    if not q.get("fname", [""])[0]:
        q["fname"] = [name]
        p = p._replace(query=urllib.parse.urlencode(q, doseq=True, quote_via=urllib.parse.quote))
    return p.geturl()


def _fmt_size(n) -> str:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return "-"
    if n < 1024:
        return f"{n} B"
    if n < 1024 ** 2:
        return f"{n / 1024:.1f} KB"
    if n < 1024 ** 3:
        return f"{n / 1024 ** 2:.1f} MB"
    return f"{n / 1024 ** 3:.2f} GB"


def _fmt_time(ts) -> str:
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(ts)))
    except (TypeError, ValueError):
        return "-"


# ---------- loguru 配置 ----------
def setup_logger():
    logger.remove()
    # 文件：完整时间戳 + 级别，含全部事件（含心跳）
    logger.add(
        LOG_FILE,
        level=LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        encoding="utf-8",
        rotation="10 MB",
        retention=5,
    )
    # 控制台：干净格式，仅 INFO 及以上（心跳不刷屏）
    logger.add(
        sys.stderr,
        level="INFO",
        format="{message}",
        colorize=False,
    )


# ---------- OneBot 客户端（精简：仅连接 + 扫描取链） ----------
class OneBotMonitor:
    def __init__(self):
        self.ws = None
        self._echo = 0
        self._pending = {}
        self._stop = False

    # ---- 底层 API ----
    async def call_api(self, action, params, timeout=20):
        if self.ws is None:
            raise RuntimeError("OneBot 未连接")
        self._echo += 1
        echo = f"api-{self._echo}"
        fut = asyncio.get_running_loop().create_future()
        self._pending[echo] = fut
        await self.ws.send(json.dumps({"action": action, "params": params, "echo": echo}))
        try:
            resp = await asyncio.wait_for(fut, timeout=timeout)
        finally:
            self._pending.pop(echo, None)
        if resp.get("status") not in (None, "ok") or resp.get("retcode", 0) != 0:
            raise RuntimeError(f"API {action} 返回异常: {resp}")
        return resp

    async def get_group_file_url(self, file_id, group_id, busid):
        """实时取最新直链。优先 get_group_file_url（需 busid），失败再用 get_file（仅需 file_id）。"""
        try:
            resp = await self.call_api(
                "get_group_file_url",
                {"group_id": group_id, "file_id": file_id, "busid": busid},
            )
            url = (resp.get("data") or {}).get("url")
            if url:
                return url
        except Exception as e:  # noqa
            logger.warning("get_group_file_url 失败，尝试 get_file: {}", e)
        try:
            resp = await self.call_api("get_file", {"file_id": file_id})
            return (resp.get("data") or {}).get("url")
        except Exception as e:  # noqa
            logger.warning("get_file 也失败: {}", e)
            return None

    async def scan_group_files(self, group_id, folder_id="/", parent=""):
        """递归枚举群文件，返回扁平化的文件列表（含 download_times）。"""
        try:
            if folder_id == "/":
                resp = await self.call_api("get_group_root_files", {"group_id": group_id})
            else:
                resp = await self.call_api(
                    "get_group_files_by_folder",
                    {"group_id": group_id, "folder_id": folder_id},
                )
        except Exception as e:  # noqa
            logger.warning("扫描群文件失败 gid={} folder={}: {}", group_id, folder_id, e)
            return []
        data = resp.get("data") or {}
        out = []
        for f in data.get("files", []):
            out.append({
                "file_id": f.get("file_id"),
                "name": f.get("file_name"),
                "size": f.get("file_size", 0),
                "busid": f.get("busid"),
                "upload_time": f.get("upload_time"),
                "uploader": (f.get("uploader_name") or str(f.get("uploader_uin", "")) or "未知"),
                "download_times": f.get("download_times"),
                "folder": parent,
            })
        for fol in data.get("folders", []):
            fid = fol.get("folder_id")
            if fid:
                fol_name = fol.get("folder_name") or ""
                sub = f"{parent}/{fol_name}" if parent else fol_name
                out += await self.scan_group_files(group_id, fid, sub)
        return out

    # ---- 事件处理（精简：仅记录连接/生命周期/心跳） ----
    async def _handle(self, raw):
        try:
            m = json.loads(raw)
        except json.JSONDecodeError:
            return
        if "echo" in m and m["echo"] in self._pending:
            fut = self._pending[m["echo"]]
            if not fut.done():
                fut.set_result(m)
            return
        if m.get("post_type") != "meta_event":
            return
        if m.get("meta_event_type") == "heartbeat":
            logger.debug("[其他事件] meta_event/heartbeat")   # 心跳：仅写文件
        elif m.get("meta_event_type") == "lifecycle":
            logger.info("[其他事件] meta_event/lifecycle")

    async def _run(self):
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"} if ACCESS_TOKEN else {}
        kwargs = _connect_kwargs(headers)
        while not self._stop:
            try:
                logger.info("[连接中] {}", WS_URL)
                async with websockets.connect(WS_URL, **kwargs) as ws:
                    self.ws = ws
                    logger.info("[已连接] {}", WS_URL)
                    async for raw in ws:
                        await self._handle(raw)
            except Exception as e:  # noqa
                logger.warning("OneBot 连接异常: {}", e)
            finally:
                self.ws = None
            if self._stop:
                break
            await asyncio.sleep(5)  # 重连退避


# ---------- 文件查询 + 取链（scan） ----------
async def scan_cli():
    """扫描各监控群的完整文件列表，并为每个文件取回下载直链。"""
    monitor = OneBotMonitor()
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"} if ACCESS_TOKEN else {}
    kwargs = _connect_kwargs(headers)

    async def _recv():
        async for raw in ws:
            try:
                m = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if "echo" in m and m["echo"] in monitor._pending:
                fut = monitor._pending[m["echo"]]
                if not fut.done():
                    fut.set_result(m)

    async with websockets.connect(WS_URL, **kwargs) as ws:
        monitor.ws = ws
        recv_task = asyncio.create_task(_recv())

        groups = GROUP_IDS or []
        if not groups:
            logger.warning("config 中未配置 group_ids，无法扫描。")
            recv_task.cancel()
            return

        for gid in groups:
            try:
                info = await monitor.call_api("get_group_file_system_info", {"group_id": gid})
                d = info.get("data") or {}
                logger.info("[文件系统] 群={} 总文件数={} 已用容量={} 总容量={}",
                            gid, d.get("file_count"), _fmt_size(d.get("used_space")),
                            _fmt_size(d.get("total_space")))
            except Exception as e:  # noqa
                logger.warning("获取群 {} 文件系统信息失败: {}", gid, e)

            files = await monitor.scan_group_files(gid)
            logger.info("[扫描] 群={} 共 {} 个文件", gid, len(files))
            sep = "-" * 64
            if not files:
                logger.info("（该群暂无文件）")
            for idx, f in enumerate(files, 1):
                url = None
                try:
                    url = await monitor.get_group_file_url(f["file_id"], gid, f["busid"])
                    if url:
                        url = _with_fname(url, f["name"])
                except Exception as e:  # noqa
                    logger.debug("取直链失败 file_id={}: {}", f["file_id"], e)
                logger.info(sep)
                logger.info("[{}/{}] 文件名: {}", idx, len(files), f["name"])
                logger.info("  上传者: {} | 大小: {} | 上传时间: {} | 下载次数: {}",
                            f["uploader"], _fmt_size(f["size"]),
                            _fmt_time(f["upload_time"]), f["download_times"])
                logger.info("  文件夹: {} | file_id: {}",
                            f["folder"] or "(根目录)", f["file_id"])
                logger.info("  直链: {}",
                            url or "（取链失败：文件可能已失效 / NapCat 未缓存）")
            if files:
                logger.info(sep)
        recv_task.cancel()


# ---------- 入口 ----------
async def main_watch():
    setup_logger()
    logger.info("[监控群] {}", GROUP_IDS or "全部")
    logger.info("等待事件…（在群里发消息 / 传文件）Ctrl+C 退出")
    monitor = OneBotMonitor()
    await monitor._run()


def main():
    parser = argparse.ArgumentParser(description="QQ 群文件监控（精简版）")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("scan", help="扫描并打印各监控群的完整文件列表（含下载直链）")
    args = parser.parse_args()

    if args.cmd == "scan":
        setup_logger()
        try:
            asyncio.run(scan_cli())
        except KeyboardInterrupt:
            pass
        except Exception as e:  # noqa
            logger.error("❌ 无法连接 NapCat（{}）：{}", WS_URL, e)
            logger.error("   请检查：NapCat 是否已启动、OneBot 11 WS 地址/token 是否与 config.toml 一致。")
    else:
        try:
            asyncio.run(main_watch())
        except KeyboardInterrupt:
            logger.info("\n已退出")


if __name__ == "__main__":
    main()
