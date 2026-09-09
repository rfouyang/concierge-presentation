"""REST 接口的 Python 客户端。

网页界面用它，机器人那边也可以直接抄。放在路由旁边而不是 util，是因为它是
这套端点的镜像 —— 加一个端点就得改这里，两个文件必须一起动。

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


class PresentationClient:
    """每个方法对应一个端点，返回值都是那个统一的 status dict。"""

    def __init__(self, **kwargs) -> None:
        self.base_url = kwargs.get("base_url", ServerConfig.BASE_URL)
        self.prefix = kwargs.get("prefix", ServerConfig.API_PREFIX)
        self.timeout = kwargs.get("timeout", ServerConfig.TIMEOUT)

    def _url(self, path: str) -> str:
        return f"{self.base_url}{self.prefix}{path}"

    def _get(self, path: str) -> dict:
        return httpx.get(self._url(path), timeout=self.timeout).json()

    def _post(self, path: str, payload: dict | None = None) -> dict:
        return httpx.post(self._url(path), json=payload, timeout=self.timeout).json()

    def status(self) -> dict:
        return self._get("/status")

    def show(self) -> dict:
        return self._post("/show")

    def stop(self) -> dict:
        return self._post("/stop")

    def next(self) -> dict:
        return self._post("/next")

    def previous(self) -> dict:
        return self._post("/previous")

    def goto(self, slide: int) -> dict:
        return self._post("/goto", {"slide": slide})

    def screen(self, mode: str) -> dict:
        return self._post("/screen", {"mode": mode})

    def focus(self) -> dict:
        return self._post("/focus")

    def monitors(self) -> list[dict]:
        return self._get("/monitors")

    def move(self, index: int) -> dict:
        return self._post("/monitor", {"index": index})


def demo_client() -> None:
    """对着已经起着的服务走一遍：放映 -> 翻页 -> 跳转 -> 结束。"""
    import time

    client = PresentationClient()
    print(f"连 {client.base_url}")
    print("屏幕:", client.monitors())
    print("当前状态:", client.status())

    print("开始放映:", client.show())
    time.sleep(2)
    print("下一页:", client.next())
    time.sleep(2)
    print("上一页:", client.previous())
    time.sleep(2)
    print("跳到第 2 页:", client.goto(2))
    time.sleep(2)
    print("结束放映:", client.stop())


def main() -> None:
    use_utf8_output()
    demo_client()


if __name__ == "__main__":
    main()
