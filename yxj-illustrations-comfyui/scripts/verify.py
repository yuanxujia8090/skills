#!/usr/bin/env python3
"""本地版出图机检：底图是否残留文字、是否出现设定卡式多视图。

用法:
  python3 verify.py <图片...>          # 或 glob: "01-*.png.notext.png"

检查项（macOS Vision）:
  1. OCR 文字块 —— 无字出图应接近 0；>0 说明模型自己画了字（常见：设定卡的「正面/侧面/背面」）
  2. 人脸数量 —— 应恰好 1 个；>1 说明画出重复人物或设定卡版式
  3. 人脸高度 —— 理想 4-6%（全身约 20-25% 图高）；>9% 说明画成近景，违反「人物小、为内容服务」
  4. 人脸 = 0 —— 提示人物可能没画或小到检不出，需人眼确认（不算硬错误）

局限：深蓝外套颜色检测不可靠（物件也用深蓝），别用它推算人物尺度。

注意: 只能发现「可识别」的文字。中文小字可能漏检，不等于零文字。
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SWIFT = r'''
import Foundation
import Vision
import AppKit
for path in CommandLine.arguments.dropFirst() {
    guard let img = NSImage(contentsOfFile: path),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { continue }
    let name = URL(fileURLWithPath: path).lastPathComponent

    let treq = VNRecognizeTextRequest()
    treq.recognitionLevel = .accurate
    treq.usesLanguageCorrection = false
    treq.recognitionLanguages = ["zh-Hans", "en-US"]
    try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([treq])
    let texts = (treq.results ?? []).compactMap { $0.topCandidates(1).first?.string }

    let freq = VNDetectFaceRectanglesRequest()
    try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([freq])
    let faces = (freq.results ?? []).count
    let maxH = (freq.results ?? []).map { $0.boundingBox.height }.max() ?? 0

    print("RESULT\t\(name)\t\(texts.count)\t\(faces)\t\(String(format: "%.3f", maxH))\t\(texts.prefix(6).joined(separator: " | "))")
}
'''


def main(argv):
    if not argv:
        sys.exit(__doc__)
    if not shutil.which("swift"):
        sys.exit("没有 swift，跳过机检（macOS 才支持）")
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "verify.swift"
        src.write_text(SWIFT)
        r = subprocess.run(["swift", str(src), *argv], capture_output=True, text=True, timeout=600)
    rows = []
    for line in r.stdout.splitlines():
        if not line.startswith("RESULT\t"):
            continue
        _, name, ntext, nfaces, maxh, sample = (line.split("\t") + [""] * 6)[:6]
        ntext, nfaces, maxh = int(ntext), int(nfaces), float(maxh or 0)
        flags = []
        if ntext > 0:
            flags.append("残留文字")
        if nfaces > 1:
            flags.append("多人物(应只出现一次)")
        if maxh > 0.09:
            flags.append(f"人物过大(脸高{maxh:.0%})")
        if nfaces == 0:
            flags.append("未检出人物(可能没画或过小)")
        rows.append({"file": name, "text_blocks": ntext, "faces": nfaces,
                     "face_height": round(maxh, 3), "sample": sample, "flags": flags})
    for row in rows:
        mark = "⚠️ " + ",".join(row["flags"]) if row["flags"] else "OK"
        print(f"{mark:26} {row['file']}  文字块={row['text_blocks']} 人脸={row['faces']} 脸高={row['face_height']:.1%}"
              + (f"  样例: {row['sample']}" if row["sample"] else ""))
    print(json.dumps(rows, ensure_ascii=False))
    if any(r["flags"] for r in rows):
        print("\n处置：残留文字 → 换 --seed 重出，或 --ref none；"
              "多人物 → 改 scene 强调 exactly one small figure；"
              "人物过大 → 改 scene 加 far away / small full-body", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:])
