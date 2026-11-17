# yxj-illustrations

「圆点 Agent 栈」封面与分享卡的云端生图技能。手绘带标注·风格2，圆点 IP 锁定 `assets/可用版V1.jpg`，出图走 OpenAI 形状的 `/images/generations`、`/images/edits` 接口。

本地免费版见同仓 [yxj-illustrations-comfyui](../yxj-illustrations-comfyui/)；两者职责相同，后端不同。

## 内容

```text
SKILL.md                       主说明（agent 读这个）
README.md                      环境与用法（本文件）
requirements.txt               改图所需的 requests
scripts/generate_image.py      出图／改图，读配置，不硬编码本地路径
scripts/test_smoke.py          离线冒烟测试（mock 服务，不计费）
references/style-dna.md        风格2 画法 DNA
references/yuandian-ip.md      圆点外形与性格
references/composition-patterns.md  8 种结构 + 原创隐喻三步
references/prompt-template.md  英文画面描述写法
references/qa-checklist.md     出图后质检
references/image-api.md        接口、配置项、已知坑
assets/可用版V1.jpg            角色设定卡（要人时当参考图传）
```

## 环境前提

- Python 3.9+；纯标准库即可出文生图，**改图需要 `requests`**：

```bash
python3 -m pip install -r requirements.txt
```

- 需要一个兼容 OpenAI 图片接口的服务（`/v1/images/generations`，可选 `/v1/images/edits`），并有该服务的 key。
- 本仓库不提供 key、不代付费用。每次真实出图都计费，单张通常 20–70 秒。

## 配置

优先级：**环境变量 > 配置文件 > 内置默认值**，每个字段各自回退。**`baseUrl` 没有内置默认值**，必须自己配（环境变量或配置文件），否则脚本报 `missing baseUrl` 退出，不会偷偷打到某个第三方地址。

| 环境变量 | 配置文件字段 | 说明 |
| --- | --- | --- |
| `OPENIMAGE_BASE_URL` | `baseUrl` | 形如 `https://host/v1`，末尾斜杠会被去掉 |
| `OPENIMAGE_MODEL` | `model` | 图片模型名 |
| `OPENIMAGE_TIMEOUT_MS` | `timeoutMs` | 单次请求超时，毫秒 |
| `OPENIMAGE_KEY_PROVIDER` | `keyProvider` | 从 `~/.pi/agent/auth.json` 取哪个键 |
| `OPENIMAGE_API_KEY` | — | 直接给 key（优先于 auth.json） |
| `YXJ_IMAGEGEN_CONFIG` | — | 换一份配置文件路径 |

配置文件默认 `~/.pi/agent/image-gen.json`，格式：

```json
{
  "baseUrl": "https://your-gateway.example/v1",
  "model": "gpt-image-2",
  "timeoutMs": 300000,
  "keyProvider": "openimage"
}
```

key 的取法顺序：`OPENIMAGE_API_KEY` → `~/.pi/agent/openimage.key` → `~/.pi/agent/auth.json` 里 `keyProvider` 对应项的 `key` / `api_key`。

只看当前生效值（不调接口、不计费）：

```bash
python3 scripts/generate_image.py --show-config
```

## 使用

```bash
# 文生图
python3 scripts/generate_image.py \
  --prompt "a huge paper funnel on a desk, thin ink lines, warm paper, lots of white space" \
  --size 1536x1024 --out ./out/01-funnel.png

# 改图（要人时传设定卡锁身份）
python3 scripts/generate_image.py \
  --prompt "keep identity from reference, the man carries a heavy drawer" \
  --image assets/可用版V1.jpg --size 1536x1024 --out ./out/02-drawer.png
```

标准输出一行 JSON：`path` / `mode` / `seconds` / `revised_prompt` / `model` / `size` / `bytes`。失败时退出码非 0，报错打到标准错误，不自动重试。

画面怎么定、要不要画人、批注几个——先读 `SKILL.md` 和 `references/`，不要直接照抄旧构图。

## 离线验证

```bash
python3 scripts/test_smoke.py
```

起本地 mock 服务，验证配置解析、env 覆盖、`b64_json` 与 `url` 两种响应、改图上传参考图、缺参数报错。**不请求真实服务、不计费**；真实出图仍需各自环境的 key 与服务单独验收。

## 限制与安全

- 生成结果可能多字、多人，或把圆点画成半身/大头；出图后按 `qa-checklist.md` 过一遍，不合格带同一参考图重跑。
- 改图会原样上传参考图给你配置的服务商，别传客户素材或未授权图片。
- 设定卡是圆点角色素材，不是通用人物模板；构图参考的来源标注保留在原文件。
- 已知坑见 `references/image-api.md`（部分网关约 30 秒切流，超时调大救不回来）。
