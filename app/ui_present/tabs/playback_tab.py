"""翻页面板。

只调 REST 接口，不 import component —— 界面和机器人用的是同一条路径，
界面上能做的事机器人一定也能做。
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import gradio as gr

from app.ui_present.context import presentation_client


class PlaybackTab:
    """无状态：每次点击都拿接口返回的 status 重画那一行文字。"""

    LABEL = "翻页控制"

    def build(self) -> None:
        self.info = gr.Markdown()
        with gr.Row():
            self.show_button = gr.Button("开始放映", variant="primary")
            self.stop_button = gr.Button("结束放映")
            self.refresh_button = gr.Button("刷新")
        with gr.Row():
            self.previous_button = gr.Button("← 上一页", scale=1)
            self.next_button = gr.Button("下一页 →", scale=1, variant="primary")
        with gr.Row():
            self.slide_number = gr.Number(label="跳到第几页", value=1, precision=0, scale=1)
            self.goto_button = gr.Button("跳转", scale=1)
        with gr.Row():
            self.black_button = gr.Button("黑屏")
            self.white_button = gr.Button("白屏")
            self.normal_button = gr.Button("恢复")
        with gr.Row():
            self.monitor_choice = gr.Dropdown(label="投到哪块屏", choices=[], scale=1)
            self.move_button = gr.Button("切换屏幕", scale=1)

    def wire(self) -> None:
        pairs = [
            (self.show_button, presentation_client.show),
            (self.stop_button, presentation_client.stop),
            (self.refresh_button, presentation_client.status),
            (self.previous_button, presentation_client.previous),
            (self.next_button, presentation_client.next),
            (self.black_button, lambda: presentation_client.screen("black")),
            (self.white_button, lambda: presentation_client.screen("white")),
            (self.normal_button, lambda: presentation_client.screen("normal")),
        ]
        for button, call in pairs:
            button.click(self._render(call), outputs=self.info)
        self.goto_button.click(self.on_goto, inputs=self.slide_number, outputs=self.info)
        self.move_button.click(self.on_move, inputs=self.monitor_choice, outputs=self.info)

    # ---- 回调 -------------------------------------------------------------

    def _render(self, call):
        """把一个「返回 status 的调用」包成 gradio 要的回调。"""
        return lambda: self.describe(call())

    def on_goto(self, slide) -> str:
        return self.describe(presentation_client.goto(int(slide)))

    def on_move(self, index) -> str:
        return self.describe(presentation_client.move(int(index)))

    def refresh(self) -> str:
        return self.describe(presentation_client.status())

    def load(self) -> tuple:
        """页面打开时问一次：现在什么状态，本机有几块屏。

        屏幕列表不能在 build 时取 —— 那会儿接口还没起来。
        """
        status = presentation_client.status()
        monitors = presentation_client.monitors()
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
        if not status["playing"]:
            return f"**{status['deck']}** —— 未放映"
        return (f"**{status['deck']}** —— 第 {status['slide']} / {status['total']} 页"
                f"，屏幕 {status['monitor']}")
