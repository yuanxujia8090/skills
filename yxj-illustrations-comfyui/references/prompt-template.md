# 本地版 scene 写法

`scripts/generate.py` 已内置四段，agent **不要重复写**：

1. 风格前缀：风格2 手绘带标注（暖白纸纹 `#F5F0E6` + 细墨线 `#1A1A1A` + 三色）、留白、**物件是主体、单一结构、3–5 主物件**
2. 比例约束：**人物恰好一次、全身 20–25% 图高、远景**
3. 身份描述：设定卡参考 + 东亚男性 + 黑帽红五角星 + 深蓝羽绒服（`--ref none` 时改用纯文字身份）
4. 负面词：多人格、设定卡三视图、半身/大头、红圆点帽标、浅蓝外套、乱码、左上角标题等

agent 写两样：**scene**（位置参数）和 **labels**（`--labels`，文字后期叠，不写进 scene）。

**这张不需要人**：加 `--no-person`，scene 只写物件和流动（`a huge paper funnel with a crack at the bottom, cards falling onto a desk`）。脚本跳过人物比例与身份段，并默认 `--ref none`——不要手配 `--ref vision`，设定卡会把人物带回来。

## scene 公式（英文，1–3 句）

```text
the man [具体动作] [低科技隐喻物件]; [信息怎么流动 / 前后对比]; [构图位置].
```

- 主语固定 `the man`（机器人用 `the small white robot`，需加 `--robot`）。
- 动作从 yuandian-ip.md 的「常见职责」里选，或用 composition-patterns.md 的「原创隐喻三步」新造。
- 物件只选 1–2 个。
- 不要写中文、角色名、文件名、尺寸、以及任何要出现在图上的文字。
- 不要写 `two men` / `different poses` / `four states` —— 立刻变成多个人物。
- 想让圆点更小：写 `far in the background`，或把物件写大（`a huge cabinet fills the frame`）。
- 想让线条更像草图：写 `quick loose pencil`，别写 `clean vector`。

## 示例

| 文章观点 | scene | labels |
|---|---|---|
| 实测比文档可靠 | `the man sits at a small desk typing on a laptop, a long paper test log curls out onto the floor, he points at one line with a red pencil` | `实测/通过` |
| 上下文太长会丢信息 | `the man holds a leaking paper funnel, small note cards fall out of a crack at the bottom, he tapes the crack` | `漏了/补上` |
| 先拆小再交给 agent | `the man cuts a huge paper roll into small cards and feeds them one by one into a small white robot` | `拆小/一张张` |
| 方案对比 | `left: the man stuck under a pile of tangled cables; right: the man calmly holding one clean cable; orange arrow from left to right` | `之前/之后` |

## 批注摆放

叠字坐标是归一化 0–1 的**左端基线**，字宽约 `字数 × 字号(px)`。

- **一键贴图**：坐标不用很准，脚本会把字朝最近笔画推到 8–28px（位移上限 100px）。想精确控制加 `--no-snap`。
- 一张图 **4–8 处、基准 5 处**，每个主要结构旁一处，环绕主体分布（上/下/左/右/四角）。
- 初始坐标给"大致方位"即可，例如主体在中间就写 `0.05,0.20` / `0.75,0.25` / `0.75,0.72` / `0.05,0.72` / `0.45,0.88`。
- 输出里有 `gap_px`：>35 说明这处没贴上去，换初始坐标；`snap:kept` 同理。
- 颜色：红 `#c0392b` 重点/问题，橙 `#d35400` 流程，蓝 `#2e6da4` 补充。
- 字号 3.2 默认；标题型批注 4–4.5。

## 重出时怎么改

- 身份漂移：先换 seed；连续两次漂移 → `--ref latent`。
- 构图像设定卡（人物正面站立、多视图排版）：改回 `--ref vision`，或在 scene 里写清楚侧身动作。
- 字不对/压主体：不要重出图，改 `--labels` 坐标或文案，从 `.notext.png` 重叠即可。
- 圆点像旁观：把动作动词提到句首，写清手上拿着什么。
