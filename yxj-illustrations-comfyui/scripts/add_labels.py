#!/usr/bin/env python3
"""给圆点配图叠手写风格中文批注（PIL 渲染，零乱码）

模型只负责画面，文字由本脚本落到图上：字体可控、坐标可控、改文案不用重出图（省 3 分钟/张）。

用法:
  python3 add_labels.py in.png --out out.png \
      --label "实测@0.06,0.80,#c0392b" --label "通过@0.72,0.18,#d35400"

--label 格式: 文字@x,y[,颜色[,字号百分比[,旋转度]]]
  x,y 归一化 0-1，指文字左端基线
  颜色默认 #c0392b（红）；字号默认 3.2（占图高百分比）；旋转默认随机 ±2.5°
--auto   不给坐标时自动找空白格放字（有压住主体的风险，建议显式给坐标）
--font   kaiti(默认) | hannotate | xingkai | yuang | heiti | song
"""
import argparse, glob, json, os, random, subprocess, sys

import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FONT_QUERY = {
    "kaiti": ["Kaiti SC", "Kaiti"],
    "hannotate": ["Hannotate SC", "Hannotate"],
    "xingkai": ["Xingkai SC", "Xingkai"],
    "yuang": ["Yuanti SC", "YuanTi SC"],
    "heiti": ["Heiti SC", "PingFang SC"],
    "song": ["Songti SC", "STSong"],
}
FONT_GLOB = {
    "kaiti": ["**/Kaiti.ttc", "**/Supplemental/Songti.ttc"],
    "hannotate": ["**/Hannotate.ttc"],
    "xingkai": ["**/Xingkai.ttc"],
    "yuang": ["**/Yuanti.ttc"],
    "heiti": ["/System/Library/Fonts/STHeiti Medium.ttc"],
    "song": ["**/Songti.ttc"],
}
DEFAULT_COLOR = "#c0392b"


