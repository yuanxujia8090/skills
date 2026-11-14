#!/usr/bin/env python3
"""圆点封面与分享卡配图（风格2） · 本地 ComfyUI (Qwen-Image 2.1) 生成器

用法:
  python3 generate.py "scene: the man ... (英文画面描述)" \
      --labels "实测@0.06,0.80" --labels "通过@0.72,0.18,#d35400" \
      --out-dir <dir> --name 01-topic [--ref vision|latent|none] [--seed N]

- **文字默认不进模型**：模型只画画面（零乱码），批注由 add_labels.py 用本机楷体叠到图上。
  需要坐标（x,y 归一化）；不给坐标时要加 --auto 自动找空白。
- 想回到「让模型自己写字」的旧行为：--model-labels "实测/通过"（乱码率高，仅作对比）。
- 默认把 assets/可用版V1.jpg 作为参考图喂给 TextEncodeQwenImage21（本地版"改图锁形象"）。
  --ref vision : 只让视觉编码器看设定卡（语义参考，构图自由）
  --ref latent : 视觉 + VAE 潜变量（贴原图更紧，易把设定卡构图带进来）
  --ref none   : 纯文生图（形象最容易漂）
- 端口自动探测 8000(Desktop) -> 8188；后端不在线直接退出，不自己起实例。
- 输出: stdout 最后一行 JSON {path, seconds, seed, ref, port}
"""
import argparse, json, mimetypes, os, shutil, subprocess, sys, time, uuid, urllib.request, urllib.error
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
REF_IMAGE = SKILL_DIR / "assets" / "可用版V1.jpg"

MODELS = {
    "unet": "qwen_image_2.1_int8_convrot.safetensors",
    "clip": "qwen3vl_8b_int8_convrot.safetensors",
    "vae": "qwen_image_2.1_vae_bf16.safetensors",
}
MODEL_ROOT = os.path.expanduser(os.environ.get("COMFYUI_MODEL_ROOT", "~/ComfyUI/models"))
# 通过 /view 下载，不依赖后端输出目录的本地位置。
COMFY_OUTPUT = ""  # 兼容历史引用；取图不使用此变量
DEFAULT_OUT = os.path.expanduser(os.environ.get("COMFYUI_OUTPUT_DIR", "~/Pictures/comfyui-output"))

# 风格 + 身份前缀（角色不写中文名，见 SKILL.md 坑⑦）；画法=风格2 手绘带标注（2026-11-13）
POS_STYLE = (
    "One standalone Chinese cover illustration, flat 2D storybook-infographic look. "
    "Hand-drawn marker-and-watercolor style on warm off-white paper (#F5F0E6) with subtle paper grain. "
    "Thin imperfect ink linework (#1A1A1A), light flat watercolor fill. "
    "Only three accent colors: ink black, burnt orange (#E8552D), navy (#1F3A5F). "
    "Playful but tidy, generous negative space. "
    "The SCENE OBJECTS AND STRUCTURE carry the meaning and occupy 40-60% of the canvas; "
    "the character is only one small actor inside that scene. "
    "Single clear structure: one core action, 3 to 5 main objects, no dense node network. "
    "Leave a few small clean blank pockets around the objects where handwritten labels can sit later. "
    "No 3D, no photorealism, no glossy highlights, no gradients, no stock clip-art look, "
    "not commercial flat vector, not PPT infographic, not cute chibi. "
)
POS_SIZE = (
    "Character scale: the man appears EXACTLY ONCE in the whole picture, as a small but clearly readable "
    "full-body figure about 20-25% of the image height (roughly a quarter), seen from a distance, "
    "never a portrait, never a close-up, never a headshot. The objects around him are bigger than he is "
    "and carry the meaning; he is one working part of the scene. "
)
POS_IDENTITY_REF = (
    "The reference picture is ONLY a character design sheet; do not copy its layout, "
    "do not draw multiple views of him, do not reproduce any text from it. "
    "Draw the SAME man from the reference: East Asian man, short hair, calm focused face, simplified features, "
    "normal body proportion about 1:4 head-to-body (not big-head chibi), "
    "black baseball cap with ONE solid RED five-pointed star on the front, "
    "DARK NAVY quilted puffer jacket, black inner shirt, black pants, white shoes. "
)
POS_IDENTITY_TXT = (
    "Main character: East Asian man, short hair, calm focused face, simplified features, "
    "normal body proportion about 1:4 (not chibi), black baseball cap with ONE solid RED five-pointed star on the front, "
    "DARK NAVY quilted puffer jacket, black inner shirt, black pants, white shoes. "
)
NEG = (
    "red circle logo on cap, red dot on cap, yellow star, light blue jacket, sky blue jacket, "
    "anime handsome face, glossy anime, cel shading, 3d render, realistic photo, chibi, big head, cute mascot, "
    "PPT slide, flowchart title, infographic, dense diagram, gradient sky, cyberpunk UI, "
    "colored pencil hatching, graphite shading, pencil texture, heavy shadow, gradient fill, "
    "stock clip-art look, glossy highlights, "
    "Japanese flag, white flag with red circle, wrong chinese characters, random characters, gibberish text, "
    "extra handwritten text, title in top-left corner, signature, watermark, character name written as text, "
    "multiple copies of the character, the same man repeated, character sheet, three views, turnaround, "
    "multiple panels, comic strip panels, portrait, close-up of the face, headshot, giant character "
)


