---
name: yxj-illustrations-comfyui
disable-model-invocation: true
description: >-
  「圆点 Agent 栈」封面与分享卡配图的本地 ComfyUI 版：本机 Qwen-Image 2.1 + 可用版V1 设定卡
  参考图，手绘带标注·风格2，不走云端计费。用户要圆点封面图/头图/分享卡，且提到本地、
  ComfyUI、省钱、批量时使用；用户指定云端或 gpt-image-2 时改用 yxj-illustrations。
  正文插图默认不做——正文优先真实截图或可复用信息图。
---
# 圆点封面与分享卡配图 · 本地 ComfyUI 版

**分工边界（2026-11-13 定）**：正文配图走真实截图／信息图，**不生成插画**；本技能只做封面、分享卡、头图，与云端版 `yxj-illustrations` 同职责、不同后端（本地免费 / 云端计费）。

融合两个技能：

| 来自 | 拿了什么 |
|------|---------|
| `yxj-illustrations`（云端 gpt-image-2） | 圆点 IP、风格2 手绘带标注 DNA、质检清单、设定卡 `assets/可用版V1.jpg` |
| `gzh-xiaohei-comfyui`（本地小黑） | ComfyUI 后端探测、Qwen-Image 2.1 三件套、串行提交、坑清单、构图模式 |

**关键融合点**：云端版靠「上传设定卡改图」锁形象；本地版用 `TextEncodeQwenImage21` 节点自带的 `images` 参考图输入，把设定卡喂给编码器，起同样作用。

## 仓库版使用约定

以下命令均在本技能目录执行。模型、输出和参考图路径可配置，详见 [README.md](README.md)。默认不自动重试；重试前先读报错，`--retries` 只在用户明确允许时设置。

## 先读参考

- `references/yuandian-ip.md`：圆点外形、性格、职责（与云端版同源）
- `references/style-dna.md`：风格2 手绘带标注（与云端版同源，逐字一致）
- `references/composition-patterns.md`：8 种结构 + 原创隐喻三步（取自小黑版，「小黑」读作「圆点」）
- `references/prompt-template.md`：本地版写 scene 的方法
- `references/qa-checklist.md`：质检（含本地版加项）

## 画面构成（学自 ian-xiaohei，2026-11-06 定）

一句话：**物件和结构是主体，圆点是场景里干活的那个小角色，而且不一定出场。**

| 规则 | 具体要求 | 为什么 |
|---|---|---|
| 人物 0 或 1 次 | 一张图最多 1 个圆点；不要多视图、不要分镜里每格一个、不要角色设定卡式排版。结构自己说得清时**可以不画人**（漏斗、闸门、秤、抽屉分层、路线） | 多个人物会抢走结构表达，读者先看人再看意思；人缺席时图意仍成立就不该硬塞 |
| 人物要小 | 全身约 **20–25%** 图高；远景全身，不画半身、不画大头 | 配图是解释结构，不是人物海报 |
| 物件更大 | 主要物件、机器、抽屉、漏斗、纸带、柜子都比人大 | 让读者的眼睛先落在"这东西怎么运转" |
| 单一结构 | 一张图一个核心动作，主物件 **3–5 个**；不要密集节点网 | 小黑版的失败信号就是"元素太多、箭头太多" |
| 线条 | 细线、轻微抖动、不机械、不矢量、不要粗描边、不要均匀网格 | 手绘草图感；粗线和网格会立刻变成 PPT |
| 留白 | 至少 35% 空白，最好留一整块安静区域放批注 | 批注要落在纸上，不是挤在图上 |
| 文字 | 不进模型（`add_labels.py` 后期叠），**4–8 处、基准 5 处**，贴各结构 | 见「文字策略」 |

**结构类型**从 `references/composition-patterns.md` 里选一种，不要混。注意其中的「角色状态」和「小漫画分镜」两类会画出多个人物，本技能改成：**用物件状态表达多状态**（例如三个抽屉的不同深浅），不重复画人。

