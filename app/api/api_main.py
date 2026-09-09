"""程序入口：机器人用的 REST 接口，外加挂在同一个进程上的网页界面。

    uv run python -m app.api.api_main

    http://127.0.0.1:8000/ui        人用的面板（幻灯片 / 视频两个 tab）
    http://127.0.0.1:8000/api/ppt/*     幻灯片
    http://127.0.0.1:8000/api/video/*   视频
    http://127.0.0.1:8000/docs      接口文档，可以直接点着试

两个调用方打的是同一套路由、同一个 PowerPoint 和同一个 mpv，所以谁翻的页、谁按的
暂停，另一边刷新就能看到。

端点全部写成同步 def：COM 调用和管道读写都是阻塞的，交给 FastAPI 的线程池跑，
不占事件循环。
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import gradio as gr
import uvicorn
from fastapi import FastAPI

from app.api.context import stage
from app.api.routers import ppt, video
from app.api.schemas import Monitor
from app.ui_present.ui_main import PresentationUI
from config.settings import ServerConfig, use_utf8_output


class PresentationAPI:
    """两个 blueprint 各管一半，只有「有几块屏」是共用的，留在顶层。"""

    TITLE = "Concierge Presentation"

    def build(self) -> FastAPI:
        api = FastAPI(title=self.TITLE, description="控制一份固定的 ppt 和一个固定的视频")
        api.include_router(ppt.router)
        api.include_router(video.router)

        @api.get(f"{ServerConfig.API_PREFIX}/monitors", response_model=list[Monitor],
                 tags=["共用"], summary="有几块屏")
        def monitors() -> list[dict]:
            return stage.monitors()

        return api

    def serve(self) -> None:
        api = gr.mount_gradio_app(
            self.build(), PresentationUI().build(), path=ServerConfig.UI_PATH
        )
        print(f"ppt:   {stage.ppt.deck}")
        print(f"视频:  {stage.video.video}")
        print(f"界面:  {ServerConfig.BASE_URL}{ServerConfig.UI_PATH}")
        print(f"接口:  {ServerConfig.BASE_URL}/docs")
        uvicorn.run(api, host=ServerConfig.HOST, port=ServerConfig.PORT)


def main() -> None:
    use_utf8_output()
    PresentationAPI().serve()


if __name__ == "__main__":
    main()
