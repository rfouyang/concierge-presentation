# concierge-presentation

用 REST 接口和网页界面控制**一份固定的** PowerPoint 放映。人在网页上点，机器人打
接口，两边控的是同一个 PowerPoint 进程。

Windows only —— 靠 COM 驱动本机装着的 PowerPoint。

## 跑起来

```bash
uv sync
cp env_example .env      # 把 DECK_PATH 改成你的 ppt
uv run python -m app.api.api_main
```

- `http://127.0.0.1:8000/ui` —— 人用的翻页面板
- `http://127.0.0.1:8000/docs` —— 接口文档，可以直接点着试
- `http://127.0.0.1:8000/api/*` —— 机器人用的接口

## 接口

写操作和读操作返回同一个 status，一次请求就够刷新界面。

| 方法 | 路径 | 入参 |
|---|---|---|
| GET | `/api/status` | |
| POST | `/api/show` | 打开 ppt 并开始放映 |
| POST | `/api/stop` | 退出放映 |
| POST | `/api/next` | |
| POST | `/api/previous` | |
| POST | `/api/goto` | `{"slide": 3}` |
| POST | `/api/screen` | `{"mode": "normal\|black\|white"}` |
| POST | `/api/focus` | 放映被别的窗口盖住时提回最前面 |
| GET | `/api/monitors` | 有几块屏、编号多少 |
| POST | `/api/monitor` | `{"index": 2}` 把放映搬到那块屏 |

```json
{"deck": "demo.pptx", "slide": 3, "total": 12, "playing": true,
 "monitor": 2, "foreground": true}
```

机器人侧最短的调用：

```bash
curl -X POST http://127.0.0.1:8000/api/next
```

## 目录结构

依赖方向 `app → component → util`，界面走 `app/ui_present → app/api/client`，
只经 HTTP，不碰 component。

```
config/settings.py                 路径、放映常量、监听地址
util/powerpoint_helper.py          COM 原子能力，不含演示概念
component/presentation_application.py
                                   全部业务能力，两个调用方共用
app/api/api_main.py                FastAPI 路由 + 挂载界面，程序入口
app/api/client.py                  接口的 Python 客户端，跟路由一起改
app/ui_present/tabs/playback_tab.py  翻页面板
data/deck/                         ppt 放这里
```

## 放到哪块屏

`GET /api/monitors` 列出本机的屏幕，编号从 1 开始，顺序就是 Windows 的显示器枚举顺序：

```json
[{"index": 1, "width": 1440, "height": 2560, "primary": false},
 {"index": 2, "width": 2560, "height": 1440, "primary": true}]
```

指定用哪块，两种方式：

- **固定下来**：`.env` 里写 `MONITOR=2`，每次 `/api/show` 都投到那块。留空就是主屏。
- **临时切换**：`POST /api/monitor {"index": 1}`，界面上也有个下拉框。

做法是放映起来之后改 `SlideShowWindow` 的 `Left/Top/Width/Height`（单位是磅，
= 像素 × 0.75），窗口仍然是全屏放映。另外放映前会强制关掉演示者视图，否则
PowerPoint 会自己把幻灯片和备注面板分到两块屏上，指定的那块未必是幻灯片。

## 放映被别的窗口盖住

`Run()` 之后放映窗口**不一定在前台**——谁本来在前台就还是谁。`/api/show` 和
`/api/monitor` 都会自动把它提到最前，被盖住时再调 `POST /api/focus` 提一次，
`/api/status` 的 `foreground` 字段能看出当前是不是被盖着。

实测过三种手段，只有一种有效：

| 手段 | 结果 |
|---|---|
| `SlideShowWindow.Activate()` | 无反应 |
| `SetWindowPos(HWND_TOPMOST)` | 不报错，但 `WS_EX_TOPMOST` 都置不上 |
| `win32gui.SetForegroundWindow()` | 有效 |

放映窗口的句柄用 `FindWindow("screenClass", None)` 找 —— `SlideShowWindow.HWND`
这个属性在部分 Office 版本上调用会报 Member not found，不能依赖。

## 两个设计上的取舍

**COM 对象不缓存。** 每次调用现 `Dispatch` 一次，附着到正在运行的 PowerPoint。
FastAPI 的同步端点跑在线程池上，缓存下来的 COM 对象换个线程再用会报
`RPC_E_WRONG_THREAD`；状态全交给 PowerPoint 自己记，Python 侧一个句柄都不留。

**页码只信 PowerPoint。** 一律读 `View.CurrentShowPosition`，不自己维护影子计数，
所以用户拿遥控器手动翻的页，界面刷新一下也能看到。

## 单文件自测

每个文件底部都有 demo，可以单独跑：

```bash
uv run python -m util.powerpoint_helper            # 真的开一次放映，自动翻三页
uv run python -m component.presentation_application  # 离线检查配置
uv run python -m app.api.client                    # 对着已起的服务走一遍
```
