"""网页界面：把 tab 组装成一个页面。

**这不是程序入口。** 界面上每个按钮都打到 :8000 的 REST 接口，所以要跑的是

    uv run python -m app.api.api_main        然后开 http://127.0.0.1:8000/ui

它会把这个页面挂在 /ui 上，接口和界面同一个进程。

单独跑本文件只起 gradio、不起接口，一点按钮就是 ConnectError。只在「接口已经
由另一个进程起着，我只想改界面」时才这么用。
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import gradio as gr

from app.ui_present.tabs.ppt_tab import PptTab
from app.ui_present.tabs.video_tab import VideoTab
from config.settings import ServerConfig, use_utf8_output


class PresentationUI:
    """页面。所有按钮都打到 REST 接口，界面自己不存任何状态。

    两个 tab 各管一半，跟 /api/ppt 和 /api/video 两个 blueprint 一一对应。
    """

    TITLE = "放映控制"

    def __init__(self) -> None:
        self.ppt_tab = PptTab()
        self.video_tab = VideoTab()

    def build(self) -> gr.Blocks:
        with gr.Blocks(title=self.TITLE) as page:
            gr.Markdown(f"# {self.TITLE}")
            with gr.Tab(PptTab.LABEL):
                self.ppt_tab.build()
            with gr.Tab(VideoTab.LABEL):
                self.video_tab.build()

            self.ppt_tab.wire()
            self.video_tab.wire()

            # 打开页面时各问一次状态。两个 tab 的屏幕下拉框都要等接口起来才能填。
            page.load(self.ppt_tab.load,
                      outputs=[self.ppt_tab.info, self.ppt_tab.monitor_choice])
            page.load(self.video_tab.load,
                      outputs=[self.video_tab.info, self.video_tab.monitor_choice])
        return page


def main() -> None:
    use_utf8_output()
    print(f"注意：本文件只起界面，不起接口。按钮会打到 {ServerConfig.BASE_URL}"
          f"{ServerConfig.API_PREFIX}，那个服务没起着的话点了就是 ConnectError。")
    print(f"正常启动请用: uv run python -m app.api.api_main"
          f"（界面在 {ServerConfig.BASE_URL}{ServerConfig.UI_PATH}）\n")
    PresentationUI().build().launch()


if __name__ == "__main__":
    main()