def pick_port(port):
    for p in ([port] if port else [8000, 8188]):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{p}/system_stats", timeout=2)
            return p
        except Exception:
            continue
    sys.exit("后端未启动: 请打开 ComfyUI Desktop 并保持实例运行（agent 不要自己起后端）")


def check_models():
    sub = {"unet": "diffusion_models", "clip": "text_encoders", "vae": "vae"}
    for k, name in MODELS.items():
        p = os.path.join(MODEL_ROOT, sub[k], name)
        if not os.path.exists(p):
            sys.exit(f"缺模型: {p}")


def upload_ref(port, path: Path) -> str:
    """POST /upload/image (multipart)，返回 ComfyUI input 目录里的文件名。"""
    boundary = uuid.uuid4().hex
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    # 用 ASCII 文件名，避免中文名在 multipart / LoadImage 里出问题
    fname = "yuandian_ref_v1" + path.suffix.lower()
    body = b"".join([
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{fname}\"\r\n"
        f"Content-Type: {mime}\r\n\r\n".encode(), path.read_bytes(), b"\r\n",
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n".encode(),
        f"--{boundary}--\r\n".encode(),
    ])
    req = urllib.request.Request(f"http://127.0.0.1:{port}/upload/image", data=body,
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=30))
    except urllib.error.HTTPError as e:
        sys.exit("参考图上传失败: " + e.read().decode()[:300])
    return (r.get("subfolder") + "/" if r.get("subfolder") else "") + r["name"]


def build(prompt, seed, prefix, ref_name, ref_mode, w, h, steps):
    enc = {"clip": ["2", 0], "prompt": prompt, "negative_prompt": NEG, "resolution": 1024}
    g = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": MODELS["unet"], "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": MODELS["clip"], "type": "qwen_image", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": MODELS["vae"]}},
        "4": {"class_type": "TextEncodeQwenImage21", "inputs": enc},
        "6": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "7": {"class_type": "KSampler", "inputs": {
            "model": ["1", 0], "positive": ["4", 0], "negative": ["4", 1], "latent_image": ["6", 0],
            "seed": seed, "steps": steps, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}},
        "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": prefix}},
    }
    if ref_mode != "none":
        g["10"] = {"class_type": "LoadImage", "inputs": {"image": ref_name}}
        enc["images.image_1"] = ["10", 0]
        if ref_mode == "latent":
            enc["vae"] = ["3", 0]
    return g


def fetch_image(port, img, dest):
    """GET /view 把图下载到本地路径；不依赖 ComfyUI 的输出目录在哪。"""
    from urllib.parse import urlencode
    q = urlencode({"filename": img["filename"],
                   "subfolder": img.get("subfolder", ""),
                   "type": img.get("type", "output")})
    try:
        data = urllib.request.urlopen(f"http://127.0.0.1:{port}/view?{q}", timeout=120).read()
    except urllib.error.HTTPError as e:
        sys.exit("取图失败: " + e.read().decode(errors="replace")[:300])
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return dest


