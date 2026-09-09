"""REST 接口的 Python 客户端。

网页界面用它，机器人那边也可以直接抄。放在路由旁边而不是 util，是因为它是这两套
端点的镜像 —— 加一个端点就得改这里，文件必须一起动。

    uv run python -m app.api.client        # 需要服务已经起着
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import httpx

from config.settings import ServerConfig, use_utf8_output


class ApiClient:
    """管 HTTP 那点事。两个子客户端各自只写自己的路径。"""

    PREFIX = ""

    def __init__(self, **kwargs) -> None:
        self.base_url = kwargs.get("base_url", ServerConfig.BASE_URL)
        self.timeout = kwargs.get("timeout", ServerConfig.TIMEOUT)

    def _url(self, path: str) -> str:
        return f"{self.base_url}{self.PREFIX}{path}"

    def _get(self, path: str):
        return httpx.get(self._url(path), timeout=self.timeout).json()

    def _post(self, path: str, payload: dict | None = None) -> dict:
        return httpx.post(self._url(path), json=payload, timeout=self.timeout).json()

    def monitors(self) -> list[dict]:
        """共用端点，不带 blueprint 前缀。"""
        return httpx.get(f"{self.base_url}/api/monitors", timeout=self.timeout).json()


class PptClient(ApiClient):
    """幻灯片。"""

    PREFIX = "/api/ppt"

    def status(self) -> dict:
        return self._get("/status")

    def show(self) -> dict:
        return self._post("/show")

    def stop(self) -> dict:
        return self._post("/stop")

    def next(self) -> dict:
        return self._post("/next")

    def next_slide(self) -> dict:
        return self._post("/next-slide")

    def previous(self) -> dict:
        return self._post("/previous")

    def previous_slide(self) -> dict:
        return self._post("/previous-slide")

    def goto(self, slide: int) -> dict:
        return self._post("/goto", {"slide": slide})

    def screen(self, mode: str) -> dict:
        return self._post("/screen", {"mode": mode})

    def focus(self) -> dict:
        return self._post("/focus")

    def move(self, index: int) -> dict:
        return self._post("/monitor", {"index": index})


class VideoClient(ApiClient):
    """视频。"""

    PREFIX = "/api/video"

    def status(self) -> dict:
        return self._get("/status")

    def play(self) -> dict:
        return self._post("/play")

    def pause(self) -> dict:
        return self._post("/pause")

    def resume(self) -> dict:
        return self._post("/resume")

    def stop(self) -> dict:
        return self._post("/stop")

    def seek(self, seconds: float) -> dict:
        return self._post("/seek", {"seconds": seconds})

    def focus(self) -> dict:
        return self._post("/focus")

    def move(self, index: int) -> dict:
        return self._post("/monitor", {"index": index})


def demo_client() -> None:
    """对着已经起着的服务走一遍：视频放一段，再切去放 ppt。"""
    import time

    ppt = PptClient()
    video = VideoClient()
    print(f"连 {ppt.base_url}")
    print("屏幕:", ppt.monitors())

    print("\n--- 先放视频 ---")
    print("play: ", video.play())
    time.sleep(3)
    print("pause:", video.pause())
    print("seek: ", video.seek(10))
    print("resume:", video.resume())
    time.sleep(2)

    print("\n--- 再切去放 ppt（视频应被自动关掉）---")
    print("show:  ", ppt.show())
    print("video: ", video.status())
    print("next:  ", ppt.next_slide())
    time.sleep(2)
    print("stop:  ", ppt.stop())


def main() -> None:
    use_utf8_output()
    demo_client()


if __name__ == "__main__":
    main()
