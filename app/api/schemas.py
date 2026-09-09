"""REST 接口的出入参。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PptStatus(BaseModel):
    """幻灯片那半边的统一返回。写操作也返回它，省掉一次 GET。"""

    deck: str = Field(description="正在控制的 ppt 文件名")
    slide: int = Field(description="当前页码，没在放映时为 0")
    total: int = Field(description="总页数，ppt 没打开时为 0")
    playing: bool = Field(description="是否正在放映")
    monitor: int = Field(description="放映在第几块屏，没在放映时为 0")
    foreground: bool = Field(description="放映窗口是否在最前面（没被别的窗口盖住）")


class VideoStatus(BaseModel):
    """视频那半边的统一返回。

    running 和 playing 是两件事：mpv 常驻，播完或暂停时窗口还在但画面不动。
    """

    video: str = Field(description="正在控制的视频文件名")
    running: bool = Field(description="mpv 是否起着（窗口开着）")
    playing: bool = Field(description="是否正在放（没暂停、没播完）")
    paused: bool = Field(description="是否暂停")
    finished: bool = Field(description="是否已播完，停在最后一帧")
    position: float = Field(description="播到第几秒")
    duration: float = Field(description="视频总长，秒")
    monitor: int = Field(description="播在第几块屏，mpv 没起时为 0")
    foreground: bool = Field(description="播放窗口是否在最前面")


class Monitor(BaseModel):
    index: int = Field(description="屏幕编号，从 1 开始")
    width: int = Field(description="像素宽")
    height: int = Field(description="像素高")
    primary: bool = Field(description="是不是主屏")


class GotoRequest(BaseModel):
    slide: int = Field(description="要跳到的页码，从 1 开始")


class ScreenRequest(BaseModel):
    mode: str = Field(description="normal / black / white")


class MonitorRequest(BaseModel):
    index: int = Field(description="要投到第几块屏，编号取自 /api/monitors")


class SeekRequest(BaseModel):
    seconds: float = Field(description="绝对定位到第几秒")