## 后台内存：生成后卸载（默认开）

ComfyUI 常驻会一直占着模型（本机实测 137GB 统一内存里曾占到 96GB）。本技能默认**每次生成结束后让后端卸载模型**：

- `generate.py` 在提交任务**之前**给后端设 `unload_models` 标记；ComfyUI 在任务结束时才处理这个标记，所以生成完自动卸载 + 回收缓存。
- 连续出多张时加 `--keep-loaded`，避免每张都重载模型（重载约 1–2 分钟）；整批结束后手动跑一次：
  ```bash
  python3 ~/.agents/skills/yxj-illustrations-comfyui/scripts/free_comfy.py
  ```
- `free_comfy.py` 只设标记、不关进程。要彻底回收内存，手动退出 ComfyUI Desktop。
- **两个技能都不会启动或关闭 ComfyUI**：本地版只探测端口，云端版 `yxj-illustrations` 完全不用 ComfyUI（走 zhient.com API）。
- 坑：`/free` 里不要带 `free_memory: true`，也不要额外发「轻任务」去触发卸载 —— 2026-11-07 实测这样会把后端直接搞挂（进程退出、端口不再监听）。

## 前置检查（每次开工，10 秒）

1. 后端：`curl -s -m 2 http://127.0.0.1:8000/system_stats`；不通试 8188；都不通 → 请用户打开 ComfyUI Desktop。**agent 不自己起后端**。
2. 模型：按 `--model-root` 或环境变量 `COMFYUI_MODEL_ROOT` 检查三件套，默认 `~/ComfyUI/models`；缺失直接退出。

## 文字策略（重要：别让本地模型写字）

本机 Qwen-Image 2.1 int8 的中文小字曾出现错笔画，也有多余标题、签名和参考图标签。未做未量化版本的对照，不能断言量化是错字原因；提示词禁止文字也不保证完全消除。

所以默认做法：**模型只画画面，文字由 `add_labels.py` 用本机楷体后期叠加**。字形交给字体渲染，仍需检查字体覆盖、位置与遮挡。

```bash
# 推荐：出无字图 + 出生时就叠好字（坐标必填）
python3 scripts/generate.py "the man pulls a jammed paper strip out of an old machine" \
  --labels "卡住@0.08,0.80,#c0392b" --labels "重来@0.66,0.24,#d35400" \
  --name 01-jam --out-dir <文章目录>/assets/<slug>-illustrations

# 不知道放哪：自动找空白（可能压到主体，出图后必须看一眼）
python3 scripts/generate.py "..." --labels "卡住/重来" --auto-label

# 只给已有图补字 / 改文案（秒级）
python3 scripts/add_labels.py 01-jam.png.notext.png --out 01-jam.png \
  --labels "卡住@0.08,0.80,#E8552D;重来@0.66,0.24,#E8552D"
```

- `--label` 格式 `文字@x,y[,颜色[,字号百分比[,旋转度]]]`；x,y 是归一化 0–1，指文字**左端基线**。
- 默认字号 3.2% 图高（1664×928 约 30px）；想更醒目写 4–4.5。
- 字体 `--font`：`kaiti`（默认，像铅笔批注）/ `hannotate`（更手写）/ `xingkai`（行书）/ `yuang` / `heiti` / `song`。
- 每个 label 自动带 ±2.5° 微旋转，避免印刷感。
- **批注 4–8 处，基准 5 处**，每处 2–6 字；每个主要结构旁一处（学 xiaohei）。只有 2 处会显得信息不足。
- 布局要环绕主体：上/下/左/右/四角各放，别全挤一侧或堆在角上成一列。
- 构图时就要留空位：scene 里已内置 "leave clean blank pockets around the objects"。
- 拿不准位置时先 `--auto near` 出草稿，再按 `--labels` 手改坐标（自动会偏向同一侧，成品建议手定）。
- **默认会把字自动贴向图案**：给定坐标后，`add_labels.py` 朝最近笔画移动，停在距笔画 **8–28px**；位移上限 100px（超过就保持原位，避免标到别的物件上）。想完全按坐标摆：`--no-snap`。
- 输出 JSON 每处带 `gap_px`（最终距笔画像素）和 `snap: moved|kept`。`kept` 说明附近找不到近处空位，需要换初始坐标。
- 无字原图保留为 `<name>.png.notext.png`；改文案从它重叠，不会叠两遍。
- 确实要模型写字：`--model-labels "A/B"`，明确知道在赌乱码。

