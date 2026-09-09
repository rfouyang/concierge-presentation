# concierge-presentation

用 REST 接口和网页界面控制**一份固定的 PowerPoint** 和**一个固定的视频**。人在网页上
点，机器人打接口，两边控的是同一个 PowerPoint 进程和同一个 mpv 进程。

ppt 和视频不交叉播 —— 要么放完视频接着放 ppt，要么反过来 —— 所以启动一个之前会自动把
另一个停掉。

Windows only：PowerPoint 靠 COM 驱动，视频靠 mpv 的 JSON IPC。

## 跑起来

```bash
uv sync
cp env_example .env      # 改 DECK_PATH / VIDEO_PATH / MPV_PATH
uv run python -m app.api.api_main
```

- `http://127.0.0.1:8000/ui` —— 人用的面板，幻灯片 / 视频两个 tab
- `http://127.0.0.1:8000/docs` —— 接口文档，可以直接点着试
- `http://127.0.0.1:8000/api/ppt/*`、`/api/video/*` —— 机器人用的接口

需要装 mpv（`winget install shinchiro.mpv`）。它不进 PATH，所以 `.env` 里要写
`MPV_PATH` 的绝对路径。

## 接口

两个 blueprint 各管一半，写操作和读操作返回同一个 status，一次请求就够刷新界面。

### 幻灯片 `/api/ppt`

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/status` | |
| POST | `/show` | 打开 ppt 并开始放映（会先关掉视频） |
| POST | `/stop` | 退出放映 |
| POST | `/next` | 下一步，等同按空格：有动画的页推进的是动画 |
| POST | `/next-slide` | 下一张，跳过页内动画，页码必然 +1 |
| POST | `/previous` | 上一步，等同 Backspace |
| POST | `/previous-slide` | 上一张，页码必然 -1 |
| POST | `/goto` | `{"slide": 3}` |
| POST | `/screen` | `{"mode": "normal\|black\|white"}` |
| POST | `/focus` | 被别的窗口盖住时提回最前面 |
| POST | `/monitor` | `{"index": 2}` 换屏 |

```json
{"deck": "demo.pptx", "slide": 3, "total": 12, "playing": true,
 "monitor": 2, "foreground": true}
```

### 视频 `/api/video`

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/status` | |
| POST | `/play` | 从头播（会先退掉 ppt 放映） |
| POST | `/pause` / `/resume` | |
| POST | `/stop` | 停止并关掉播放窗口 |
| POST | `/seek` | `{"seconds": 30}` 绝对定位 |
| POST | `/focus` | |
| POST | `/monitor` | `{"index": 2}` |

```json
{"video": "video.mp4", "running": true, "playing": true, "paused": false,
 "finished": false, "position": 22.02, "duration": 53.45,
 "monitor": 2, "foreground": true}
```

`running` 和 `playing`是两件事：mpv 常驻，暂停或播完时窗口还在（`running`）但画面
不动（`playing` 为假）。播完停在最后一帧，不会突然露出桌面。

### 共用

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/monitors` | 有几块屏、编号多少（跟放什么无关） |

## 机器人怎么用

典型只有两件事：翻页和查页码。

```bash
curl -X POST http://127.0.0.1:8000/api/ppt/next-slide   # 讲完一页，翻一页
curl http://127.0.0.1:8000/api/ppt/status               # 需要确认时才查
```

翻页那几个操作都需要有个正在放映的窗口。**没在放映时它们是空操作**，返回 200 和当前
status（`playing: false`），不会报错 —— 用户手动按 Esc 退出放映后，机器人接着发指令也
只是什么都不发生。视频那边同理。

边界：`next-slide` 在最后一张、`previous-slide` 在第一张都是空操作；而 `next` 在最后
一张上再按会翻到结尾黑屏，再按一次整个放映就结束了。结束放映请显式调 `/api/ppt/stop`。

## 放到哪块屏

`GET /api/monitors` 列出本机的屏幕，编号从 1 开始，顺序就是 Windows 的显示器枚举顺序：

```json
[{"index": 1, "width": 1440, "height": 2560, "primary": false},
 {"index": 2, "width": 2560, "height": 1440, "primary": true}]
