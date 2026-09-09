"""用 mpv 放视频，通过 JSON IPC 控制。

技术层：只有起进程、收发 IPC、读属性，不含任何演示业务概念。

模式和 powerpoint_helper 对称：**进程常驻，不缓存连接**。mpv 用 --idle=yes 起来
之后播完不退出，换片子只要一条 loadfile；每条指令现连一次命名管道、写一行 JSON、
读一行 JSON 就关。状态（播到第几秒、暂停没有）全问 mpv，Python 侧不留。

选屏和置顶用 mpv 自己的启动参数（--fs-screen / --ontop），不用像 PowerPoint 那样
自己搬窗口。mpv 的 --fs-screen 从 0 数，对外的屏幕编号从 1 数，在这里换算。

    uv run python -m util.video_helper
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import json
import subprocess
import time

from config.settings import PathConfig, VideoConfig, use_utf8_output
from util.window_helper import WindowHelper


class VideoHelper:
    """一份视频的播放控制。video 只存文件路径。"""

    # mpv 在 Windows 上注册的窗口类名，找句柄用（提到最前、判断在哪块屏）。
    WINDOW_CLASS = "mpv"

    def __init__(self, **kwargs) -> None:
        self.video = Path(kwargs.get("video") or PathConfig.VIDEO).resolve()
        self.mpv = kwargs.get("mpv") or VideoConfig.MPV
        self.pipe = kwargs.get("pipe") or VideoConfig.PIPE
        self.monitor_index = kwargs.get("monitor") or VideoConfig.MONITOR
        self.start_timeout = kwargs.get("start_timeout", VideoConfig.START_TIMEOUT)
        self.connect_retries = kwargs.get("connect_retries", VideoConfig.CONNECT_RETRIES)
        self.connect_wait = kwargs.get("connect_wait", VideoConfig.CONNECT_WAIT)

    # ---- IPC --------------------------------------------------------------

    def _connect(self):
        """连上管道。

        mpv 的命名管道一次只接一个客户端，上一个连接刚断开的瞬间再连会撞上
        ERROR_PIPE_BUSY —— 表现为「mpv 明明活着，探测却说没活」。服务端更躲不开：
        FastAPI 的线程池里两个请求同时发指令必然撞上。所以短重试是必须的，不是容错；
        重试完还是连不上，说明 mpv 真的不在，让异常照常抛出去。
        """
        for attempt in range(self.connect_retries):
            try:
                return open(self.pipe, "r+b", buffering=0)
            except FileNotFoundError:
                # 管道根本不存在 = mpv 不在。重试没有意义，立刻说清楚。
                raise
            except OSError:
                # 主要是 ERROR_PIPE_BUSY：上一个客户端刚断开，mpv 还没重新监听。
                if attempt == self.connect_retries - 1:
                    raise
                time.sleep(self.connect_wait)

    @property
    def running(self) -> bool:
        """mpv 在不在。管道随进程一起消失，所以能连上就等于活着。"""
        try:
            with self._connect():
                return True
        except OSError:
            return False

    def send(self, *command) -> dict:
        """发一条命令，返回 mpv 的回复。"""
        payload = json.dumps({"command": list(command)}).encode() + b"\n"
        with self._connect() as pipe:
            pipe.write(payload)
            while True:
                message = json.loads(pipe.readline())
                # mpv 会在同一条连接上推事件，事件不是回复，跳过。
                if "event" not in message:
                    return message

    def get(self, name: str):
        return self.send("get_property", name).get("data")

    def set(self, name: str, value) -> None:
        self.send("set_property", name, value)

    # ---- 进程 -------------------------------------------------------------

    def start(self) -> None:
        """起一个常驻 mpv。已经起着就什么都不做。

        --force-window 让它在还没加载片子时就先把全屏黑底窗口摆好，避免 loadfile
        那一刻观众看到桌面闪一下。
        """
        if self.running:
            return
        monitor = self.monitor_index or WindowHelper.primary_monitor()
        subprocess.Popen([
            str(self.mpv),
            f"--input-ipc-server={self.pipe}",
            "--fullscreen",
            f"--fs-screen={monitor - 1}",
            *VideoConfig.IDLE_ARGS,
        ])
        deadline = time.monotonic() + self.start_timeout
        while not self.running and time.monotonic() < deadline:
            time.sleep(0.1)

    def quit(self) -> None:
        """关掉 mpv，窗口一起消失。

        要等它真的退干净：quit 只是把指令递进去，mpv 退出要一会儿，这期间管道还
        在。紧跟着的一次状态查询会先看到「还活着」、读到一半管道就没了。
        """
        self.send("quit")
        deadline = time.monotonic() + self.start_timeout
        while self.running and time.monotonic() < deadline:
            time.sleep(self.connect_wait)

    # ---- 播放 -------------------------------------------------------------

    def load(self, video: str | Path | None = None) -> None:
        """从头播。mpv 常驻，所以这只是一条 loadfile。"""
        path = Path(video).resolve() if video else self.video
        self.send("loadfile", str(path), "replace")

    def pause(self, value: bool = True) -> None:
        self.set("pause", value)

    def seek(self, seconds: float) -> None:
        """绝对定位到第几秒。"""
        self.send("seek", seconds, "absolute")

    # ---- 状态 -------------------------------------------------------------

    @property
    def position(self) -> float:
        """播到第几秒。没加载片子时 mpv 返回 null，折成 0。"""
        return self.get("time-pos") or 0.0

    @property
    def duration(self) -> float:
        return self.get("duration") or 0.0

    @property
    def paused(self) -> bool:
        return bool(self.get("pause"))

    @property
    def loaded(self) -> str | None:
        """当前加载的文件路径，没加载返回 None。"""
        return self.get("path")

    @property
    def finished(self) -> bool:
        """播完了。--keep-open 让它停在最后一帧，窗口还在。"""
        return bool(self.get("eof-reached"))

    # ---- 窗口 -------------------------------------------------------------

    def hwnd(self) -> int:
        return WindowHelper.find(self.WINDOW_CLASS)

    @property
    def foreground(self) -> bool:
        return WindowHelper.foreground(self.hwnd())

    @property
    def monitor(self) -> int:
        return WindowHelper.monitor_of(self.hwnd())

    def focus(self) -> bool:
        return WindowHelper.focus(self.hwnd())

    def move(self, monitor: int) -> int:
        """换到第 monitor 块屏。fs-screen 要先退出全屏再进才生效。"""
        self.set("fullscreen", False)
        self.set("fs-screen", str(monitor - 1))
        self.set("fullscreen", True)
        return monitor


def demo_video(pause: float = 3.0) -> None:
    """起 mpv、放一段、暂停、定位、换屏、退出，每步打印 mpv 报回来的状态。"""
    video = VideoHelper()
    print(f"mpv:   {video.mpv}")
    print(f"视频:  {video.video}（存在: {video.video.exists()}）")
    for index, rect in enumerate(WindowHelper.monitors(), start=1):
        mark = "（主屏）" if index == WindowHelper.primary_monitor() else ""
        print(f"屏幕 {index}: {rect}{mark}")

    print("\n起 mpv …")
    video.start()
    print(f"活着: {video.running}")

    video.load()
    time.sleep(pause)
    print(f"播放中: {video.position:.1f}s / {video.duration:.1f}s  "
          f"屏幕 {video.monitor}  在最前 {video.foreground}")

    video.pause()
    time.sleep(1)
    print(f"暂停后: paused={video.paused}  位置 {video.position:.1f}s")

    video.seek(10)
    video.pause(False)
    time.sleep(pause)
    print(f"定位到 10s 并继续: {video.position:.1f}s  paused={video.paused}")

    others = [i for i in range(1, len(WindowHelper.monitors()) + 1)
              if i != video.monitor]
    if others:
        target = others[0]
        video.move(target)
        time.sleep(2)
        print(f"搬到屏幕 {target}: 现在在屏幕 {video.monitor}")

    print(f"加载的文件: {video.loaded}")
    video.quit()
    time.sleep(1)
    print(f"退出后还活着吗: {video.running}")


def main() -> None:
    use_utf8_output()
    demo_video()


if __name__ == "__main__":
    main()