## 工作流

1. **消化正文 → shot list**：选 3–5 个关键锚点（用户指定按指定）。每张写：位置 / 核心意思 / 结构类型 / **要不要出现圆点** / 圆点动作（若出现）/ 批注词 + 批注放哪。只要策略时到此为止。
2. **写 scene**：英文，主语写 `the man`，不写「圆点」中文名（坑①）。只写动作、隐喻物件、构图；比例、线条、单一结构和身份描述都由脚本内置，**不要重复写，也不要把任何文字内容写进 scene**（文字走 `--labels`）。
   - **这张不需要人** → 加 `--no-person`，scene 只写物件和流动（例如 `a huge paper funnel with a crack at the bottom, cards falling onto a desk; orange arrow loops back up`）。脚本会跳过人物比例与身份段，并默认 `--ref none`（参考图会把人物带回来）。
   - 想让圆点更小：在 scene 里写 `far in the background` 或加大物件描述（如 `a huge cabinet fills the frame`）。
   - 不要写 `two men` / `different poses` / `four states`，会立刻变成多个人物。
3. **逐张串行生成**：

   ```bash
   python3 ~/.agents/skills/yxj-illustrations-comfyui/scripts/generate.py \
     "the man pulls a jammed paper strip out of an old machine, an orange arrow loops back into the machine" \
     --labels "卡住/重来" --name 01-jam \
     --out-dir <文章目录>/assets/<article-slug>-illustrations
   ```

   - 单张约 3 分钟（实测 160–185s，1664×928，25 步）。在支持后台的环境放后台跑。
   - 多张**串行**，不要并发（同一后端抢显存）。
   - 可选参数：`--no-person` 不画人（结构自己说得清时用）；`--robot` 加小白机器人；`--ref vision|latent|none`；`--seed N` 复现或换图。
   - 叠字失败会保留无字原图并在 JSON 里给 `labels_error`，不会丢图。
4. **机检（必做，30 秒）**：`python3 scripts/verify.py <目录>/*.png.notext.png`
   - 文字块 > 0 → 模型自己画了字（最常见是设定卡的「正面/侧面/背面」），换 `--seed` 重出或 `--ref none`。
   - 人脸 > 1 → 画出设定卡式多视图，同样处理。
   - 机检只发现**可识别**的文字，中文小字可能漏检；不等于零文字，最终仍要人眼过。
5. **质检**：按 `qa-checklist.md` 逐张看。画面不行 → 换 `--seed` 重出；只是字不好看/压到主体 → 改坐标，用 `add_labels.py` 从 `.notext.png` 重叠。不做局部修字。
6. **交付**：张数、每张用途、路径、seed、字体、机检结果、是否已人工目视。

stdout 最后一行是 JSON：`path` / `seconds` / `seed` / `ref` / `labels`。
## 参考图模式怎么选

| `--ref` | 做法 | 用于 |
|---------|------|------|
| `vision`（默认） | 只给视觉编码器看设定卡 | 一般场景，构图自由 |
| `latent` | 视觉 + VAE 潜变量 | 形象漂移严重时，贴设定卡更紧，但可能带进设定卡的版式 |
| `none` | 纯文生图 | 参考图把构图带偏时兜底；**`--no-person` 时默认**（没人物就不需要设定卡） |

2026-11-06 实测：①同一 seed 下 `vision`/`latent` 都能出图，`latent` 白底占比更高（89% vs 74%）；②`vision` 有把设定卡「正面/侧面/背面」标签画进画面的实例，`none` 同题未复现，但形象一致性下降。身份保持效果**仍未经人工目视**，确认后再改写默认值。

