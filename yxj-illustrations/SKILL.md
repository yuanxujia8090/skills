---
name: yxj-illustrations
disable-model-invocation: true
description: >-
  为「圆点 Agent 栈」生成封面与分享卡配图（手绘带标注 · 风格2）。当用户要圆点封面图、文章头图、分享卡、按可用版V1 画圆点、或已成稿的封面视觉时使用；
  会调用 zhient gpt-image-2 直接出图。正文插图默认不做——正文优先真实截图或可复用信息图。
---
# 圆点封面与分享卡配图（可用版 V1 · 风格2）

## 核心定位

为「圆点 Agent 栈」生成**封面、分享卡**的视觉配图，并**直接调用生图 API 落盘**。

**分工边界（2026-11-13 定）**：

| 场景 | 谁负责 |
| --- | --- |
| 正文配图 | **真实操作截图优先**；降级为信息图／流程图；**不生成插画** |
| 封面、分享卡、头图 | **本技能** |
| 只想要提示词、不实际出图 | `yxj-content-workflow-v8` 的 `references/visual-gpt-image.md` |

正文确实需要插画时，先向用户确认，再按本技能临时出一张，不在默认路径里。

视觉 IP 锁定 **可用版 V1**：深蓝羽绒服 + 黑帽红色五角星；**画法一律用「风格2 手绘带标注」**（暖白纸纹 + 细墨线 + 轻水彩 + 三色），不再用旧彩色素描。可选白色圆形机器人（脸屏红五角星）。

**画面主体是物件和结构，不是人**：圆点一张图最多出现一次（全身远景，约 20–25% 图高），结构自己说得清时可以不出现。

流程学自 ian-xiaohei（消化 → shot list → 单张生成 → 质检），形象原创，不搬小黑外形。

## 仓库版使用约定

外网/新机器上用时，命令都在本技能目录执行；环境前提、依赖安装、配置项见 [README.md](README.md)。脚本不硬编码本地路径：地址/模型/超时/取哪个 key 由环境变量（`OPENIMAGE_*`）或配置文件（默认 `~/.pi/agent/image-gen.json`，可用 `YXJ_IMAGEGEN_CONFIG` 换）决定，两者都没有才用内置默认值。改图需要 `requests`。

默认不自动重试；失败先读报错，用户明确允许再重跑。

## 先读参考

- `references/style-dna.md`
- `references/yuandian-ip.md`
- `references/composition-patterns.md`（8 种结构 + 原创隐喻三步 + 元素组织）
- `references/prompt-template.md`
- `references/qa-checklist.md`
- `references/image-api.md`（生图 API，对齐 pi `image-gen`）
- `assets/可用版V1.jpg`（角色设定卡，改图时必传）

## 画面构成（2026-11-06 定，优先于其它描述）

一句话：**物件和结构是主体，圆点是场景里干活的那个小角色，而且不一定出场。**

| 规则 | 要求 |
| --- | --- |
| 人物 0 或 1 次 | 最多一个圆点；多状态用物件状态表达，不重复画人 |
| 人物要小 | 全身远景约 **20–25%** 图高；不画半身、大头、多视图 |
| 可以不出现 | 漏斗、闸门、秤、抽屉分层、一条路线能自己说清 → 不画人 |
| 物件更大 | 主物件 3–5 个，占画面 40–60%，明显比人大 |
| 线条 | 细线、轻微抖动；不粗描边、不矢量、不网格 |
| 布局 | 留白 ≥35%，一条主流向，主体偏一侧/偏下 |
| 批注 | 4–8 处（基准 5 处），2–6 字，环绕主体分布 |

## 工作流

### 1. 消化正文
提炼核心观点、认知转折、适合配图的锚点。不要平均配图。

### 2. 先出配图策略（可选）
若用户只要策略，给 shot list：位置 / 主题 / 核心意思 / **结构类型** / **要不要出现圆点** / 圆点动作（若出现）/ 建议物件 / 标注词。默认 4–8 张；用户指定张数时按指定。

### 3. 直接出图（默认）
用户要「配图 / 出图 / 生成插图」时：

1. 选定 N 张（用户未指定则 3–5 张关键锚点）。
2. 每张先定两件事：**结构类型**（composition-patterns 里选一种）和**是否出现圆点**。
3. 按 prompt-template 写英文画面描述：物件比人大、3–5 主物件、一条流向、留白 ≥35%、线条细而抖；要人时写清小全身（20–25% 图高）+ 动宾动作。
4. **优先改图**：把 `assets/可用版V1.jpg` 作参考，调用脚本（见下），`size=1536x1024`。
5. 逐张生成，不要拼成一张。
6. 过 qa-checklist；人过大、出现多人、结构太满就带同一参考图重跑（追加句见 prompt-template 末尾）。
7. 把图给人看，并报路径。

### 4. 生图命令（pi image-gen 同源）

端点／模型／超时／key 来源按 **环境变量 > 配置文件 > 内置默认值** 解析（`OPENIMAGE_BASE_URL` / `OPENIMAGE_MODEL` / `OPENIMAGE_TIMEOUT_MS` / `OPENIMAGE_KEY_PROVIDER`，配置文件默认 `~/.pi/agent/image-gen.json`，字段 `baseUrl` / `model` / `timeoutMs` / `keyProvider`），**改服务商只改配置，不改代码**；key 取 `OPENIMAGE_API_KEY`、`~/.pi/agent/openimage.key`，或 `~/.pi/agent/auth.json` 里 `keyProvider` 指定项的 `key`。查当前生效值与来源：`python3 scripts/generate_image.py --show-config`（不调接口、不计费）。细节见 `references/image-api.md`。

```bash
python3 scripts/generate_image.py \
  --prompt "...english scene description..." \
  --image assets/可用版V1.jpg \
  --size 1536x1024 \
  --out assets/<article-slug>-illustrations/01-topic.png
```

不传 `--image` 则为纯文生图。**要人时传参考图锁身份；这张不画人时不要传**（设定卡会把人画回来）。

一次约 20–70 秒，**真实计费**；用户明确要图才调用。

### 5. 保存交付

```text
assets/<article-slug>-illustrations/
01-topic.png
02-topic.png
```

交付：张数、每张用途、路径、**这张有没有人**（被人问起好解释）。短报即可。

## 固定身份（压缩）

> 圆点：东亚男性，风格2 手绘带标注；黑帽 + **朱红五角星** `#E8552D`；**藏蓝**羽绒服 `#1F3A5F`；平静专注。全文只画一个、全身远景约 20–25% 图高，或干脆不画。可选小白机器人脸屏红星。禁红圆点帽标、禁浅蓝外套、禁 AI 帅哥脸、禁半身/多视图、禁小黑外形。


## 在 pi agent 中的用法

本技能是**手动技能**（`disable-model-invocation: true`）：只有用户明确要封面图、分享卡，或敲 `/skill:yxj-illustrations` 时才执行。写文章中段不要自动跑它。

生图优先顺序：

1. `python3 <本技能目录>/scripts/generate_image.py ...`（推荐，自带 key 读取与 url/b64 兼容）
2. 若当前会话已启用 `generate_image` 工具，也可用它；改图时 `image` 指向本技能 `assets/可用版V1.jpg` 的绝对路径

参考文件路径一律相对本技能根目录解析。
