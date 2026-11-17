# 单张生图提示词模板

把方括号换成本张图内容。**要人时**把 `assets/可用版V1.jpg` 作参考图锁身份；**不要人时纯文生图，不传参考图**。画面描述用英文更稳。

**先定两件事，再套模板**：① 这张选哪种结构（`composition-patterns.md`）；② 这张要不要出现圆点。

## 模板

```text
Flat 2D storybook-infographic illustration for a Chinese tech article cover or share card.
Hand-drawn marker-and-watercolor style on warm off-white paper (#F5F0E6) with subtle paper grain.
Thin imperfect ink linework (#1A1A1A), light flat watercolor fill.
Only three accent colors: ink black, burnt orange (#E8552D), navy (#1F3A5F).
Playful but tidy, generous negative space, hand-lettered labels that stay perfectly legible.
No 3D, no photorealism, no glossy highlights, no gradients, no colored-pencil hatching,
no stock clip-art look, not commercial flat illustration.

Composition (follow exactly):
one single core structure; 3 to 5 main objects only; the objects are the subject
and are much bigger than any person; subject placed off-center, not a centered poster;
one main flow direction only (left to right, or top to bottom);
at least 35% empty paper, with one quiet blank area kept for handwritten labels;
no dense node network, no stacked arrows, no grid lines, no ruler guides, no thick outlines.

Structure type: [Workflow / 系统局部 / 前后对比 / 状态演变 / 概念隐喻 / 方法分层 / 地图路线]
Core idea: [这张图要表达的一个意思]

Scene: [1–3 句：入口是什么物件、怎么流动、出口是什么]

Character (at most ONE appearance, optional — pick one block):
[需要人]
Character IP 圆点 MUST match reference sheet: East Asian man, calm focused face,
black baseball cap with ONE solid RED five-pointed star on front (not a red circle),
DARK NAVY quilted puffer jacket, black shirt, black pants.
Draw him as a small distant FULL-BODY figure, about 20–25% of the image height,
doing the core action: [动作]. The machine/object is much bigger than him.
[不需要人]
NO person in the image. The objects and structure alone carry the meaning.
（这一支不要传 `assets/可用版V1.jpg`：设定卡上有人，模型会把人画回来。用纯文生图。）

Optional: one tiny round white robot with a RED five-pointed star on its face screen
(never use the robot to add a second human).

Sparse handmade Chinese labels, 4–8 labels, 2–6 characters each, placed next to the
objects they name and spread around the structure (top / bottom / left / right / corners):
[词1] / [词2] / [词3] / [词4] / [词5]

Color use: black for line art and objects; dark navy only for 圆点's jacket;
red only for the cap star, the robot's face star, key warnings/results;
orange only for the main flow arrows; light blue only for secondary notes.
Invention: do not copy known case compositions; invent a fresh low-tech metaphor
for this article.

Avoid: character sheet, three views, multiple copies of the character, two men,
half-body or close-up or portrait of the character; PPT infographic look;
a title like 流程图/架构图/常见坑 in any corner; cute chibi; generic AI handsome face;
white background with a red circle (Japanese flag look); yellow cap star; light blue jacket.
```

## 两个分支怎么写

- **要人**：动作必须是动宾短语，写清手上拿着什么、身体朝哪、和哪个物件接触。例如 `pulls a jammed paper strip out of an old machine with both hands`。
- **不要人**：不要留「空位等人」；把主物件画大、画细（几个抽屉、几段纸带、一个开口的漏斗）。批注就落在物件旁边。

## 示例

| 文章观点 | 人物 | Scene 要点 | 批注 |
| --- | --- | --- | --- |
| 上下文太长会丢信息 | 要 | 巨大的纸漏斗在画面中央，底部裂口，卡片掉在桌上；人站在漏斗右侧踮脚贴胶带 | 漏了/补上/重来 |
| 实测比文档可靠 | 要 | 桌上摊开的测试记录纸带卷到地上，人蹲着用红铅笔圈一行 | 实测/通过/文档没说 |
| 一条素材拆成三种内容 | **不要** | 一个纸团在左侧被压成三块不同形状的成品，橙色箭头从左到右；三个成品大小不同 | 一份/拆开/三种 |
| 设计稿到上线要过几道闸 | **不要** | 一条弯曲路径穿过三道不同高度的闸门，第一道半闭 | 卡在闸门/放行/上线 |

## 改图时的追加句

- 人太大/成了半身：`Keep the same scene but redraw the man much smaller: a distant full-body figure about 20% of the image height, the object much bigger than him.`
- 多出人物：`Remove all but one figure; there must be exactly one person at most.`
- 人只是站着：`Keep the meaning; make the man actually do the core action with his hands, not stand beside the diagram.`
- 结构太满：`Simplify: keep only 3–5 main objects and one flow direction; increase white space to 40%.`
- 线条太硬：`Redraw the lines as thin, slightly wobbly pen strokes; remove straight vector edges and uniform grids.`
- 去掉左上角标题：`Remove only the handwritten title in the top-left corner and its underline; fill with the same clean white background; change nothing else.`
