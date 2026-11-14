# 图文参数契约

这是给上游 AI / 调度器看的接口说明。**怎么把 JSON 传进来（HTTP、队列、命令行、函数调用）不归这个仓库决定；这个仓库只负责按参数渲染。**

## 1. 参数优先级

从低到高：

1. `templates/black-card/template.json` 里的模板默认值。
2. `presets/<preset>.json` 预设。
3. plan JSON 里的同名字段。
4. 命令行 `--theme`（只覆盖主题）。

嵌套对象（`account`、`character`）是逐字段合并，不是整块替换。数组（`highlights`）是整块替换。

## 2. 参数表

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `preset` | 否 | 预设 id，例如 `dandan-default`；预设提供默认值 |
| `format` | 否 | 当前固定 `image_post`；缺省自动补 |
| `template` | 是 | 当前 `black-card`；预设里带了就可以不传 |
| `theme` | 否 | 配色主题 id；缺省用模板默认 `butter-yellow` |
| `colors` | 否 | 自定义颜色，覆盖 `theme`；只传要改的键 |
| `account.handle` | 否 | 昵称，原样显示，例如 `@蛋蛋` |
| `account.avatar` | 否 | 头像素材路径；相对 `assets/` 或绝对路径；缺省用角色注册表头像 |
| `hook` | 否 | 第一句，最终正文的精确前缀 |
| `body` | 是 | 正文；最终可见正文 = `hook + body` |
| `highlights` | 否 | 最多 3 段，必须是最终正文精确子串，单段 ≤10 字，不能重叠/相邻 |
| `caption` | 否 | 发布页文案，和图片正文分开 |
| `published_at` | 否 | ISO 8601 时间；缺省用渲染时刻 |
| `timezone` | 否 | IANA 时区，默认 `Asia/Shanghai`；Windows 无 tzdata 时对上海做 +08:00 兜底 |
| `display_time.date` | 否 | 图片上显示的日期；不传则由时间推导，如 `11-14` |
| `display_time.time` | 否 | 图片上显示的时间；不传则由时间推导，如 `20:30` |
| `display_time.weekday` | 否 | 图片上显示的星期；不传则由时间推导，如 `Saturday` |
| `character.enabled` | 否 | 是否叠加 AI 形象 |
| `character.id` | 否 | 角色注册表 id，默认 `dandan` |
| `character.pose` | 否 | 姿势键，默认 `stand`；当前 5 个见第 5 节 |
| `character.placement` | 否 | 放置位：`bottom-right`（默认）、`left-edge`、`right-edge` |
| `character.image` | 否 | 显式形象素材路径；优先级高于 `id + pose` |
| `character.mode` | 否 | `cutout`（透明立绘，默认）或 `sticker`（带背景贴纸） |
| `character.anchor` | 否 | 高级覆盖：`top-left`、`top-right`、`bottom-right`、`bottom-left`、`center` |
| `character.cutEdge` | 否 | 高级覆盖：`none`、`left`、`right`；一般由 `poseMeta` 提供 |
| `character.outlineWidth` | 否 | 高级覆盖：描边宽度，默认 `0`（不画描边） |
| `character.outlineColor` | 否 | 高级覆盖：描边色；`auto` 跟随主题 `highlight`，也可写 `#FFFFFF` 等固定色 |
| `character.glowRadius` | 否 | 高级覆盖：光晕半径，默认 `0` |
| `character.glowOpacity` | 否 | 高级覆盖：光晕透明度，默认 `0` |

`format` / `template` 最终必须存在；如果 plan 不写，就由预设提供。

## 3. 颜色

`theme` 是预设配色；`colors` 是在预设基础上做局部覆盖：

```json
{
  "theme": "sakura-pink",
  "colors": {
    "background": "#F3C9D4",
    "highlight": "#FFA3B8"
  }
}
```

可覆盖的键只有：

