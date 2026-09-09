"""视频控制对外的全部能力。幻灯片那半边在 ppt_application.py。

和 PptApplication 对称：所有写操作都返回同一个 status，调用方一次请求就能拿到
刷新界面需要的全部东西；播到第几秒这种事由 mpv 自己记着，这里不留状态。

    uv run python -m component.video_application
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.settings import PathConfig, VideoConfig, use_utf8_output
from util.video_helper import VideoHelper


class VideoApplication:
    """控制固定的那一个视频文件。"""

    def __init__(self, **kwargs) -> None:
        self.mpv = VideoHelper(**kwargs)

    @property
    def video(self) -> Path:
        return self.mpv.video

    def status(self) -> dict:
        """mpv 没起来时全部折成零值 —— 那会儿管道不存在，问什么都问不到。

        running 和 playing 是两件事：mpv 常驻，播完或暂停时窗口还在（running），
        但没有画面在动（playing 为假）。

        一个 status 要问 mpv 好几个属性，而 mpv 是**独立进程**、随时可能在这中间
        消失（观众按了 q、我们刚发过 quit、进程崩了）。读到一半没了就等于没在播，
        所以这里有一个 OSError 边界 —— 不是容错，是「对方不在」这个状态的定义。
        """
        idle = {
            "video": self.video.name,
            "running": False,
            "playing": False,
            "paused": False,
            "finished": False,
            "position": 0.0,
            "duration": 0.0,
            "monitor": 0,
            "foreground": False,
        }
        try:
            if not self.mpv.running:
                return idle
            paused = self.mpv.paused
            finished = self.mpv.finished
            return {
                "video": self.video.name,
                "running": True,
                "playing": bool(self.mpv.loaded) and not paused and not finished,
                "paused": paused,
                "finished": finished,
                "position": round(self.mpv.position, 2),
                "duration": round(self.mpv.duration, 2),
                "monitor": self.mpv.monitor,
                "foreground": self.mpv.foreground,
            }
        except OSError:
            return idle

    # ---- 播放 -------------------------------------------------------------

    def play(self) -> dict:
        """从头播。mpv 没起就先起，起着就直接换片 —— 不重启进程。"""
        self.mpv.start()
        self.mpv.load()
        self.mpv.focus()
        return self.status()

    def pause(self) -> dict:
        if self.mpv.running:
            self.mpv.pause(True)
        return self.status()

    def resume(self) -> dict:
        if self.mpv.running:
            self.mpv.pause(False)
        return self.status()

    def stop(self) -> dict:
        """关掉 mpv，窗口一起消失。已经关了就什么都不做。"""
        if self.mpv.running:
            self.mpv.quit()
        return self.status()

    def seek(self, seconds: float) -> dict:
        """绝对定位到第几秒。"""
        if self.mpv.running:
            self.mpv.seek(seconds)
        return self.status()

    # ---- 窗口 -------------------------------------------------------------

    def focus(self) -> dict:
        """被别的窗口盖住时提回最前面。"""
        if self.mpv.running:
            self.mpv.focus()
        return self.status()

    def move(self, monitor: int) -> dict:
        """搬到第 monitor 块屏。"""
        if self.mpv.running:
            self.mpv.move(monitor)
            self.mpv.focus()
        return self.status()


def demo_application() -> None:
    """不起 mpv 的离线检查：配置接得上、文件在不在。"""
    application = VideoApplication()
    print(f"要播的视频: {application.video}")
    print(f"文件存在: {application.video.exists()}")
    assert application.video == PathConfig.VIDEO.resolve()

    print(f"mpv: {VideoConfig.MPV}")
    print(f"管道: {VideoConfig.PIPE}")
    print(f"投到屏幕: {VideoConfig.MONITOR or '主屏（未在 .env 指定）'}")

    status = application.status()
    print(f"\n当前状态（mpv 未起时应全为零值）: {status}")
    assert status["running"] is False and status["position"] == 0.0

    print("\n实际播放请跑: uv run python -m util.video_helper")


def main() -> None:
    use_utf8_output()
    demo_application()


if __name__ == "__main__":
    main()
