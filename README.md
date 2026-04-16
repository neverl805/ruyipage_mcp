# ruyipage-mcp

<p align="center">
  <b>MCP Server for ruyiPage Firefox Automation</b>
</p>

> 将 [ruyiPage](https://github.com/LoseNine/ruyipage) 的 Firefox BiDi 自动化能力，通过 [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) 暴露为 AI 可调用的工具集。
>
> 支持 Claude Code、Cursor 等任意 MCP 客户端。

---

## 特性

- **34 个工具**，覆盖浏览器自动化全流程：启动/接管浏览器、页面导航、DOM 查找与交互、截图/PDF、Cookie/Storage、JS 执行、网络拦截/监听/数据采集、标签页管理、设备模拟、BiDi 事件订阅
- **原生 BiDi 动作优先** — 点击、输入、拖拽等操作保持 `isTrusted=true`，更适合高风控场景
- **支持接管指纹浏览器** — 可自动探测并接管 ADS / FlowerBrowser 等 Firefox 内核指纹浏览器
- **智能元素管理** — LRU 元素注册表，自动回收 + 过期元素自动重查
- **截图自动压缩** — 超宽图片自动缩放，JPEG 压缩，大图自动落盘
- **stdio 传输** — 标准 JSON-RPC 2.0，开箱即用

---

## 安装

### 前置要求

- Python >= 3.10
- [ruyiPage](https://github.com/LoseNine/ruyipage) >= 1.1.0
- Firefox 浏览器（推荐使用 [ruyiPage 配套的 Firefox 内核](https://github.com/LoseNine/firefox-fingerprintBrowser)）

### 从源码安装

```bash
git clone https://github.com/LoseNine/ruyipage-mcp.git
cd ruyipage-mcp
pip install -e .
```

---

## 配置

### Claude Code

**方式一：** 项目级 `.mcp.json`（推荐）

```json
{
  "mcpServers": {
    "ruyipage": {
      "command": "python",
      "args": ["-m", "ruyipage_mcp"]
    }
  }
}
```

**方式二：** CLI 注册（用户级）

```bash
claude mcp add --scope user ruyipage python -- -m ruyipage_mcp
```

### Cursor / 其他 MCP 客户端

在对应 MCP 配置文件中添加：

```json
{
  "mcpServers": {
    "ruyipage": {
      "command": "python",
      "args": ["-m", "ruyipage_mcp"]
    }
  }
}
```

### 独立运行

```bash
python -m ruyipage_mcp
```

服务器通过 stdin/stdout 传输 JSON-RPC 消息，日志输出到 stderr。

---

## 配置

### 配置文件

将 `ruyipage_mcp.example.json` 复制为 `ruyipage_mcp.json`，按需修改：

```bash
cp ruyipage_mcp.example.json ruyipage_mcp.json
```

```json
{
  "browser_path": "E:\\ruyi_firefox\\firefox.exe",
  "disable_run_js": false,
  "disable_extensions": false,
  "browser_path_whitelist": [],
  "max_elements": 512,
  "event_buffer_size": 500,
  "wait_timeout_ceiling": 60
}
```

**配置文件查找顺序：**

1. `RUYIPAGE_MCP_CONFIG` 环境变量指定的路径
2. 当前工作目录下的 `ruyipage_mcp.json`
3. 若未找到配置文件，使用内置默认值

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `browser_path` | string | `E:\ruyi_firefox\firefox.exe` | Firefox 可执行文件路径 |
| `disable_run_js` | bool | `false` | 设为 `true` 禁用 `js_run` 工具 |
| `disable_extensions` | bool | `false` | 设为 `true` 禁用扩展相关能力 |
| `browser_path_whitelist` | list | `[]` (允许任意路径) | 允许的浏览器路径列表 |
| `max_elements` | int | `512` | 每个会话的元素注册表 LRU 容量 |
| `event_buffer_size` | int | `500` | BiDi 事件缓冲区大小 |
| `wait_timeout_ceiling` | int | `60` | 所有等待类工具的超时上限（秒） |

### 环境变量覆盖

环境变量优先级高于配置文件，适合 CI 或临时覆盖场景：

| 环境变量 | 对应配置项 |
|----------|------------|
| `RUYIPAGE_MCP_BROWSER_PATH` | `browser_path` |
| `RUYIPAGE_MCP_DISABLE_RUN_JS` | `disable_run_js` (`1` = true) |
| `RUYIPAGE_MCP_DISABLE_EXTENSIONS` | `disable_extensions` (`1` = true) |
| `RUYIPAGE_MCP_BROWSER_PATH_WHITELIST` | `browser_path_whitelist` (逗号分隔) |
| `RUYIPAGE_MCP_MAX_ELEMENTS` | `max_elements` |
| `RUYIPAGE_MCP_EVENT_BUFFER_SIZE` | `event_buffer_size` |
| `RUYIPAGE_MCP_WAIT_TIMEOUT_CEILING` | `wait_timeout_ceiling` |
| `RUYIPAGE_MCP_CONFIG` | 指定配置文件路径 |

---

## 工具一览 (34 个)

### session — 浏览器生命周期

| 工具 | 说明 |
|------|------|
| `session_launch` | 启动新 Firefox 浏览器。支持自定义端口、无头模式、隐私模式、XPath Picker、窗口大小等 |
| `session_attach` | 通过 `host:port` 接管已运行的 Firefox |
| `session_auto_attach` | 按进程特征自动探测并接管 Firefox / ADS / FlowerBrowser |
| `session_quit` | 关闭浏览器会话。`owned` 会话直接关闭进程，`attached` 会话仅释放连接 |

**典型流程：**

```
session_launch(port=9222)
  → 操作页面...
  → session_quit()
```

```
# 接管已打开的指纹浏览器
session_auto_attach(latest_tab=true)
  → 操作页面...
  → session_quit()  # 仅释放连接，浏览器继续运行
```

### nav — 页面导航

| 工具 | 说明 |
|------|------|
| `nav_get` | 打开 URL，支持 `complete` / `interactive` / `none` 等待策略 |
| `nav_back` | 后退 |
| `nav_forward` | 前进 |
| `nav_refresh` | 刷新 |
| `nav_info` | 获取当前页面的 URL、标题、ready state |

### dom — 元素查找与读取

| 工具 | 说明 |
|------|------|
| `dom_find` | 查找单个元素，返回 `element_id`。支持 `#id`、`css:`、`xpath:`、`text:`、`tag:` 定位 |
| `dom_find_all` | 查找所有匹配元素，返回列表（默认上限 20，最大 100） |
| `dom_read` | 读取元素属性：`text` / `html` / `inner_html` / `outer_html` / `value` / `attrs` / `rect` / `all` |
| `dom_query_in` | 在已有元素内部继续查找子元素 |
| `dom_wait_for` | 等待元素出现（带超时） |
| `dom_release` | 释放元素句柄，回收注册表空间 |

**定位器格式：**

| 格式 | 示例 | 说明 |
|------|------|------|
| `#id` | `#search-box` | ID 选择器 |
| `css:` | `css:div.card > a` | CSS 选择器 |
| `xpath:` | `xpath://button[text()='Login']` | XPath |
| `text:` | `text:登录` | 文本匹配 |
| `tag:` | `tag:input` | 标签名 |

### act — 元素交互

| 工具 | 说明 |
|------|------|
| `act_click` | 点击元素。支持左键 / 右键 / 双击，可选 JS 点击。默认使用原生 BiDi 动作 (`isTrusted=true`) |
| `act_input` | 输入文本。原生 BiDi 键盘输入，可选清空已有内容。支持 JS 回退 |
| `act_simple` | 简单操作：`hover` / `clear` / `focus` / `scroll_into_view` |
| `act_chain` | 执行 BiDi 动作链（JSON 数组），支持按键、点击、移动、拖拽、滚轮、暂停等 |

**`act_chain` 支持的动作：**

```json
[
  {"action": "press", "key": "Enter"},
  {"action": "click"},
  {"action": "click", "element_id": "el_abc123"},
  {"action": "move_to", "element_id": "el_abc123"},
  {"action": "move_to", "x": 100, "y": 200},
  {"action": "double_click"},
  {"action": "right_click"},
  {"action": "key_down", "key": "Shift"},
  {"action": "key_up", "key": "Shift"},
  {"action": "type", "text": "hello"},
  {"action": "scroll", "x": 0, "y": -300},
  {"action": "pause", "duration": 500}
]
```

### state — 页面状态

| 工具 | 说明 |
|------|------|
| `state_screenshot` | 截图。支持全页面截图、元素截图、保存到文件。自动压缩，超大图自动落盘 |
| `state_save_pdf` | 将当前页面保存为 PDF |
| `state_cookies` | Cookie 管理：`get` / `set` / `delete`。支持按 name/domain 过滤 |
| `state_storage` | localStorage / sessionStorage 管理：`items` / `get` / `set` / `delete` / `clear` |

### js — JavaScript 执行

| 工具 | 说明 |
|------|------|
| `js_run` | 在页面中执行 JS 代码。可作为表达式求值 (`as_expr=true`) 或函数体执行。可通过环境变量禁用 |
| `js_preload` | 管理 preload script：`add`（每次页面加载前注入）/ `remove` |

### net — 网络控制

| 工具 | 说明 |
|------|------|
| `net_intercept` | 请求拦截：`start` → `wait_and_resolve`（continue/mock/fail）→ `stop` |
| `net_listen` | 网络监听：`start` → `wait`（按 URL/method 过滤）→ `stop` |
| `net_collector` | 数据采集器：`add` → `get`（按 request_id 获取请求/响应体）→ `remove` |
| `net_headers` | 设置/清除额外请求头 |
| `net_cache` | 设置缓存行为：`default`（正常缓存）/ `bypass`（强制重新请求） |

**请求拦截典型流程：**

```
net_intercept(op="start", url_patterns="api/login")
  → 触发页面操作
  → net_intercept(op="wait_and_resolve", action='{"mode":"mock","status":200,"body":"{}"}')
  → net_intercept(op="stop")
```

**网络监听典型流程：**

```
net_listen(op="start", targets="api/data", method="POST")
  → 触发页面操作
  → net_listen(op="wait", timeout=10)
  → net_listen(op="stop")
```

### ctx — 上下文管理

| 工具 | 说明 |
|------|------|
| `ctx_tabs` | 标签页管理：`list` / `create` / `close` / `activate` / `reload` |
| `ctx_emulation` | 设备模拟：地理位置、时区、语言、移动设备预设、离线模式、JS 开关 |
| `ctx_events` | BiDi 事件订阅：统一入口管理 `page.events` / `page.navigation` / `page.downloads` |

**模拟操作示例：**

```
ctx_emulation(op="set_geolocation", latitude=39.9, longitude=116.4)
ctx_emulation(op="set_timezone", timezone_id="Asia/Tokyo")
ctx_emulation(op="set_locale", locales="ja-JP,ja")
ctx_emulation(op="apply_mobile_preset", width=390, height=844, device_pixel_ratio=3)
ctx_emulation(op="set_offline", enabled=true)
ctx_emulation(op="set_offline", enabled=false)
```

### meta — 服务器信息

| 工具 | 说明 |
|------|------|
| `ruyipage_describe_capabilities` | 返回当前服务器状态：活跃会话、元素数量、配置开关、工具命名空间列表 |

---

## 核心概念

### 会话管理

每个浏览器连接对应一个 **session**，以 `host:port`（如 `127.0.0.1:9222`）作为标识。

- 当只有一个活跃 session 时，所有工具的 `session_id` 参数可省略，自动解析
- 有多个 session 时，需要显式传入 `session_id`
- `session_launch` 创建的是 **owned** 会话，`session_quit` 会终止浏览器进程
- `session_attach` / `session_auto_attach` 创建的是 **attached** 会话，`session_quit` 仅释放连接

### 元素注册表

通过 `dom_find` / `dom_find_all` 查到的元素会被注册到当前 session 的元素注册表中，返回一个短 ID（如 `el_a3f2b1`）。

- **LRU 回收** — 达到容量上限（默认 512）时，最久未使用的元素自动回收
- **过期自动恢复** — 访问过期元素时，自动尝试用原始定位器重新查找
- 元素 ID 可传给 `act_click`、`act_input`、`dom_read`、`act_chain` 等所有需要元素引用的工具
- 所有接受 `target` 参数的工具也可直接传入定位器字符串（如 `css:button.submit`），无需先调用 `dom_find`

### 响应格式

所有工具（`state_screenshot` 除外）返回统一 JSON 信封：

```json
// 成功
{"ok": true, "data": ...}

// 失败
{"ok": false, "error": "error message"}
```

`state_screenshot` 在截图体积允许时直接返回 MCP `Image` 对象；超过 800KB 时落盘返回文件路径。

---

## 配套项目

- [ruyiPage](https://github.com/LoseNine/ruyipage) — 核心 Firefox BiDi 自动化库
- [ruyipage-skill](https://github.com/LoseNine/ruyipage-skill) — AI 自动化分析运行 Skill
- [Firefox 指纹浏览器](https://github.com/LoseNine/firefox-fingerprintBrowser) — 配套 Firefox 指纹环境

---

## 架构

```
python -m ruyipage_mcp
  → __main__.py → server.run()
    → 导入 tools/*.py（触发 @mcp.tool() 注册 34 个工具）
    → 注册 atexit 清理（退出时关闭 owned 浏览器）
    → mcp.run(transport="stdio")

ruyipage_mcp/
├── app.py          # FastMCP("ruyipage-mcp") 单例
├── config.py       # 环境变量配置
├── registries.py   # SessionRegistry + ElementRegistry (LRU)
├── runtime.py      # async/sync 桥接 + 响应封装 + 元素解析
├── server.py       # 入口 + atexit 清理
└── tools/
    ├── session.py  # 浏览器启动/接管/关闭
    ├── nav.py      # 页面导航
    ├── dom.py      # 元素查找/读取
    ├── act.py      # 元素交互/动作链
    ├── state.py    # 截图/PDF/Cookie/Storage
    ├── js.py       # JS 执行/预加载脚本
    ├── net.py      # 网络拦截/监听/采集
    ├── ctx.py      # 标签页/模拟/事件
    └── meta.py     # 服务器状态
```

ruyiPage 是同步库，MCP FastMCP 是 asyncio。所有 ruyiPage 调用通过 `asyncio.to_thread()` 桥接，确保 MCP 事件循环不被阻塞。

---

## 使用声明

本项目遵循 [ruyiPage](https://github.com/LoseNine/ruyipage) 的使用声明，仅限合法、合规、非盈利的个人研究与技术交流用途。

## License

BSD-3-Clause