- `background`
- `card`
- `text`
- `highlight`
- `muted`
- `accent`

`accent` 用于头像圆环和贴纸边框。不要在这里塞布局字段。

## 4. 时间显示

两种方式，任选其一：

**A. 传时间，显示自动推导**

```json
{
  "published_at": "2026-11-14T20:30:00+08:00",
  "timezone": "Asia/Shanghai"
}
```

图片会显示 `11-14`、`20:30`、`Saturday`。

**B. 传时间，同时指定显示文案**

```json
{
  "published_at": "2026-11-14T20:30:00+08:00",
  "display_time": {
    "date": "11-14",
    "time": "20:30",
    "weekday": "星期六"
  }
}
```

`display_time` 只影响画面文字，不改变 `published_at`。星期几可以传英文、中文或任何上游想要的字符串。

## 5. 头像与 AI 形象

头像和形象是两件事：

- `account.avatar`：左上角圆形头像。
- `character.*`：画面里的 AI 形象层，可以放底部、左侧边框或右侧边框。

当前 `black-card` 角色层是**透明立绘，默认不画描边、不开光晕**，不再用固定右下角盒子硬塞。模板里定义三套位置：

| `placement` | 锚点 | 位置 | 裁切边 | 用途 |
| --- | --- | --- | --- | --- |
| `bottom-right` | `bottom-right` | `(1024, 1342)` | `none` | 站在/坐在卡片底部 |
| `left-edge` | `top-left` | `(56, 220)` | `left` | 从左侧边缘探头 |
| `right-edge` | `top-right` | `(1024, 220)` | `right` | 从右侧边缘探头 |

角色注册表在 `assets/characters/registry.json`：

```json
{
  "dandan": {
    "name": "蛋蛋",
    "avatar": "characters/dandan/avatar.png",
    "poses": {
      "stand": "characters/dandan/poses/stand.png",
      "wave": "characters/dandan/poses/wave.png",
      "sit": "characters/dandan/poses/sit.png",
      "peek-left": "characters/dandan/poses/peek-left.png",
      "peek-right": "characters/dandan/poses/peek-right.png"
    },
    "poseMeta": {
      "wave": {"height": 360},
      "sit": {"height": 330},
      "peek-left": {"cutEdge": "left"},
      "peek-right": {"cutEdge": "right"}
    },
    "sticker": "characters/dandan/sticker.png"
  }
}
```

5 个姿势：

| `pose` | 说明 | 默认适合的 `placement` |
| --- | --- | --- |
| `stand` | 正面站立 | `bottom-right` |
| `wave` | 招手 | `bottom-right` |
| `sit` | 坐姿 | `bottom-right` |
| `peek-left` | 左扒边、半身探头 | `left-edge` |
| `peek-right` | 右扒边、半身探头 | `right-edge` |

规则：

- 只传 `character.id` / `pose` / `placement`，让仓库查注册表和模板。
- `poseMeta.cutEdge` 会自动把扒边姿势的切割侧贴到卡片边缘；不要手动传 `cutEdge`，除非你在做新姿势。
- `poseMeta.height` 用来给不同姿势单独定高度，避免同一个底部盒子里头部大小差太多。
- 默认 `outlineWidth=0`、`glowRadius=0`、`glowOpacity=0`：角色直接贴黑卡，不画黄色描边。`outlineColor=auto` 的含义不是“固定黄色”，而是取主题 `highlight`：`butter-yellow → #FFF35F`、`mist-blue → #8FD1FF`；但只有 `outlineWidth > 0` 时才生效。
- 如果确实需要角色和黑卡分离，把 `outlineWidth` 调到 1–2，并建议把 `outlineColor` 固定成 `#FFFFFF` 或中性色，避免换主题时描边跟着变色。
- 文字版心不是固定的：模板 `character.bodyBoxes` 会按 `placement` 给出正文盒，角色和正文不能重叠；QA 会检查 `character_bounds`、`character_body_overlap`、`character_header_overlap`。
- 角色越出卡片会被 `clipToCard` 裁进卡片圆角；越界同时会被 QA 记录。
- 角色 id 不存在且 `enabled: true` 时直接报错，不会悄悄换成蛋蛋。
- 显式 `character.image` 仍然优先；但此时 `poseMeta` 不会生效，需要自己传 `cutEdge` / 尺寸。

