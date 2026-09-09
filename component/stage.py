"""舞台：同一时间只放一样东西。

ppt 和视频不会交叉播 —— 要么放完视频接着放 ppt，要么反过来。所以启动一个之前先
把另一个停掉：两个全屏窗口落在同一块屏上会互相抢前台，谁后启动谁在上面，看着就
像坏了。这条规则是业务规则，所以放在 component，两个 application 各自仍然独立、
能单独 demo。

    uv run python -m component.stage
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from component.ppt_application import PptApplication
from component.video_application import VideoApplication
from config.settings import use_utf8_output
from util.window_helper import WindowHelper


class Stage:
    """持有两半边，并保证它们不同时上台。

    除了这两个「上台」的入口，其余操作（翻页、暂停、定位、换屏）直接走
    stage.ppt.xxx 和 stage.video.xxx，这里不做转发壳子。
    """

    def __init__(self, **kwargs) -> None:
        self.ppt = PptApplication(**kwargs)
        self.video = VideoApplication(**kwargs)

    def show_ppt(self) -> dict:
        """开始放 ppt，先把视频关掉。"""
        self.video.stop()
        return self.ppt.show()

    def play_video(self) -> dict:
        """开始放视频，先把 ppt 的放映退掉（ppt 文件仍开着，下次 show 快）。"""
        self.ppt.stop()
        return self.video.play()

    def monitors(self) -> list[dict]:
        """有几块屏、编号多少、多大。跟放什么无关，所以在舞台这一层。"""
        primary = WindowHelper.primary_monitor()
        return [
            {
                "index": index,
                "width": right - left,
                "height": bottom - top,
                "primary": index == primary,
            }
            for index, (left, top, right, bottom)
            in enumerate(WindowHelper.monitors(), start=1)
        ]


def demo_stage() -> None:
    """不碰 PowerPoint 和 mpv 的离线检查。"""
    stage = Stage()
    print(f"ppt:   {stage.ppt.deck}（存在 {stage.ppt.deck.exists()}）")
    print(f"视频:  {stage.video.video}（存在 {stage.video.video.exists()}）")

    print("\n屏幕:")
    for monitor in stage.monitors():
        mark = "  <- 主屏" if monitor["primary"] else ""
        print(f"  屏幕 {monitor['index']}: "
              f"{monitor['width']}x{monitor['height']}{mark}")

    # 两半边都没在放时，互斥逻辑不该碰任何东西。
    print(f"\nppt 状态:   {stage.ppt.status()}")
    print(f"视频状态:   {stage.video.status()}")
    print("\n实际放映请跑服务: uv run python -m app.api.api_main")


def main() -> None:
    use_utf8_output()
    demo_stage()


if __name__ == "__main__":
    main()
