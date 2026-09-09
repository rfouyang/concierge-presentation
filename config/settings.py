"""项目配置，按域分开。一次性从 .env 读入。"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def use_utf8_output() -> None:
    """让 stdout/stderr 能打印中文。

    Windows 控制台默认是旧代码页，打印一个中文文件名就会抛
    UnicodeEncodeError —— 在 try 里看起来像是操作本身失败了。入口先调它。
    """
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def _resolve(value: str) -> Path:
    """相对路径按项目根目录算，绝对路径原样返回。"""
    path = Path(value)
    return path if path.is_absolute() else BASE_DIR / path


class PathConfig:
    """哪些目录存什么。"""

    BASE_DIR = BASE_DIR

    # 用户的 ppt。放的是原件，任何清理都不许碰。
    DECK_DIR = BASE_DIR / "data" / "deck"

    # 要控制的那一份。整个服务从头到尾只认这个文件，换 ppt 改 .env 后重启。
    DECK = _resolve(os.getenv("DECK_PATH", "data/deck/demo.pptx"))


class SlideShowConfig:
    """PowerPoint COM 的放映常量。原值是 Office 的枚举，这里给个名字。"""

    # SlideShowSettings.ShowType
    SPEAKER = 1       # 演讲者全屏
    WINDOW = 2        # 窗口化，调试时看得见别的窗口
    KIOSK = 3         # 展台

    # SlideShowSettings.AdvanceMode
    MANUAL = 1        # 只听我们的指令翻页
    USE_TIMINGS = 2   # 用 ppt 自带的排练计时

    # SlideShowView.State
    RUNNING = 1
    PAUSED = 2
    BLACK = 3
    WHITE = 4
    DONE = 5

    # 屏幕模式的对外名字 -> View.State
    SCREEN_MODES = {"normal": RUNNING, "black": BLACK, "white": WHITE}

    # 放映投到第几块屏，从 1 开始，编号顺序同 Windows 的显示器枚举。
    # 留空就是主屏。运行时也能通过 /api/monitor 换。
    MONITOR = int(os.getenv("MONITOR") or 0)

    # Office 用磅，Windows 的显示器矩形用像素。96 DPI 下 1 像素 = 0.75 磅。
    POINT_PER_PIXEL = 0.75


class ServerConfig:
    """一个进程同时服务两类调用方：机器人走 /api，人走 /ui。"""

    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "8000"))
    UI_PATH = "/ui"
    API_PREFIX = "/api"

    # 网页界面自己也走 HTTP 调上面那套接口，连的就是这个地址。
    BASE_URL = f"http://{HOST}:{PORT}"
    TIMEOUT = 30.0
