"""显示器枚举与窗口层级。

技术层里最底下的一块：这里一个业务概念都没有，只有显示器矩形、窗口句柄和前台。
PowerPoint 那半边和 mpv 那半边都用它，所以从 powerpoint_helper 里抽了出来 ——
不抽就得复制一份「提到最前」的降级链。

单位一律是**像素**。Office 用磅，那是 PowerPoint 自己的事，换算留在
powerpoint_helper 里做。

    uv run python -m util.window_helper
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import ctypes

import pywintypes
import win32api
import win32con
import win32gui
import win32process

from config.settings import use_utf8_output


class WindowHelper:
    """全是静态方法，没有状态可存。"""

    # ---- 显示器 -----------------------------------------------------------

    @staticmethod
    def monitors() -> list[tuple[int, int, int, int]]:
        """每块屏的像素矩形 (left, top, right, bottom)。编号就是这个列表的序号
        （从 1 开始）。副屏在主屏左边或上边时坐标是负的，属正常。"""
        return [tuple(rect) for _, _, rect in win32api.EnumDisplayMonitors()]

    @classmethod
    def primary_monitor(cls) -> int:
        """主屏的编号。Windows 里主屏的左上角固定是 (0, 0)。"""
        return next(index for index, rect in enumerate(cls.monitors(), start=1)
                    if rect[0] == 0 and rect[1] == 0)

    @classmethod
    def monitor_at(cls, x: int, y: int) -> int:
        """这个点落在第几块屏。落在所有屏之外返回 0。"""
        return next((index for index, (left, top, right, bottom)
                     in enumerate(cls.monitors(), start=1)
                     if left <= x < right and top <= y < bottom), 0)

    # ---- 窗口 -------------------------------------------------------------

    @staticmethod
    def find(window_class: str) -> int:
        """按窗口类名找顶层窗口，找不到返回 0。"""
        return win32gui.FindWindow(window_class, None)

    @staticmethod
    def rect(handle: int) -> tuple[int, int, int, int]:
        return tuple(win32gui.GetWindowRect(handle))

    @staticmethod
    def foreground(handle: int) -> bool:
        return bool(handle) and win32gui.GetForegroundWindow() == handle

    @classmethod
    def monitor_of(cls, handle: int) -> int:
        """这个窗口在第几块屏，按左上角判断。句柄为 0 时返回 0。"""
        if not handle:
            return 0
        left, top, _, _ = cls.rect(handle)
        return cls.monitor_at(left, top)

    @classmethod
    def focus(cls, handle: int) -> bool:
        """把窗口提到最前面，返回最后是否真的在前台。

        麻烦在于 SetForegroundWindow 受 Windows 前台锁约束：不持有前台的进程调
        它会直接失败（错误码 0，没有错误文本）。从控制台跑脚本时能成功，但从
        uvicorn 的工作线程调就被拒 —— 而这正是服务的运行方式。所以这里破例带
        except，按结果递进地试：

          1. SW_RESTORE，窗口可能只是被最小化了；
          2. 把本线程挂到当前前台窗口的线程上，借它的前台资格再抢；
          3. 判断依据是**结果**而不是有没有报错（刚创建的窗口上 SetForegroundWindow
             常常既不报错也没抢到），没抢到就用 SwitchToThisWindow 兜底 ——
             半公开 API，不受前台锁约束。
        """
        if not handle:
            return False
        win32gui.ShowWindow(handle, win32con.SW_RESTORE)
        try:
            cls._steal_foreground(handle)
        except pywintypes.error:
            pass
        if not cls.foreground(handle):
            ctypes.windll.user32.SwitchToThisWindow(handle, True)
        return cls.foreground(handle)

    @staticmethod
    def _steal_foreground(handle: int) -> None:
        """把本线程挂到前台窗口的线程上，借它的前台资格再抢。"""
        foreground = win32gui.GetForegroundWindow()
        target_thread, _ = win32process.GetWindowThreadProcessId(foreground)
        own_thread = win32api.GetCurrentThreadId()
        win32process.AttachThreadInput(target_thread, own_thread, True)
        try:
            win32gui.BringWindowToTop(handle)
            win32gui.SetForegroundWindow(handle)
        finally:
            win32process.AttachThreadInput(target_thread, own_thread, False)


def demo_windows() -> None:
    """列出显示器，并报出当前前台窗口是谁、在哪块屏。"""
    helper = WindowHelper()
    primary = helper.primary_monitor()
    for index, (left, top, right, bottom) in enumerate(helper.monitors(), start=1):
        mark = "  <- 主屏" if index == primary else ""
        print(f"屏幕 {index}: {right - left}x{bottom - top} "
              f"@ ({left}, {top}){mark}")

    handle = win32gui.GetForegroundWindow()
    print(f"\n当前前台窗口: {handle} "
          f"class={win32gui.GetClassName(handle)!r} "
          f"title={win32gui.GetWindowText(handle)!r}")
    print(f"它在屏幕 {helper.monitor_of(handle)} 上")


def main() -> None:
    use_utf8_output()
    demo_windows()


if __name__ == "__main__":
    main()
