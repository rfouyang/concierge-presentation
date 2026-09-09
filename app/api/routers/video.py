"""视频的路由，全部挂在 /api/video 下。

和 ppt 那边同样的形状：转发给 stage.video，play 走 stage.play_video() 以便先把
ppt 的放映退掉。
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi import APIRouter

from app.api.context import stage
from app.api.schemas import MonitorRequest, SeekRequest, VideoStatus

router = APIRouter(prefix="/api/video", tags=["视频"])


@router.get("/status", response_model=VideoStatus, summary="当前状态")
def status() -> dict:
    return stage.video.status()


@router.post("/play", response_model=VideoStatus, summary="从头播（会先关掉 ppt 放映）")
def play() -> dict:
    return stage.play_video()


@router.post("/pause", response_model=VideoStatus, summary="暂停")
def pause() -> dict:
    return stage.video.pause()


@router.post("/resume", response_model=VideoStatus, summary="继续")
def resume() -> dict:
    return stage.video.resume()


@router.post("/stop", response_model=VideoStatus, summary="停止并关掉播放窗口")
def stop() -> dict:
    return stage.video.stop()


@router.post("/seek", response_model=VideoStatus, summary="定位到第几秒")
def seek(request: SeekRequest) -> dict:
    return stage.video.seek(request.seconds)


@router.post("/focus", response_model=VideoStatus, summary="把播放窗口提到最前面")
def focus() -> dict:
    return stage.video.focus()


@router.post("/monitor", response_model=VideoStatus, summary="投到指定的屏")
def monitor(request: MonitorRequest) -> dict:
    return stage.video.move(request.index)
