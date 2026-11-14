# yxj-illustrations-comfyui

圆点封面与分享卡的本地 ComfyUI 技能。包含生成脚本、中文排字、macOS 文字与人脸机检、角色设定卡及五份视觉参考。

## 环境前提

- Python 3.10+；排字使用 Pillow、NumPy，依赖见 `requirements.txt`。
- 主要适配 macOS：排字默认使用系统中文字体；机检依赖系统 Swift 与 Vision。其他系统的字体发现与机检未验证。
- 已启动并可正常生图的 ComfyUI，监听本机 8000 或 8188；脚本不会启动后端。
- 后端必须提供 `TextEncodeQwenImage21`、`CLIPLoader` 的 `qwen_image` 类型及脚本所用节点。仅安装标准 ComfyUI 不代表具备全部节点。
- 本地模型目录中包含以下文件，且后端使用同一组文件名：

```text
models/
├── diffusion_models/qwen_image_2.1_int8_convrot.safetensors
├── text_encoders/qwen3vl_8b_int8_convrot.safetensors
└── vae/qwen_image_2.1_vae_bf16.safetensors
```

本仓库不提供模型或节点安装器。文件名及版本针对作者既有环境，其他权重不能只改名替换；新机器需自行核对来源、使用许可和兼容性。若后端在远端或容器中，本地文件检查不能替代后端节点和模型检查；当前脚本仅连接本机。

## 安装与配置

在本技能目录执行：

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt

export COMFYUI_MODEL_ROOT="$HOME/ComfyUI/models"
export COMFYUI_OUTPUT_DIR="$HOME/Pictures/comfyui-output"
```

默认模型目录为 `~/ComfyUI/models`，默认输出目录为 `~/Pictures/comfyui-output`。也可用 `--model-root`、`--out-dir` 覆盖；参考图用 `--ref-image` 指定。

## 使用

先由 agent 阅读 `SKILL.md` 和 `references/`。`disable-model-invocation: true` 保留原技能的手动触发方式，不保证自动进入每种 agent 的候选技能列表。

```bash
# 生成一张，明确给出文字位置
python3 scripts/generate.py \
  "the man pulls a jammed paper strip out of a huge machine" \
  --labels "卡住@0.08,0.80,#E8552D" \
  --labels "重来@0.66,0.24,#E8552D" \
  --name 01-jam --out-dir ./output

# 仅物件，不画人物，不上传设定卡
python3 scripts/generate.py \
  "a huge paper funnel with a crack, cards falling onto a desk" \
  --no-person --name 02-funnel --out-dir ./output

# 在保留底图上重新排字；--no-snap 严格保持给定位置
python3 scripts/add_labels.py ./output/01-jam.png.notext.png \
  --out ./output/01-jam-relabel.png --no-snap \
  --labels "卡住@0.08,0.80,#E8552D;重来@0.66,0.24,#E8552D"

# 只检查底图；文字识别和人脸识别可能漏检
python3 scripts/verify.py ./output/01-jam.png.notext.png
```

默认生成 1536×1024、25 步；失败不自动重试。`--retries N` 仅用于明确允许的重试。参考图上传会覆盖后端 input 中同名的 `yuandian_ref_v1.jpg`；换自定义参考图前请知晓这一行为。

图片经 `/view` 下载，不依赖 ComfyUI 的输出目录安装在哪里。最后一行返回 JSON（程序可读取的结果记录），包含图片路径、耗时、随机种子等；出现 `labels_error` 表示叠字失败，不能把“有路径”当成整体成功。

## 限制与安全

- 画面本身仍可能生成多余字或多个人物。后期字体排字不等于无字底图已经合格，需机检及人工看图。
- 默认尝试设置生成结束后的模型卸载标记；释放时机取决于后端，不能保证内存立即归还。
- `free_comfy.py` 默认只设置卸载标记。其 `--stop-backend` 会尝试终止监听进程，使用前必须获明确授权；离线检查不调用此功能。
- 不自动转云端模型、不自动产生云端费用。历史耗时和内存数据只代表作者环境。
- 设定卡是圆点角色素材，不是通用人物模板。构图参考的来源标注保留在原文件；本次整理不额外授予第三方素材或角色的商业使用权。
- 本仓库版为便携配置做了小范围适配；不自动覆盖作者机器上原有安装版。

## 离线验证

```bash
python3 scripts/test_smoke.py
```

检查脚本语法、参数入口、任务图结构、模拟 `/view` 下载和中文叠字；不提交真实生图、不卸载模型、不关闭后端。真实生成仍需按本机后端和模型环境单独验收。
