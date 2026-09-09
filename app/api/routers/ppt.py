"""幻灯片的路由，全部挂在 /api/ppt 下。

路由不含业务判断，一律转发给 stage.ppt；「开始放映要先关掉视频」这条互斥规则在
stage 里，所以 show 走 stage.show_ppt()。
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi import APIRouter

from app.api.context import stage
from app.api.schemas import GotoRequest, MonitorRequest, PptStatus, ScreenRequest

router = APIRouter(prefix="/api/ppt", tags=["幻灯片"])


@router.get("/status", response_model=PptStatus, summary="当前状态")
def status() -> dict:
    return stage.ppt.status()


@router.post("/show", response_model=PptStatus, summary="开始放映（会先关掉视频）")
def show() -> dict:
    return stage.show_ppt()


@router.post("/stop", response_model=PptStatus, summary="结束放映")
def stop() -> dict:
    return stage.ppt.stop()


@router.post("/next", response_model=PptStatus, summary="下一步（含页内动画）")
def next_step() -> dict:
    return stage.ppt.next()


@router.post("/next-slide", response_model=PptStatus, summary="下一张幻灯片（跳过动画）")
def next_slide() -> dict:
    return stage.ppt.next_slide()


@router.post("/previous", response_model=PptStatus, summary="上一步（含页内动画）")
def previous_step() -> dict:
    return stage.ppt.previous()


@router.post("/previous-slide", response_model=PptStatus, summary="上一张幻灯片（跳过动画）")
def previous_slide() -> dict:
    return stage.ppt.previous_slide()


@router.post("/goto", response_model=PptStatus, summary="跳到指定页")
def goto(request: GotoRequest) -> dict:
    return stage.ppt.goto(request.slide)


@router.post("/screen", response_model=PptStatus, summary="黑屏 / 白屏 / 恢复")
def screen(request: ScreenRequest) -> dict:
    return stage.ppt.screen(request.mode)


@router.post("/focus", response_model=PptStatus, summary="把放映提到最前面")
def focus() -> dict:
    return stage.ppt.focus()


@router.post("/monitor", response_model=PptStatus, summary="投到指定的屏")
def monitor(request: MonitorRequest) -> dict:
    return stage.ppt.move(request.index)
