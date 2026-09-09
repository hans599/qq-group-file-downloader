# QQ 群文件监控 · 取链工具

> 基于 **NapCatQQ（OneBot 11）+ Python + loguru** 的轻量工具：扫描指定 QQ 群的群文件，并逐个给出可下载直链，方便用 NDM 等工具高速下载。**无网页、无数据库。**

## 特性
- `monitor.py` —— 常驻监听，仅记录连接 / 生命周期 / 心跳等基本信息
- `monitor.py scan` —— 一次性扫描群内全部文件，并逐个输出可下载直链
- 日志写入 `monitor.log`（loguru），心跳默认仅落盘

---

## 一、准备（只需一次）

官方资源：
- 下载（Shell 版）：https://github.com/NapNeko/NapCatQQ/releases
- 文档：https://napneko.github.io/guide/start-install

下载后进入 `NapCat.Shell` 目录，登录同一 QQ：
```bat
.\launcher-win10-user.bat 123456789[QQ账号]
```
开启 **OneBot 11（正向 WebSocket）**，记下地址（如 `ws://127.0.0.1:3001/onebot/v11/ws`）与 `access_token`（若设置）。

## 二、安装依赖
```bat
cd <项目目录>
python -m venv venv
venv\Scripts\pip install -r requirements.txt
```
仅需 `loguru` + `websockets`。

## 三、配置
首次使用先复制示例配置并填入真实值（`config.toml` 含敏感信息，已被 `.gitignore` 忽略，不会提交；`config.example.toml` 可提交）：
```bat
cp config.example.toml config.toml
```
```toml
[onebot]
ws_url = "ws://127.0.0.1:3001/onebot/v11/ws"   # 上面记下的地址
access_token = ""                                # 若设了 token 填这里（敏感，勿提交）
group_ids = [123456789]                          # 要监控的群号，多个用逗号

[log]
file = "monitor.log"     # 日志文件
level = "DEBUG"          # DEBUG=文件含心跳等全部事件；INFO=仅关键事件
```

---

## 四、使用

### 1. 常驻监听（仅记录基本信息）
```bat
venv\Scripts\python monitor.py
```
输出示例：
```
[已连接] ws://127.0.0.1:3001/onebot/v11/ws
[监控群] [123456789]
等待事件…（在群里发消息 / 传文件）Ctrl+C 退出
[其他事件] meta_event/lifecycle
[其他事件] meta_event/heartbeat
```
退出：`Ctrl+C`（心跳默认只写进 `monitor.log`，不刷控制台）。

### 2. 扫描群文件并取下载直链（最常用）
```bat
venv\Scripts\python monitor.py scan
```
逐文件列出 上传者 / 大小 / 下载次数 / 文件夹，并给出可下载直链，复制 `直链:` 整行即可下载（已自动补 `fname=文件名`）：
```
[扫描] 群=123456789 共 2 个文件
----------------------------------------------------------------
[1/2] 文件名: 示例文档.txt
  上传者: 群友A | 大小: 6.1 KB | 下载次数: 7
  文件夹: (根目录) | file_id: abc123...
  直链: https://gzc-download.ftn.qq.com/ftn_handler/.../?fname=示例文档.txt
----------------------------------------------------------------
```

---

## 五、常见问题
- **连不上**：核对 `ws_url` / `access_token` 与 NapCat 是否一致，确认 NapCat 已开启 WS。
- **直链为空 / 失效**：文件可能已删或 `rkey` 过期，重新跑一次 `scan` 取新链即可。
- **下载保存名空白**：取链时已自动补 `fname=文件名`，直接用日志里的直链即可。
- **上传时间显示 1970**：QQ 群文件接口不返回真实上传时间（协议限制，非 bug）。

## 六、文件
| 文件 | 作用 |
|------|------|
| `monitor.py` | 主程序（监听 / 扫描取链 / 写日志） |
| `config.toml` / `config.py` | 配置（前者含敏感信息，已忽略） |
| `config.example.toml` | 配置模板（可提交） |
| `monitor.log` | 运行日志 |
| `NapCat.Shell/` | NapCat 运行时（第三方，**不纳入 git**） |

---

## 鸣谢
- 本工具依赖 [NapCatQQ](https://github.com/NapNeko/NapCatQQ) 提供的 OneBot 11 接口实现群文件监听与取链。
- NapCatQQ 采用其自有的 **Limited Redistribution License**（非商业用途、修改后的代码不得公开发布）。本项目仅以客户端方式调用其接口，**未包含、未修改 NapCat 本体**（`NapCat.Shell/` 已在 `.gitignore` 中忽略）。

## 许可证
- 本项目自身源码以 **MIT License** 发布，详见 [LICENSE](./LICENSE)。
- 本项目仅供**个人、非商业**使用，与 NapCatQQ 官方无隶属关系。

## 免责声明
- 本工具**风险未测，按现状（as-is）提供**，作者不对使用过程中产生的任何后果负责。
- 仅供**个人学习 / 非商业**用途，请遵守 QQ 与 NapCatQQ 的平台服务条款，**注意合理使用，风险自负**。
- 因使用本工具导致的账号封禁、数据丢失、法律纠纷等一切后果，由使用者自行承担。