底部/左右各自的正文盒（模板默认值，plan 不用传）：

| `placement` | `x` | `y` | `w` | `h` | `maxLines` | `sizeMax` | `sizeMin` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `bottom-right` | 140 | 300 | 748 | 680 | 6 | 100 | 60 |
| `left-edge` | 360 | 300 | 640 | 850 | 8 | 84 | 54 |
| `right-edge` | 140 | 300 | 580 | 850 | 8 | 84 | 54 |

## 6. 预设

预设只是默认值包，不是固定模板。当前 5 个：

| preset | 用途 |
| --- | --- |
| `dandan-default` | 默认：无角色层，奶油黄 |
| `dandan-with-character` | 正面站立，底部 |
| `dandan-sit-bottom` | 坐姿，底部 |
| `dandan-peek-left` | 左扒边，左侧 |
| `dandan-peek-right` | 右扒边，右侧 |

`presets/dandan-default.json`：

```json
{
  "format": "image_post",
  "template": "black-card",
  "theme": "butter-yellow",
  "timezone": "Asia/Shanghai",
  "account": {
    "handle": "@蛋蛋",
    "avatar": "characters/dandan/avatar.png"
  },
  "character": {
    "enabled": false,
    "id": "dandan",
    "pose": "stand",
    "mode": "cutout"
  }
}
```

带位置的预设会把 `character.enabled`、`pose`、`placement` 一起带上；plan 里仍然可以改任何一个字段。

上游可以只传变化的部分：

```json
{
  "preset": "dandan-default",
  "theme": "mist-blue",
  "account": {"handle": "@测试号"},
  "hook": "换参数了。",
  "body": "同一个模板，昵称、颜色、时间、角色都能换。",
  "highlights": ["换参数了。", "昵称", "时间"],
  "caption": "同一个模板，换一套参数就是另一张图。",
  "published_at": "2026-11-14T20:30:00+08:00"
}
```

plan 里的字段覆盖预设；嵌套对象逐字段覆盖。预设可以复制、改名、删除，不影响渲染器。

## 7. 运行

直接按 plan 出图：

```powershell
python -m studio render --plan data\jobs\<id>.json --out data\renders\<id>.png
```

给上游插件出图（推荐当前阶段使用）：

```powershell
python -m studio render-job --job data\jobs\<id>.json
```

`render-job` 只负责创作。默认输出：

```text
data/exports/<job_id>/
  image.png
  plan.json
  result.json
  caption.txt
```

返回 JSON 里的 `output_dir`、`image`、`result`、`caption` 都是绝对路径；上游读这些字段即可。`result.json` 的 `ok` 和 `qa.errors` 必须检查。

输出 JSON 里：

- `ok: true` 才算成功；
- `metadata` 回显实际生效的 `handle`、`avatar`、`theme`、`date`、`time`、`weekday`、`character_id`、`character_pose`、`character_placement`、`preset`；
- `qa.errors` 非空时不要交付。

## 8. 这个仓库不负责的部分

- 参数怎么从上游传进来（HTTP、消息队列、函数调用由上游决定）；
- 抖音登录、浏览器会话、BGM、上传、发布、回查；
- 账号冷却、每日上限、数据复盘。

上游插件对接细节见 `INTEGRATION.md`。本文件只描述“plan 怎么画出一张确定的图”；当前 `render-job` 只出图到 `data/exports/`。发布由上游负责，本仓库不再提供发布包、发布队列或发布 worker。
