# QQ 群文件监控 · 取链工具（精简版，loguru，无 Web / 无 DB）

基于 **NapCatQQ（OneBot 11）+ Python + loguru**。两个功能：
- `monitor.py` —— 常驻监听，记录连接 / 生命周期 / 心跳等基本信息
- `monitor.py scan` —— 扫描各监控群的**全部文件**，并逐个给出可下载直链

---

## 一、准备（只需一次）

官方资源地址
- 下载页面：https://github.com/NapNeko/NapCatQQ/releases，下载Shell版本
- 官方文档：https://napneko.github.io/guide/start-install

下载后进入NapCatQQ.Shell目录，登录同一 QQ。
```bat
./launcher-win10-user.bat 123456[QQ账号]
``` 


开启 **OneBot 11（正向 WebSocket）**，记下地址（如 `ws://127.0.0.1:3001/onebot/v11/ws`）和 `access_token`（若设了）。




## 二、安装依赖
```bat
cd <项目目录>
python -m venv venv
venv\Scripts\pip install -r requirements.txt
```
只需 `loguru` + `websockets`。

## 三、配置 config.toml
首次使用先复制示例配置并填入你的真实值（`config.toml` 含敏感信息，已被 `.gitignore` 忽略，**不会提交到 git**；`config.example.toml` 可提交）：
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

## 四、怎么用

### 1. 常驻监听（仅记录基本信息）
```bat
venv\Scripts\python monitor.py
```
控制台 / `monitor.log` 会记录：
```
[已连接] ws://127.0.0.1:3001/onebot/v11/ws
[监控群] [123456789]
等待事件…（在群里发消息 / 传文件）Ctrl+C 退出
[其他事件] meta_event/lifecycle
[其他事件] meta_event/heartbeat
```
退出：`Ctrl+C`。（心跳默认只写进 `monitor.log`，不刷控制台。）

### 2. 扫描全部群文件并取下载直链（最常用）
```bat
venv\Scripts\python monitor.py scan
```
逐个文件列出 上传者 / 大小 / 下载次数 / 文件夹，并**给出可下载直链**，把 `直链:` 整行复制即可下载（已自动补 `fname=文件名`）：
```
[扫描] 群=123456789 共 2 个文件
----------------------------------------------------------------
[1/2] 文件名: 示例文档.txt
  上传者: 群友A | 大小: 6.1 KB | 下载次数: 7
  文件夹: (根目录) | file_id: abc123...
  直链: https://gzc-download.ftn.qq.com/ftn_handler/.../?fname=示例文档.txt
----------------------------------------------------------------
[2/2] 文件名: 资料包.zip
  上传者: 群友B | 大小: 895.8 KB | 下载次数: 5
  文件夹: (根目录) | file_id: def456...
  直链: https://gzc-download.ftn.qq.com/ftn_handler/.../?fname=资料包.zip
----------------------------------------------------------------
```

---

## 五、常见问题
- **连不上**：核对 `ws_url` / `access_token` 与 NapCat 是否一致，确认 NapCat 已开 WS。
- **直链为空 / 失效**：文件可能已删或 `rkey` 过期，重新跑一次 `scan` 取新链即可。
- **下载保存名空白**：本程序取链时已自动补 `fname=文件名`，用日志里的直链即可。
- **上传时间显示 1970**：QQ 群文件接口不返回真实上传时间（协议限制，非 bug）。

---

## 六、文件
| 文件 | 作用 |
|------|------|
| `monitor.py` | 主程序（监听 / 扫描取链 / 写日志） |
| `config.toml` / `config.py` | 配置 |
| `monitor.log` | 运行日志 |
