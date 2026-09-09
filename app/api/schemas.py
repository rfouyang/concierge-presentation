"""REST 接口的出入参。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Status(BaseModel):
    """所有接口的统一返回。写操作也返回它，省掉一次 GET。"""

    deck: str = Field(description="正在控制的 ppt 文件名")
    slide: int = Field(description="当前页码，没在放映时为 0")
    total: int = Field(description="总页数，ppt 没打开时为 0")
    playing: bool = Field(description="是否正在放映")
    monitor: int = Field(description="放映在第几块屏，没在放映时为 0")


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
