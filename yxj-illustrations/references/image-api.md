# 生图 API（OpenAI 形状）

## 端点

- 文生图：`POST {baseUrl}/images/generations`
- 改图：`POST {baseUrl}/images/edits`（multipart，单张参考图，字段名 `image`）
- 模型：由配置的 `model` 决定（作者环境用 `gpt-image-2`）
- 鉴权：`Authorization: Bearer <key>`
- 默认尺寸：`1536x1024`（横向）；单张通常 20–70s，**计费**
- 超时：由 `timeoutMs` 决定，作者环境 300000ms

## 配置（改配置，不改代码）

优先级：环境变量 > 配置文件 > 内置默认值。配置默认读 `~/.pi/agent/image-gen.json`，可用 `YXJ_IMAGEGEN_CONFIG` 指向别处：

```json
{
  "baseUrl": "https://your-gateway.example/v1",
  "model": "gpt-image-2",
  "timeoutMs": 300000,
  "keyProvider": "openimage"
}
```

对应环境变量：`OPENIMAGE_BASE_URL` / `OPENIMAGE_MODEL` / `OPENIMAGE_TIMEOUT_MS` / `OPENIMAGE_KEY_PROVIDER` / `OPENIMAGE_API_KEY`。逐字段回退，配置文件只写一部分也能用。

key 顺序：`OPENIMAGE_API_KEY` → `~/.pi/agent/openimage.key` → `~/.pi/agent/auth.json` 中 `keyProvider` 项的 `key` / `api_key`。

查生效值：`python3 scripts/generate_image.py --show-config`（不调接口、不计费）。

作者机器上 Pi 扩展 `~/.pi/agent/extensions/image-gen.ts` 读同一份 JSON，所以改地址/模型两边同时生效；本脚本立即读，Pi 扩展需重启会话。这不是本仓库的依赖，只是同源配置的由来。

## 本技能脚本

```bash
python3 scripts/generate_image.py --prompt "..." --image assets/可用版V1.jpg --size 1536x1024 --out out.png
```

stdout 一行 JSON：`path` / `mode` / `seconds` / `revised_prompt` / `model` / `size` / `bytes`。

## 响应格式注意

网关可能返回 `data[0].b64_json`，也可能只返回 `data[0].url`（需再下载）。脚本两种都处理；`url` 必须是 http/https。

## 已知坑

- **约 30 秒切流**（2026-11-11 实测，`zhient.com` 在 Cloudflare 后）：生成请求 30 秒左右被上游切断（curl 状态 `000` 或 `HTTP 524`），而 `/v1/models` 1.7 秒正常回 401。属服务端，调大 `timeoutMs` 救不回来。
- 网关 4xx/5xx 时脚本把前 400 字符响应体打出来；先读报错再决定重试，默认不自动重试。
- 请求体里不要塞本地路径或文件名；prompt 只写画面。
- 跨境/代理不稳定时先 `--show-config` 确认地址，再用最小 prompt 试一张，别批量跑。