```

- **固定下来**：`.env` 里写 `MONITOR=2`（ppt）和 `VIDEO_MONITOR=2`（视频），留空就是主屏
- **临时切换**：`POST /api/ppt/monitor` 或 `/api/video/monitor`，界面上也有下拉框

两边的实现不一样。ppt 是放映起来之后改 `SlideShowWindow` 的 `Left/Top/Width/Height`
（单位是磅 = 像素 × 0.75），窗口仍然是全屏；视频直接用 mpv 的 `--fs-screen=N`（mpv 从 0
数，对外统一从 1 数，在 `video_helper` 里换算）。另外 ppt 放映前会强制关掉演示者视图，
否则 PowerPoint 会自己把幻灯片和备注面板分到两块屏上。

## 放映被别的窗口盖住

`Run()` 之后放映窗口**不一定在前台**。`/show`、`/play`、`/monitor` 都会自动把窗口提到
最前，被盖住时再调 `/focus`，`status` 的 `foreground` 字段能看出当前是不是被盖着。

难点是 Windows 的**前台锁**：不持有前台的进程调 `SetForegroundWindow` 会被直接拒绝
（`pywintypes.error: (0, 'SetForegroundWindow', ...)`，没有错误文本）。从控制台跑脚本
时能成功，但从 uvicorn 的工作线程调就失败 —— 而这正是服务的运行方式。

所以 `WindowHelper.focus()` 是按结果递进的三步：

1. `SW_RESTORE`，窗口可能只是被最小化了；
2. `AttachThreadInput` 把本线程挂到当前前台窗口的线程上，借它的前台资格再抢；
3. 判断依据是**结果**而不是有没有报错 —— 刚创建的窗口上它常常既不报错也没抢到 ——
   这时用 `SwitchToThisWindow` 兜底（半公开 API，不受前台锁约束）。

另两条走不通的路：`SlideShowWindow.Activate()` 毫无反应；`SetWindowPos(HWND_TOPMOST)`
不报错但 `WS_EX_TOPMOST` 根本置不上。放映窗口的句柄用 `FindWindow("screenClass", None)`
找 —— `SlideShowWindow.HWND` 在部分 Office 版本上调用会报 Member not found。

## 目录结构

依赖方向 `app → component → util`，界面走 `app/ui_present → app/api/client`，只经 HTTP，
不碰 component。

```
config/settings.py                 路径、放映常量、mpv 参数、监听地址
util/
  window_helper.py                 显示器枚举 + 提到最前，两边共用
  powerpoint_helper.py             COM 原子能力，不含演示概念
  video_helper.py                  起 mpv + JSON IPC
component/
  stage.py                         舞台：持有两半边，保证不同时上台
  ppt_application.py               幻灯片的全部业务能力
  video_application.py             视频的全部业务能力
app/api/
  api_main.py                      挂两个 router + 界面，程序入口
  routers/ppt.py, routers/video.py 两个 blueprint
  client.py                        PptClient / VideoClient，跟路由一起改
app/ui_present/
  tabs/ppt_tab.py, tabs/video_tab.py
```

## 三个设计上的取舍

**COM 对象不缓存。** 每次调用现 `Dispatch` 一次，附着到正在运行的 PowerPoint。FastAPI
的同步端点跑在线程池上，缓存下来的 COM 对象换个线程再用会报 `RPC_E_WRONG_THREAD`；状态
全交给 PowerPoint 自己记，Python 侧一个句柄都不留。

**mpv 也是同一个模式。** `--idle=yes` 让它播完不退出，换片子只要一条 `loadfile`；每条
指令现连一次命名管道，写一行 JSON、读一行 JSON 就关。但管道**一次只接一个客户端**，
上一个连接刚断开的瞬间再连会撞 `ERROR_PIPE_BUSY`（线程池里两个请求同时发指令必然遇到），
所以 `_connect` 带短重试；而管道不存在（`FileNotFoundError`）意味着 mpv 真的不在，不重试。

**页码和进度只信播放器。** ppt 一律读 `View.CurrentShowPosition`，视频一律读 mpv 的
`time-pos`，不自己维护影子计数，所以观众拿遥控器手动翻的页、或在 mpv 窗口上按的键，
刷新一下都能看到。

## 单文件自测

每个文件底部都有 demo，可以单独跑：

```bash
uv run python -m util.window_helper              # 列显示器（无副作用）
uv run python -m util.powerpoint_helper          # 真的放映一次，翻三页
uv run python -m util.video_helper               # 真的播一段，暂停/定位/换屏
uv run python -m component.stage                 # 离线检查两半边的配置
uv run python -m component.ppt_application       # 离线检查
uv run python -m component.video_application     # 离线检查
uv run python -m app.api.client                  # 对着已起的服务走一遍
```
