"""程序入口：机器人用的 REST 接口，外加挂在同一个进程上的网页界面。

    uv run python -m app.api.api_main

    http://127.0.0.1:8000/ui        人用的翻页面板
    http://127.0.0.1:8000/api/*     机器人用的接口
    http://127.0.0.1:8000/docs      接口文档，可以直接点着试

两个调用方打的是同一套路由、同一个 PowerPoint 进程，页码都从
View.CurrentShowPosition 读，所以谁翻的另一边刷新就能看到。

端点全部写成同步 def：COM 调用是阻塞的，交给 FastAPI 的线程池跑，不占事件循环。
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

from app.api.context import presentation_context
from app.api.schemas import GotoRequest, Monitor, MonitorRequest, ScreenRequest, Status
from app.ui_present.ui_main import PresentationUI
from config.settings import ServerConfig, use_utf8_output


class PresentationAPI:
    """路由本身不含业务判断，一律转发给 presentation_context。"""

    TITLE = "Concierge Presentation"

    def build(self) -> FastAPI:
        api = FastAPI(title=self.TITLE, description="控制一份固定的 PowerPoint 放映")
        prefix = ServerConfig.API_PREFIX

        @api.get(f"{prefix}/status", response_model=Status, summary="当前状态")
        def status() -> dict:
            return presentation_context.status()

        @api.post(f"{prefix}/show", response_model=Status, summary="开始放映")
        def show() -> dict:
            return presentation_context.show()

        @api.post(f"{prefix}/stop", response_model=Status, summary="结束放映")
        def stop() -> dict:
            return presentation_context.stop()

        @api.post(f"{prefix}/next", response_model=Status, summary="下一页")
        def next_slide() -> dict:
            return presentation_context.next()

        @api.post(f"{prefix}/next-slide", response_model=Status,
                  summary="下一张幻灯片（跳过页内动画）")
        def next_slide() -> dict:
            return presentation_context.next_slide()

        @api.post(f"{prefix}/previous", response_model=Status, summary="上一步")
        def previous() -> dict:
            return presentation_context.previous()

        @api.post(f"{prefix}/previous-slide", response_model=Status,
                  summary="上一张幻灯片（跳过页内动画）")
        def previous_slide() -> dict:
            return presentation_context.previous_slide()

        @api.post(f"{prefix}/goto", response_model=Status, summary="跳到指定页")
        def goto(request: GotoRequest) -> dict:
            return presentation_context.goto(request.slide)

        @api.post(f"{prefix}/screen", response_model=Status, summary="黑屏 / 白屏 / 恢复")
        def screen(request: ScreenRequest) -> dict:
            return presentation_context.screen(request.mode)

        @api.post(f"{prefix}/focus", response_model=Status, summary="把放映提到最前面")
        def focus() -> dict:
            return presentation_context.focus()

        @api.get(f"{prefix}/monitors", response_model=list[Monitor], summary="有几块屏")
        def monitors() -> list[dict]:
            return presentation_context.monitors()

        @api.post(f"{prefix}/monitor", response_model=Status, summary="投到指定的屏")
        def monitor(request: MonitorRequest) -> dict:
            return presentation_context.move(request.index)

        return api

    def serve(self) -> None:
        api = gr.mount_gradio_app(
            self.build(), PresentationUI().build(), path=ServerConfig.UI_PATH
        )
        print(f"ppt:  {presentation_context.deck}")
        print(f"界面: {ServerConfig.BASE_URL}{ServerConfig.UI_PATH}")
        print(f"接口: {ServerConfig.BASE_URL}/docs")
        uvicorn.run(api, host=ServerConfig.HOST, port=ServerConfig.PORT)


def main() -> None:
    use_utf8_output()
    PresentationAPI().serve()


if __name__ == "__main__":
    main()