def find_font(name: str) -> str:
    wanted = FONT_QUERY.get(name, FONT_QUERY["kaiti"])
    cmd = ["fc-list", ":lang=zh", "file", "family"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout
    except Exception:
        out = ""
    for line in out.splitlines():
        path = line.split(":", 1)[0].strip()
        if not path or not os.path.exists(path):
            continue
        if any(w in line for w in wanted):
            return path
    bases = ["/System/Library/AssetsV2", "/System/Library/Fonts", "/Library/Fonts", os.path.expanduser("~/Library/Fonts")]
    for pattern in FONT_GLOB.get(name, FONT_GLOB["kaiti"]):
        for base in bases:
            hits = glob.glob(os.path.join(base, pattern), recursive=True)
            if hits:
                return sorted(hits)[0]
    sys.exit(f"找不到字体 {name}，可用: {', '.join(FONT_QUERY)}")


def load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    for idx in range(4):
        try:
            f = ImageFont.truetype(path, size, index=idx)
            if not hasattr(f, "getbbox"):
                continue
            return f
        except Exception:
            continue
    return ImageFont.truetype(path, size)


def parse_label(spec: str):
    parts = [p.strip() for p in spec.split("@")]
    text = parts[0]
    pos = [None, None]
    color, size_pct, rot = DEFAULT_COLOR, None, None
    if len(parts) > 1 and parts[1]:
        xy = [p.strip() for p in parts[1].split(",")]
        pos[0] = float(xy[0]) if xy[0] else None
        pos[1] = float(xy[1]) if len(xy) > 1 and xy[1] else None
        if len(xy) > 2 and xy[2]:
            color = xy[2]
        if len(xy) > 3 and xy[3]:
            size_pct = float(xy[3])
        if len(xy) > 4 and xy[4]:
            rot = float(xy[4])
    return {"text": text, "x": pos[0], "y": pos[1], "color": color, "size": size_pct, "rot": rot}


def _dilate(mask, n):
    m = mask.copy()
    for _ in range(n):
        m2 = m.copy()
        m2[1:, :] |= m[:-1, :]
        m2[:-1, :] |= m[1:, :]
        m2[:, 1:] |= m[:, :-1]
        m2[:, :-1] |= m[:, 1:]
        m = m2
    return m


def _integral(mask):
    return np.pad(np.cumsum(np.cumsum(mask, axis=0), axis=1), ((1, 0), (1, 0)))


def _box_sum(ii, x0, y0, x1, y1):
    """积分图上求矩形和；参数顺序统一为 (x0, y0, x1, y1)。"""
    return int(ii[y1, x1] - ii[y0, x1] - ii[y1, x0] + ii[y0, x0])


def _gap_to_ink(ii, taken_ii, bx, by, tw, th, max_gap=64):
    """框外扩多少像素才碰到笔画；None = 附近没有任何内容。"""
    inner = _box_sum(ii, bx, by, bx + tw, by + th) + _box_sum(taken_ii, bx, by, bx + tw, by + th)
    for g in range(0, max_gap + 1, 2):
        x0, y0, x1, y1 = bx - g, by - g, bx + tw + g, by + th + g
        if x0 < 0 or y0 < 0 or x1 > ii.shape[1] - 1 or y1 > ii.shape[0] - 1:
            return g if g else None
        ring = _box_sum(ii, x0, y0, x1, y1) + _box_sum(taken_ii, x0, y0, x1, y1) - inner
        if ring > 0:
            return g
    return None


def snap_to_ink(gray_np, ii, taken_ii, bx, by, tw, th, radius=260, step=6, gap_min=8, gap_max=28, max_shift=100):
    """把文字框朝最近的笔画推近，停在 gap_min..gap_max 之间；找不到就原样返回。"""
    H, W = gray_np.shape
    best = None
    for dy in range(-radius, radius + 1, step):
        for dx in range(-radius, radius + 1, step):
            d2 = dx * dx + dy * dy
            if d2 > radius * radius or abs(dx) + abs(dy) > max_shift:
                continue
            nb = (bx + dx, by + dy)
            if nb[0] < 6 or nb[1] < 6 or nb[0] + tw > W - 6 or nb[1] + th > H - 6:
                continue
            if _box_sum(ii, nb[0], nb[1], nb[0] + tw, nb[1] + th) > tw * th * 0.01:
                continue
            if _box_sum(taken_ii, nb[0], nb[1], nb[0] + tw, nb[1] + th) > 0:
                continue
            gap = _gap_to_ink(ii, taken_ii, nb[0], nb[1], tw, th)
            if gap is None or not (gap_min <= gap <= gap_max):
                continue
            score = (abs(dx) + abs(dy), -gap)
            if best is None or score < best[0]:
                best = (score, nb)
    return best[1] if best else None


def pick_positions(img: Image.Image, items, mode="near", step=6):
    """给每处批注找落点，返回归一化（左端基线 x, y）。

    near : 环绕画面主体（上/下/左/右/四角），批注贴着内容分布——模拟 xiaohei 的「每个结构一处短标注」
    blank: 只挑最白的整块空白（旧行为，容易离内容很远）
    """
    gray = np.array(img.convert("L"))
    H, W = gray.shape
    ink = gray < 205
    ii = _integral(ink)
    taken = np.zeros_like(ink)

    if mode == "blank":
        slots = blank_slots(img, len(items))
        return [(x + 0.02, y + 0.05) for x, y in slots]

    ys, xs = np.nonzero(ink)
    if len(xs) == 0:
        return [(None, None)] * len(items)
    # 用分位数收窄 bbox，忽略零散小点
    x0b, x1b = int(np.percentile(xs, 2)), int(np.percentile(xs, 98))
    y0b, y1b = int(np.percentile(ys, 2)), int(np.percentile(ys, 98))
    pad = 8

    def clean_box(bx, by, tw, th):
        x1, y1 = bx + tw, by + th
        if bx < 6 or by < 6 or x1 > W - 6 or y1 > H - 6:
            return False
        if _box_sum(ii, bx, by, x1, y1) > tw * th * 0.01:
            return False
        return _box_sum(_integral(taken), bx, by, x1, y1) == 0

    def place(tw, th, order):
        """按优先锚点顺序找干净框。"""
        anchors = [
            ((x0b + x1b) // 2 - tw // 2, y0b - th - pad),        # 上
            ((x0b + x1b) // 2 - tw // 2, y1b + pad),             # 下
            (x0b - tw - pad, (y0b + y1b) // 2 - th // 2),        # 左
            (x1b + pad, (y0b + y1b) // 2 - th // 2),             # 右
            (x0b - tw - pad, y0b),                               # 左上
            (x1b + pad, y0b),                                    # 右上
            (x0b - tw - pad, y1b),                               # 左下
            (x1b + pad, y1b),                                    # 右下
        ]
        for idx in order:
            ax, ay = anchors[idx % len(anchors)]
            for grow in range(0, 9):
                for bx in (ax, ax - tw - pad, ax + tw + pad):
                    for by in (ay, ay - th - pad, ay + th + pad):
                        bx2, by2 = bx + (-grow * 6 if bx > ax else grow * 6), by + grow * 6
                        if clean_box(bx2, by2, tw, th):
                            return bx2, by2 + th
        return None

    picks = []
    # 交替分配到不同方向：上、下、左、右、右下、右上、左下、左上
    prefer = [0, 2, 1, 3, 6, 5, 7, 4]
    for i, it in enumerate(items):
        fs = it["_fs"]
        tw = max(1, int(len(it["text"]) * fs * 1.05))
        th = int(fs * 1.15)
        order = prefer[i:] + prefer[:i]
        got = place(tw, th, order)
        if got:
            bx, by = got
            taken[max(0, by - th):by, bx:bx + tw] = True
            picks.append((bx / W, by / H))
        else:
            picks.append((None, None))
    return picks


def blank_slots(img: Image.Image, count: int, cell=(6, 4)):
    """旧行为：按格子白度找最空的位置，返回归一化坐标。"""
    small = img.convert("RGB").resize((240, 135))
    px = small.load()
    cols, rows = cell
    scores = []
    for r in range(rows):
        for c in range(cols):
            x0, x1 = c * 240 // cols, (c + 1) * 240 // cols
            y0, y1 = r * 135 // rows, (r + 1) * 135 // rows
            vals = [px[x, y] for y in range(y0, y1, 3) for x in range(x0, x1, 3)]
            white = sum(1 for p in vals if min(p) > 205) / max(1, len(vals))
            scores.append((white, c / cols, r / rows))
    scores.sort(reverse=True)
    picked = []
    for _, x, y in scores:
        if all(abs(x - p[0]) > 0.25 or abs(y - p[1]) > 0.25 for p in picked):
            picked.append((x, y))
        if len(picked) >= count:
            break
    return picked


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--out")
    ap.add_argument("--label", action="append", default=[], help="文字@x,y[,颜色[,字号百分比[,旋转度]]]")
    ap.add_argument("--labels", help="多个 label 用 ; 分隔")
    ap.add_argument("--font", default="kaiti", choices=list(FONT_QUERY))
    ap.add_argument("--size", type=float, default=3.2, help="字号占图高百分比")
    ap.add_argument("--opacity", type=int, default=232)
    ap.add_argument("--auto", nargs="?", const="near", choices=["near", "blank"],
                    help="未给坐标时自动选位：near=贴着物件(默认)，blank=最白处")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--no-snap", action="store_true",
                    help="不自动贴向图案（默认会把字朝最近笔画推到 10-40px 内）")
    a = ap.parse_args()

    specs = list(a.label)
    if a.labels:
        specs += [s for s in a.labels.split(";") if s.strip()]
    items = [parse_label(s) for s in specs]
    if not items:
        sys.exit("没有 --label")

    src = Path(a.image)
    out = Path(a.out or src.with_name(src.stem + "-labels.png"))
    base = Image.open(src).convert("RGBA")
    W, H = base.size

    font_path = find_font(a.font)
    for it in items:
        pct = it["size"] or a.size
        it["_fs"] = max(14, int(round(pct / 100.0 * H)))

    if a.auto:
        todo = [it for it in items if it["x"] is None or it["y"] is None]
        if todo:
            if a.auto == "blank":
                slots = blank_slots(base, len(todo))
                for it, (sx, sy) in zip(todo, slots):
                    it["x"], it["y"] = sx + 0.02, sy + 0.05
            else:
                slots = pick_positions(base, todo, mode="near")
                for it, (sx, sy) in zip(todo, slots):
                    if sx is None:
                        sys.exit(f"找不到干净落点: {it['text']}（换 --auto blank 或手动给坐标）")
                    it["x"], it["y"] = sx, sy

    gray_np = np.array(base.convert("L"))
    ink_ii = _integral(gray_np < 205)
    taken_mask = np.zeros_like(gray_np, dtype=bool)
    taken_ii = _integral(taken_mask)

    random.seed(a.seed)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    placed = []
    for it in items:
        if it["x"] is None or it["y"] is None:
            sys.exit(f"缺少坐标: {it['text']}（用 --auto 或写 @x,y）")
        pct = it["size"] or a.size
        fs = max(14, int(round(pct / 100.0 * H)))
        font = load_font(font_path, fs)
        color = Image.new("RGBA", (1, 1), it["color"]).getpixel((0, 0))[:3] + (a.opacity,)
        rot = it["rot"] if it["rot"] is not None else random.uniform(-2.5, 2.5)

        bbox = font.getbbox(it["text"])
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

        gap_before = None
        if not a.no_snap:
            bx0, by0 = int(it["x"] * W), int(it["y"] * H) - th
            gap_before = _gap_to_ink(ink_ii, taken_ii, bx0, by0, tw, th)
            snapped = snap_to_ink(gray_np, ink_ii, taken_ii, bx0, by0, tw, th)
            if snapped:
                it["x"], it["y"] = snapped[0] / W, (snapped[1] + th) / H
            else:
                it["_snap_skipped"] = True

        pad = int(fs * 0.6)
        tile = Image.new("RGBA", (tw + pad * 2, th + pad * 2), (0, 0, 0, 0))
        d = ImageDraw.Draw(tile)
        d.text((pad - bbox[0], pad - bbox[1]), it["text"], font=font, fill=color)
        tile = tile.rotate(rot, resample=Image.BICUBIC, expand=True)
        px, py = int(it["x"] * W), int(it["y"] * H)
        # x,y 是文字左端基线 → 换算到贴图左上角
        layer.alpha_composite(tile, (px - pad, py - pad - th))
        bx, by_top = px, py - th
        taken_mask[max(0, by_top):max(0, by_top) + th, max(0, bx):max(0, bx) + tw] = True
        taken_ii = _integral(taken_mask)
        gap_after = _gap_to_ink(ink_ii, _integral(taken_mask), bx, by_top, tw, th)
        placed.append({"text": it["text"], "x": round(it["x"], 3), "y": round(it["y"], 3),
                       "size_px": fs, "color": it["color"], "rot": round(rot, 1),
                       "gap_px_before": gap_before, "gap_px": gap_after,
                       "snap": "kept" if it.get("_snap_skipped") else "moved"})

    result = Image.alpha_composite(base, layer).convert("RGB")
    out.parent.mkdir(parents=True, exist_ok=True)
    result.save(out)
    print(json.dumps({"path": str(out), "font": os.path.basename(font_path), "labels": placed},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
