"""演示控制对外的全部能力。

网页界面和机器人都通过 REST 打到这一个对象上，所以两个调用方谁也不需要自带
业务规则。它本身几乎无状态 —— 当前放到第几页这种事，PowerPoint 自己记着。

    uv run python -m component.presentation_application
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.settings import PathConfig, SlideShowConfig, use_utf8_output
from util.powerpoint_helper import PowerPointHelper


class PresentationApplication:
    """控制固定的那一份 ppt。所有写操作都返回同一个 status，调用方一次请求
    就能拿到刷新界面需要的全部东西。"""

    def __init__(self, **kwargs) -> None:
        self.powerpoint = PowerPointHelper(**kwargs)

    @property
    def deck(self) -> Path:
        return self.powerpoint.deck

    def status(self) -> dict:
        """没在放映时页码和屏幕号都是 0，没打开时总页数是 0。"""
        return {
            "deck": self.powerpoint.deck.name,
            "slide": self.powerpoint.current,
            "total": self.powerpoint.total,
            "playing": self.powerpoint.playing,
            "monitor": self.powerpoint.monitor,
            "foreground": self.powerpoint.playing and self.powerpoint.foreground,
        }

    def focus(self) -> dict:
        """放映被别的窗口盖住时，把它提回最前面。"""
        if self.powerpoint.playing:
            self.powerpoint.focus()
        return self.status()

    # ---- 显示器 -----------------------------------------------------------

    def monitors(self) -> list[dict]:
        """有几块屏、编号多少、多大。调用方按 index 指定往哪块投。"""
        primary = self.powerpoint.primary_monitor()
        return [
            {
                "index": index,
                "width": right - left,
                "height": bottom - top,
                "primary": index == primary,
            }
            for index, (left, top, right, bottom)
            in enumerate(self.powerpoint.monitors(), start=1)
        ]

    def move(self, monitor: int) -> dict:
        """把正在放映的窗口搬到第 monitor 块屏，顺手提到最前。"""
        if self.powerpoint.playing:
            self.powerpoint.move(monitor)
            self.powerpoint.focus()
        return self.status()

    # ---- 放映 -------------------------------------------------------------

    def show(self) -> dict:
        """打开并开始放映。已经打开过就直接放映，不重复开文件。"""
        if not self.powerpoint.opened:
            self.powerpoint.open()
        if not self.powerpoint.playing:
            self.powerpoint.run()
        return self.status()

    def stop(self) -> dict:
        """已经停了就什么都不做。"""
        if self.powerpoint.playing:
            self.powerpoint.exit()
        return self.status()

    # ---- 翻页 -------------------------------------------------------------
    #
    # 这几个都得有个正在放映的窗口才成立，没放映时 SlideShowWindows(1) 会越界。
    # 一律先看 playing：没在放映就什么都不做，直接把 status 还回去 —— 调用方从
    # playing 字段就能看出为什么没动，用户手动 Esc 掉放映也不会让接口 500。

    def next(self) -> dict:
        """下一步。和按空格键完全一致：有动画的页上推进的是动画，页码不变。"""
        if self.powerpoint.playing:
            self.powerpoint.next()
        return self.status()

    def next_slide(self) -> dict:
        """下一张幻灯片。跳过页内动画，页码必然 +1。

        给机器人用的：讲完一页翻一页，不需要处理「翻了但页码没变」。已经在最后
        一页就什么都不做 —— 结束放映走 /api/stop，不从这里溢出。
        """
        if self.powerpoint.playing and self.powerpoint.current < self.powerpoint.total:
            self.powerpoint.goto(self.powerpoint.current + 1)
        return self.status()

    def previous(self) -> dict:
        """上一步。和按 Backspace 一致：有动画的页上退的是动画步骤。"""
        if self.powerpoint.playing:
            self.powerpoint.previous()
        return self.status()

    def previous_slide(self) -> dict:
        """上一张幻灯片。跳过页内动画，页码必然 -1。

        和 next_slide 对称。已经在第 1 页就什么都不做。
        """
        if self.powerpoint.playing and self.powerpoint.current > 1:
            self.powerpoint.goto(self.powerpoint.current - 1)
        return self.status()

    def goto(self, slide: int) -> dict:
        if self.powerpoint.playing:
            self.powerpoint.goto(slide)
        return self.status()

    def screen(self, mode: str) -> dict:
        """mode 取 normal / black / white。"""
        if self.powerpoint.playing:
            self.powerpoint.screen(SlideShowConfig.SCREEN_MODES[mode])
        return self.status()


def demo_application() -> None:
    """不碰 PowerPoint 的离线检查：配置接得上、屏幕模式对得上。"""
    application = PresentationApplication()
    print(f"要控制的 ppt: {application.deck}")
    print(f"文件存在: {application.deck.exists()}")
    assert application.deck == PathConfig.DECK.resolve()

    assert set(SlideShowConfig.SCREEN_MODES) == {"normal", "black", "white"}
    assert SlideShowConfig.SCREEN_MODES["black"] == SlideShowConfig.BLACK
    print("屏幕模式映射 OK:", SlideShowConfig.SCREEN_MODES)

    print(f"\n放映用的屏幕: {SlideShowConfig.MONITOR or '主屏（未在 .env 指定）'}")
    for monitor in application.monitors():
        mark = "  <- 主屏" if monitor["primary"] else ""
        print(f"  屏幕 {monitor['index']}: "
              f"{monitor['width']}x{monitor['height']}{mark}")

    print("\n实际放映请跑: uv run python -m util.powerpoint_helper")


def main() -> None:
    use_utf8_output()
    demo_application()


if __name__ == "__main__":
    main()
