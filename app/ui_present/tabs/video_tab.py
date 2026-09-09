"""视频面板。

和幻灯片那个 tab 同样的形状：只调 REST 接口，不 import component。
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import gradio as gr

from app.ui_present.context import video_client


class VideoTab:
    """无状态：每次点击都拿接口返回的 status 重画那一行文字。"""

    LABEL = "视频"

    def build(self) -> None:
        self.info = gr.Markdown()
        with gr.Row():
            self.play_button = gr.Button("从头播放", variant="primary")
            self.pause_button = gr.Button("暂停")
            self.resume_button = gr.Button("继续")
            self.stop_button = gr.Button("停止")
        with gr.Row():
            self.seconds = gr.Number(label="定位到第几秒", value=0, precision=0, scale=1)
            self.seek_button = gr.Button("定位", scale=1)
            self.refresh_button = gr.Button("刷新", scale=1)
        with gr.Row():
            self.monitor_choice = gr.Dropdown(label="投到哪块屏", choices=[], scale=1)
            self.move_button = gr.Button("切换屏幕", scale=1)
            self.focus_button = gr.Button("提到最前", scale=1)

    def wire(self) -> None:
        pairs = [
            (self.play_button, video_client.play),
            (self.pause_button, video_client.pause),
            (self.resume_button, video_client.resume),
            (self.stop_button, video_client.stop),
            (self.refresh_button, video_client.status),
            (self.focus_button, video_client.focus),
        ]
        for button, call in pairs:
            button.click(self._render(call), outputs=self.info)
        self.seek_button.click(self.on_seek, inputs=self.seconds, outputs=self.info)
        self.move_button.click(self.on_move, inputs=self.monitor_choice, outputs=self.info)

    # ---- 回调 -------------------------------------------------------------

    def _render(self, call):
        return lambda: self.describe(call())

    def on_seek(self, seconds) -> str:
        return self.describe(video_client.seek(float(seconds)))

    def on_move(self, index) -> str:
        return self.describe(video_client.move(int(index)))

    def load(self) -> tuple:
        """页面打开时问一次状态和屏幕列表。屏幕列表不能在 build 时取 —— 那会儿
        接口还没起来。"""
        status = video_client.status()
        monitors = video_client.monitors()
        choices = [
            (f"屏幕 {monitor['index']}：{monitor['width']}×{monitor['height']}"
             f"{'（主屏）' if monitor['primary'] else ''}", monitor["index"])
            for monitor in monitors
        ]
        selected = status["monitor"] or next(
            monitor["index"] for monitor in monitors if monitor["primary"]
        )
        return self.describe(status), gr.update(choices=choices, value=selected)

    @staticmethod
    def describe(status: dict) -> str:
        name = f"**{status['video']}**"
        if not status["running"]:
            return f"{name} —— 未播放"

        clock = f"{status['position']:.0f}s / {status['duration']:.0f}s"
        if status["finished"]:
            state = f"已播完（{clock}）"
        elif status["paused"]:
            state = f"已暂停（{clock}）"
        else:
            state = f"正在播放 {clock}"
        covered = "" if status["foreground"] else "，**被其他窗口盖住了**"
        return f"{name} —— {state}，屏幕 {status['monitor']}{covered}"