def run_once(port, graph, timeout=900):
    data = json.dumps({"prompt": graph, "client_id": uuid.uuid4().hex}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}/prompt", data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        pid = json.load(urllib.request.urlopen(req, timeout=15))["prompt_id"]
    except urllib.error.HTTPError as e:
        sys.exit("提交失败: " + e.read().decode()[:600])
    print(f"prompt_id={pid}", flush=True)
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(5)
        try:
            h = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/history/{pid}", timeout=10))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            sys.exit(f"查询任务 {pid} 失败: {e}；未重新提交，请先检查原任务状态")
        if pid not in h:
            continue
        st = h[pid].get("status", {})
        if st.get("status_str") == "success":
            img = h[pid]["outputs"]["9"]["images"][0]
            return img, time.time() - t0
        if st.get("completed") is False or st.get("status_str") == "error":
            return None, json.dumps(st, ensure_ascii=False)[:400]
    return None, "超时"


def main():
    global MODEL_ROOT
    ap = argparse.ArgumentParser()
    ap.add_argument("scene", help="英文画面描述：the man does X; 隐喻物件; 构图。勿写中文角色名")
    ap.add_argument("--labels", action="append", default=[],
                    help="叠字批注：文字@x,y[,颜色[,字号%%,[旋转°]]]；可重复，多个用 ; 分隔")
    ap.add_argument("--model-labels", default="",
                    help="旧行为：让模型自己写这些字（/ 分隔）。乱码率高，仅作对比/英文场景")
    ap.add_argument("--auto-label", action="store_true", help="叠字时未给坐标则自动找空白（有风险）")
    ap.add_argument("--font", default="kaiti", help="叠字字体: kaiti/hannotate/xingkai/yuang/heiti/song")
    ap.add_argument("--robot", action="store_true", help="加入白色圆形小机器人（脸屏红五角星）")
    ap.add_argument("--no-person", action="store_true", help="不画人：结构自己说得清时（漏斗/闸门/秤/抽屉分层/路线）")
    ap.add_argument("--ref", choices=["vision", "latent", "none"], default=None,
                    help="默认 vision；--no-person 时默认 none（参考图会把人物带进画面）")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--steps", type=int, default=25)
    ap.add_argument("--width", type=int, default=1536)
    ap.add_argument("--height", type=int, default=1024)
    ap.add_argument("--port", type=int)
    ap.add_argument("--model-root", default=MODEL_ROOT, help="模型目录，默认读取 COMFYUI_MODEL_ROOT")
    ap.add_argument("--ref-image", type=Path, default=REF_IMAGE, help="角色参考图路径")
    ap.add_argument("--retries", type=int, default=0, help="显式允许的失败重试次数，默认不自动重试")
    ap.add_argument("--keep-loaded", action="store_true",
                    help="生成完不卸载模型（连续出多张时用，省重载时间；整批结束后手动跑 free_comfy.py）")
    ap.add_argument("--out-dir", help=f"默认 {DEFAULT_OUT}/<YYYYMMDDHHMM>")
    ap.add_argument("--name", default="yuandian", help="输出文件名（不含扩展名），如 01-topic")
    a = ap.parse_args()
    if not a.ref:
        a.ref = "none" if a.no_person else "vision"

    MODEL_ROOT = str(Path(a.model_root).expanduser())
    ref_path = a.ref_image.expanduser()
    if a.ref != "none" and not ref_path.is_file():
        sys.exit(f"参考图不存在: {ref_path}（可用 --ref-image 指定，或 --ref none 不用参考图）")
    port = pick_port(a.port)
    check_models()
    ref_name = upload_ref(port, ref_path) if a.ref != "none" else None

    # 归一化 labels：支持 "实测@0.1,0.8" 与旧的 "实测/通过" 写法（后者拆开并自动选位）
    label_specs = []
    for raw in a.labels:
        for chunk in raw.split(";"):
            chunk = chunk.strip()
            if not chunk:
                continue
            if "@" not in chunk and "/" in chunk:
                label_specs.extend(x.strip() for x in chunk.split("/") if x.strip())
            else:
                label_specs.append(chunk)
    model_labs = [x.strip() for x in a.model_labels.split("/") if x.strip()][:4]
    if a.no_person:
        pos = POS_STYLE
        pos += ("No people at all in the picture: the objects and the single structure alone carry the meaning. "
                "Scene: " + a.scene.strip() + " ")
    else:
        pos = POS_STYLE + POS_SIZE + (POS_IDENTITY_TXT if a.ref == "none" else POS_IDENTITY_REF)
        if a.robot:
            pos += "Optional sidekick: a tiny round white robot with ONE solid RED five-pointed star on its face screen. "
        pos += ("The man performs one core action of the scene, not standing aside as decoration, "
                "but he must stay smaller than the objects. Scene: " + a.scene.strip() + " ")
    pos += "Colors: black line art; dark navy only for the jacket; red for the stars and key notes; orange for flow arrows; light blue optional for secondary notes. "
    if model_labs:
        pos += ("Sparse handwritten Chinese labels. The ONLY text allowed in the image is: "
                + " / ".join(f"'{l}'" for l in model_labs) + ". ")
        pos += "Absolutely no other letters, characters, scribbles, titles or signatures anywhere."
    else:
        # 文字由 add_labels.py 后期叠加 → 模型画面里必须绝对无字
        pos += ("The image must contain NO text at all: no letters, no Chinese characters, no numbers, "
                "no labels, no titles, no signature, no watermark, no caption anywhere. Leave clean blank areas for later annotation.")

    stamp = time.strftime("%Y%m%d%H%M")
    out_dir = Path(a.out_dir or f"{DEFAULT_OUT}/{stamp}")
    out_dir.mkdir(parents=True, exist_ok=True)
    seed = a.seed if a.seed is not None else int(time.time()) % 10**9

    # 默认让后端在这次生成结束后卸载模型（flag 在任务结束时才被处理，所以提交前设）
    if not a.keep_loaded:
        try:
            body = json.dumps({"unload_models": True}).encode()
            req = urllib.request.Request(f"http://127.0.0.1:{port}/free", data=body,
                                         headers={"Content-Type": "application/json"}, method="POST")
            urllib.request.urlopen(req, timeout=10).read()
            print("unload-after-run=on", flush=True)
        except Exception as e:
            print(f"WARN 设置卸载标记失败: {e}", flush=True)

    for attempt in range(a.retries + 1):
        graph = build(pos, seed, f"yuandian/{stamp}/{a.name}", ref_name, a.ref, a.width, a.height, a.steps)
        print(f"submit port={port} seed={seed} ref={a.ref} try={attempt + 1}", flush=True)
        img, info = run_once(port, graph)
        if img:
            dst = out_dir / f"{a.name}.png"
            if dst.exists():
                dst = out_dir / f"{a.name}-s{seed}.png"
            fetch_image(port, img, dst)
            raw_copy = Path(str(dst) + ".notext.png")
            if not isinstance(info, (int, float)):
                sys.exit(f"生成耗时格式错误: {info}")
            result = {"path": str(dst), "seconds": round(info), "seed": seed, "ref": a.ref,
                      "port": port, "model_labels": model_labs,
                      "unload_after_run": not a.keep_loaded}
            if label_specs:
                shutil.copy2(dst, raw_copy)
                cmd = [sys.executable, str(SKILL_DIR / "scripts" / "add_labels.py"), str(dst),
                       "--out", str(dst), "--font", a.font]
                for spec in label_specs:
                    cmd += ["--label", spec]
                if a.auto_label or any("@" not in s for s in label_specs):
                    cmd.append("--auto")
                r = subprocess.run(cmd, capture_output=True, text=True)
                if r.returncode != 0:
                    print(r.stderr.strip()[:400], file=sys.stderr, flush=True)
                    shutil.copy2(raw_copy, dst)
                    result["labels_error"] = "叠字失败，已保留无字原图"
                else:
                    try:
                        result["labels"] = json.loads(r.stdout.strip().splitlines()[-1])
                    except (json.JSONDecodeError, IndexError) as e:
                        sys.exit(f"叠字结果无法解析: {e}（底图保留于 {raw_copy}）")
                    result["raw_no_text"] = str(raw_copy)
            print(json.dumps(result, ensure_ascii=False))
            return
        print(f"WARN 失败: {info}", flush=True)
        seed = (seed + 7919) % 10**9
    sys.exit("生成失败，已用尽重试")


if __name__ == "__main__":
    main()