## 坑

- ① **prompt 里不写中文角色名**：小黑版实测，模型会把「小黑」当批注画进角落。主语一律 `the man`，文字一律不进 prompt。
- ② **不信模型写字**：默认无字出图 + 叠字（见「文字策略」）。要模型写字必须显式 `--model-labels`，按约 2 次尝试/张估产能。
- ③ **叠字坐标留安全区**：字宽约 `字数 × 字号`；离边留 4% 以上，别压在圆点脸上。
- ④ **别重复叠字**：只从 `.notext.png` 重叠，叠两遍会糊。
- ⑤ **不自建后端**：Desktop 实例 = `~/ComfyUI-Installs/ComfyUI/ComfyUI`，模型目录靠内部参数注入；另起旧版会出现 `KeyError: int8_tensorwise` 或噪声图。
- ⑥ **VAE 用 2.1 专属**（`qwen_image_2.1_vae_bf16`），配 1.0 VAE 会出纯噪声。文本编码器用 `qwen3vl_8b_int8_convrot` + `type=qwen_image`，不是 9b PE 那个。
- ⑦ **编码节点一出正负两路**：KSampler positive 接 slot0、negative 接 slot1；cfg 固定 1.0。
- ⑧ `400 value_not_in_list` = 连错端口或后端没挂 Shared 模型目录 → 回坑⑤。
- ⑨ 当前默认输出 1536×1024；历史实例曾用 1664×928，不沿用旧记录判断当前尺寸。
- ⑩ 参考图上传时改成 ASCII 文件名 `yuandian_ref_v1.jpg`，覆盖写入 ComfyUI 的 `input/` 目录。
- ⑪ **参考图会把设定卡的标签带进画面**（2026-11-06 实测）：用 `--ref vision` 出「搬箱子」那张，模型把设定卡上的「正面 / 侧面 / 背面」也画了进去，而 prompt 已明确要求无字。所以出图后必须跑 `verify.py`；连出两次仍带字，改 `--ref none`（纯文字身份描述）。
- ⑫ **人物会反弹变大**（2026-11-06 实测）：prompt 里只写"the man 做某事"时，模型倾向画成半身近景。要么依赖内置 `POS_SIZE`（已写 20–25%），要么在 scene 里补 `far away / small figure / the machine is much bigger than him`。
- ⑬ **不要用颜色反推人物尺度**：深蓝也会被用在物件上，色块分析不可靠；只信人眼和 `verify.py` 的人脸检出行。
- ⑭ **`--ref none` 也不是万能**：形象靠文字描述，跨图细节更容易漂；适合人物在画面里较小、动作优先的图。
- ⑮ ComfyUI 自带 `TextOverlay` 节点**不能用于中文**：它用 Pillow 默认字体，中文变方框，且只能贴顶/底。中文叠字只用 `add_labels.py`。
- ⑯ 当前会话模型不能看图时，必须在交付里写「未做人工目视」，不能说已质检通过。
- ⑰ **`--no-person` 别手配 `--ref vision`**：参考图是角色设定卡，喂进去就会把人画回来。该参数已默认 `--ref none`；要显式指定的场景是「不画人但想借用线条密度」，那只能接受漂移风险。

## 和云端版的分工

| | 本技能（本地） | yxj-illustrations（云端） |
|---|---|---|
| 成本 | 只有电费 | 按张计费 |
| 速度 | 约 3 分钟/张 | 20–70 秒/张 |
| 文字 | 模型写字会乱码 → **默认程序叠字，零乱码** | 模型直接写中文较稳 |
| 适合 | 批量、草稿、试隐喻、所有要精确文字的图（叠字） | 终稿关键图、需要文字「融进笔触」的质感 |

推荐用法：本地批量试构图 + 叠字出终稿；只有确实需要文字融进画面的少数图，再用云端版。
