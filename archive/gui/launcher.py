# -*- coding: utf-8 -*-
"""
launcher.py — exe 打包入口（PyInstaller --noconsole）
双击 exe → 本机启动诊断网页并自动打开浏览器；关闭终端窗口即退出。
再次双击：若已有实例在运行，直接打开浏览器复用，不启动第二个实例。
"""
import sys
import threading
import urllib.request
import webbrowser
from http.server import ThreadingHTTPServer

import webapp


class NoReuseServer(ThreadingHTTPServer):
    # Windows 下默认的 SO_REUSEADDR 会允许多个进程绑同一端口（端口劫持），
    # 导致多次双击 exe 出现多个实例抢答同一端口、页面请求挂起。这里显式关闭。
    allow_reuse_address = False


def _alive_port() -> int | None:
    """探测 8501-8510 是否已有本工具的实例在服务（绕过系统代理，直连本机）。"""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for p in range(8501, 8511):
        try:
            with opener.open(f"http://127.0.0.1:{p}/api/status", timeout=1) as r:
                if r.status == 200:
                    return p
        except Exception:  # noqa: BLE001
            continue
    return None


def main() -> None:
    # 已有实例：直接打开浏览器复用，本进程退出
    alive = _alive_port()
    if alive:
        webbrowser.open(f"http://127.0.0.1:{alive}")
        return

    port = 8501
    # 端口被占用时依次向后尝试
    srv = None
    for p in range(port, port + 10):
        try:
            srv = NoReuseServer(("127.0.0.1", p), webapp.make_handler())
            port = p
            break
        except OSError:
            continue
    if srv is None:
        sys.exit("无可用端口（8501-8510 均被占用）")

    url = f"http://127.0.0.1:{port}"
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
