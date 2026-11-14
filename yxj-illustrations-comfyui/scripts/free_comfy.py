#!/usr/bin/env python3
"""给 ComfyUI 设「用完卸载模型」标记。

原理：POST /free 只是设置标记，真正 unload_all_models() 发生在「下一个任务执行完之后」。
所以：**在提交生成任务之前跑它**，生成结束就会自动卸载。
后端空闲时单独跑，标记会一直留着，等下次任务结束才生效。

安全注意：只设 unload_models，不设 free_memory（后者会执行 e.reset()，
2026-11-07 实测用「额外轻任务触发」的方式把后端搞挂过，已移除该做法）。
本脚本不会关闭 ComfyUI 进程。要彻底回收内存，用 --stop-backend 或手动退出 Desktop。

用法:
  python3 free_comfy.py                 # 卸载并打印释放前后
  python3 free_comfy.py --quiet         # 只做，不打印
  python3 free_comfy.py --port 8188
  python3 free_comfy.py --stop-backend  # 额外尝试关闭 ComfyUI Desktop 实例（危险，默认不做）

注意: 只卸载模型权重，不会关闭 ComfyUI 进程本身（Desktop App 仍在前台）。
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

PORT_CANDIDATES = (8000, 8188)
# 已上传到 ComfyUI input/ 的参考图；没有就用任意存在的图片兜底
REF_CANDIDATES = ["yuandian_ref_v1.jpg", "example.png", "ComfyUI_00001_.png"]


def pick_port(explicit=None):
    for p in ([explicit] if explicit else PORT_CANDIDATES):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{p}/system_stats", timeout=2)
            return p
        except Exception:
            continue
    return None


def stats(port):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/system_stats", timeout=5) as r:
            d = json.loads(r.read().decode())
        out = {}
        for dev in d.get("devices", []):
            out[dev.get("name", "dev")] = (dev.get("vram_free", 0), dev.get("vram_total", 0))
        return out
    except Exception:
        return {}


def free_flag(port):
    body = json.dumps({"unload_models": True}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}/free", data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.status


def find_input_image(port):
    """挑一张后端 input 目录里确实存在的图，避免轻任务校验失败。"""
    for name in REF_CANDIDATES:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/view?filename={name}", timeout=3) as r:
                if r.status == 200:
                    return name
        except Exception:
            continue
    # 列 input 目录
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/object_info/LoadImage", timeout=5) as r:
            d = json.loads(r.read().decode())
        items = d["LoadImage"]["input"]["required"]["image"][0]
        if items:
            return items[0]
    except Exception:
        pass
    return None


def trigger(port, image):
    """提交一个不加载扩散模型的轻任务，触发 flag 处理。"""
    graph = {
        "1": {"class_type": "LoadImage", "inputs": {"image": image}},
        "2": {"class_type": "PreviewImage", "inputs": {"images": ["1", 0]}},
    }
    body = json.dumps({"prompt": graph, "client_id": uuid.uuid4().hex}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}/prompt", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        pid = json.load(urllib.request.urlopen(req, timeout=15))["prompt_id"]
    except urllib.error.HTTPError as e:
        return None, e.read().decode()[:300]
    t0 = time.time()
    while time.time() - t0 < 60:
        time.sleep(1)
        try:
            h = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/history/{pid}", timeout=5))
        except Exception:
            continue
        if pid in h:
            return pid, None
    return None, "轻任务 60s 未完成"


def stop_backend(port):
    """尝试结束监听该端口的进程（Desktop 会自己重启，慎用）。"""
    try:
        out = subprocess.run(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
                             capture_output=True, text=True, timeout=10).stdout.split()
    except Exception:
        return False
    killed = False
    for pid in out:
        if pid.isdigit() and int(pid) != os.getpid():
            try:
                os.kill(int(pid), 15)
                killed = True
            except Exception:
                pass
    return killed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int)
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--stop-backend", action="store_true", help="额外尝试结束 ComfyUI 进程（默认不做）")
    a = ap.parse_args()

    port = pick_port(a.port)
    if not port:
        if not a.quiet:
            print(json.dumps({"skipped": "后端未启动"}, ensure_ascii=False))
        return

    before = stats(port)
    free_flag(port)
    after = stats(port)

    if a.stop_backend:
        stop_backend(port)

    result = {
        "port": port,
        "flag_set": True,
        "note": "标记已设置：当前任务结束（或下一次任务结束）时卸载模型",
        "vram_free_now": {k: round(v[0] / 1e9, 1) for k, v in after.items()},
        "stopped_backend": bool(a.stop_backend),
    }
    if not a.quiet:
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
