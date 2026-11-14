# AGENTS.md

本文件是给后续 AI / 代理的入口。先读一遍，再动手改仓库。

## 0. 一句话

这是一个**内容生产管线**，不是图文脚本。当前只实现了 `image_post` 的第一个版式 `black-card`，但目录结构已经按“多媒介 + 多模板 + 多主题”设计；不要为了做图文把架构写死。

## 1. 当前状态

已实现：

- `studio/pipeline.py`：`plan -> renderer -> RenderResult`。
- `studio/renderers/image_post.py`：Pillow 本地渲染，1080×1440，3:4。
- `templates/black-card/`：第一个图文版式，含文案规则、schema、模板参数。
- `themes/`：6 个配色主题，只换颜色 token，不改布局。
- 可选角色层：`cutout`（透明立绘）和 `sticker`（带背景圆角贴纸）；`cutout` 支持底部、左侧、右侧三套位置和 5 个动作（`stand`、`wave`、`sit`、`peek-left`、`peek-right`）。
- QA：画布尺寸、正文是否溢出、行数、高亮数量、昵称/日期/时间/星期是否超出卡片、角色是否越出卡片、角色是否压正文、角色是否压头部。
- 插件创作入口：`studio/render_job.py` + `python -m studio render-job`。只创作，输出 `data/exports/<job_id>/`（图、plan、result、caption）；不登录抖音、不建发布队列、不 import 发布器。
- 测试：`python -m unittest discover -s tests -v`。

未实现：

- 视频类 renderer：`code_animation`、`generative_video`、`real_composite`。
- LLM 自动写文案的调用链。
- Git 提交：仓库已初始化；提交前必须让用户审查，不要自动提交。

发布不在本仓库范围内。抖音登录、Cookie、浏览器脚本、BGM、上传、发布、回查由上游插件负责。

## 2. 最短使用路径

```powershell
# 默认主题：奶油黄
python -m studio render --plan examples\first-post.json --out examples\first-post.png

# 用预设只传变化参数
python -m studio render --plan examples\first-post-preset.json --out examples\first-post-preset.png

# 换昵称、颜色、时间、角色层的参数演示
python -m studio render --plan examples\parameterized-demo.json --out examples\parameterized-demo.png

# 三套角色位置 / 五个动作
python -m studio render --plan examples\pose-sit-bottom.json --out examples\pose-sit-bottom.png
python -m studio render --plan examples\pose-peek-left.json --out examples\pose-peek-left.png
python -m studio render --plan examples\pose-peek-right.json --out examples\pose-peek-right.png
python -m studio render --plan examples\pose-wave-bottom.json --out examples\pose-wave-bottom.png
python -m studio render --plan examples\pose-stand-bottom.json --out examples\pose-stand-bottom.png

# 查看可用主题
python -m studio themes

# 插件入口：只创作；输出 data/exports/<job_id>/
python -m studio render-job --job examples\render-job-sit.json

# 覆盖主题
python -m studio render --plan examples\first-post.json --theme sakura-pink --out examples\themes\first-post-sakura-pink.png

# 一次渲染全部主题 + 对比拼图
python scripts\render_themes.py

# 重建头像、贴纸（5 个动作立绘是已审核资产，不由脚本生成）
python scripts\build_assets.py

# 测试
python -m unittest discover -s tests -v
```

`render` 会输出 JSON。只有 `"ok": true` 才算通过；`qa.errors` 非空时不要交付。

## 3. 读文件顺序

1. `README.md`：项目定位、当前能力、目录。
2. `AGENTS.md`：本文件，执行规则。
3. `templates/black-card/copy-prompt.md`：文案与高亮规则。
4. `templates/black-card/schema.json`：plan 字段。
5. `templates/black-card/template.json`：版式与角色层参数。
6. `PARAMETERS.md`：给上游 AI / 调度器的完整参数契约。
7. `INTEGRATION.md`：上游插件如何调 `render-job`、输出目录与职责边界。
8. `examples/first-post.json`：完整参数示例。
9. `examples/first-post-preset.json`：预设 + 变化参数示例。
10. `examples/render-job-sit.json`：插件创作 job 示例。

改代码前先读对应的 `.py`，不要凭记忆复刻字段。

## 4. plan 契约

一条图文的最小 plan：

```json
{
  "id": "2026-11-14-first-post",
  "format": "image_post",
  "template": "black-card",
  "theme": "butter-yellow",
  "account": {
    "handle": "@蛋蛋",
    "avatar": "characters/dandan/avatar.png"
  },
  "hook": "新号第一条。",
  "body": "本鱼叫蛋蛋，蓝鲸，成年，饭量大，算力还行。以后在这儿记点没用的冷知识，和吃掉的炸鸡。",
  "highlights": ["新号第一条。", "蛋蛋", "冷知识"],
  "character": {
    "enabled": false,
    "pose": "stand"
  },
  "caption": "新号第一条。以后在这儿记点没用的冷知识，和吃掉的炸鸡。",
  "published_at": "2026-11-13T23:09:00+08:00"
}
```

字段规则：

- `format`：当前只能是 `image_post`。
- `template`：当前只能是 `black-card`；以后可以换成其他版式目录名。
- `theme`：可选；缺省用 `template.json` 的 `theme`，当前是 `butter-yellow`。命令行 `--theme` 会覆盖它。
- `colors`：可选；局部覆盖 `theme`，只支持 `background`、`card`、`text`、`highlight`、`muted`、`accent`。
- `preset`：可选；从 `presets/<id>.json` 读默认值，plan 里的同名字段覆盖预设。嵌套对象逐字段合并。
- `timezone`：可选；默认 `Asia/Shanghai`。
- `display_time`：可选；`{date,time,weekday}` 只覆盖画面文字，不改变 `published_at`。
- `account.handle`：昵称，原样显示；缺省用角色注册表的名字加 `@`。
- `account.avatar`：头像路径；缺省用角色注册表头像。
- `hook`：第一句，作为最终正文的精确前缀。
- `body`：正文，不能为空。最终可见正文 = `hook + body`；若 `body` 已经以 `hook` 开头，不会重复拼接。
- `highlights`：最多 3 段；必须是最终正文的精确子串；单段 ≤10 字；不能重叠，不能相邻。
- `character.enabled`：`true` 时叠加角色层；`mode` 可用 `cutout` 或 `sticker`。
- `character.id`：角色注册表 id，默认 `dandan`。
- `character.pose`：姿势键，默认 `stand`。
- `character.image`：显式素材路径，优先级高于 `id + pose`。
- `caption`：发布页文案；可以和正文不同。
- `published_at`：ISO 8601；缺省用渲染时刻。模板会显示日期、时间、星期。

完整参数优先级和示例见 `PARAMETERS.md`。上游怎么传参不在本仓库固化；本仓库只接受 JSON plan。

### 预设

- `presets/*.json` 是默认值包：模板、主题、账号、角色、时区。
- plan 写 `"preset": "<id>"`，同名字段覆盖预设；嵌套对象逐字段合并，数组整块替换。
- 预设里不要放具体文案；文案由上游/LLM 每次传入。
- 加预设只需要复制 JSON，不需要改代码。

## 5. 情绪 → 主题选择

不要随机选色。按这条内容想传达的情绪选：

| 情绪 / 场景 | 主题 | 名称 |
| --- | --- | --- |
| 日常、轻松、自嘲、第一条 | `butter-yellow` | 奶油黄 |
| 可爱、撒娇、心情好、被夸 | `sakura-pink` | 樱花粉 |
| 冷静、技术、思考、夜晚 | `mist-blue` | 雾霾蓝 |
| 清新、生活、治愈、放松 | `mint-green` | 薄荷绿 |
| 食欲、炸鸡、热闹、开心 | `apricot-orange` | 杏橙 |
| 安静、emo、深夜、独处 | `lavender-gray` | 灰紫 |

拿不准时用 `butter-yellow`。颜色只换 token，不改变高亮规则。

## 6. AI 写一条新图文的流程

1. 读 `templates/black-card/copy-prompt.md`，按蛋蛋的语气写 `hook`、`body`、`highlights`、`caption`。
2. 按第 5 节选 `theme`。
3. 在 `data/jobs/<id>.json` 写 plan（`data/jobs` 已在 gitignore 里，适合放运行态任务）。
4. 渲染：
   ```powershell
   python -m studio render --plan data\jobs\<id>.json --theme <theme> --out data\renders\<id>.png
   ```
   如果是给上游插件出图，用 `render-job` 而不是 `render`：
   ```powershell
   python -m studio render-job --job data\jobs\<id>.json
   ```
   它输出 `data/exports/<id>/{image.png,result.json,plan.json,caption.txt}`，只创作，不发布。
5. 读输出 JSON：
   - `ok: true` 才继续；
   - `qa.errors` 非空就改文案/角色参数，不要绕过 QA；
   - 正文溢出时优先缩文案，不要偷偷改模板字号。
6. 交付 PNG 路径和 `caption`。如果要发抖音，把结果交给上游插件；不要在本仓库做发布。

## 7. 高亮规则

固定三类锚点，通常一段一个：

1. `hook`：开场钩子。
2. `identity`：身份锚点，例如“蛋蛋”。
3. `topic`：这条内容承诺的主题。

硬规则：

- 最多 3 段。
- 每段 ≤10 字。
- 必须是 `hook + body` 的精确子串。
- 不能重叠、不能相邻。
- 其余支撑细节保持白色，不要整段标亮。

示例：`新号第一条。` / `蛋蛋` / `冷知识` 标亮；`蓝鲸`、`成年`、`饭量大`、`算力还行`、`炸鸡` 保持白色。

## 8. 角色层

角色素材在 `assets/characters/`：

- `registry.json`：角色 id -> 头像、poses、sticker 的注册表；换 AI 形象先改这里。
- `dandan/avatar-source.png`：与参考贴头像匹配的高分辨率原图。
- `dandan/avatar.png`：从 `avatar-source.png` 裁出的圆形头像，当前模板使用。
- `dandan/source.png`：全身立绘原图。
- `dandan/poses/stand.png`：透明底正面站立。
- `dandan/poses/wave.png`：招手。
- `dandan/poses/sit.png`：坐姿。
- `dandan/poses/peek-left.png`：左扒边半身。
- `dandan/poses/peek-right.png`：右扒边半身。
- `dandan/sticker.png`：带背景的贴纸，`sticker` 模式备选。

参数在 `templates/black-card/template.json` 的 `character`：

- `mode: cutout`：直接贴透明立绘，不套卡片。
- `mode: sticker`：保留原图背景，圆角 + 可选边框。
- 角色层现在有三套位置，不是固定右下角：
  - `bottom-right`：底部，`anchor=bottom-right`，盒 `320×312`；`wave` / `sit` 由 `poseMeta.height` 分别调到 360 / 330。
  - `left-edge`：左侧，`anchor=top-left`，盒 `520×380`，`cutEdge=left`。
  - `right-edge`：右侧，`anchor=top-right`，盒 `520×380`，`cutEdge=right`。
- `placements` 管位置和尺寸；`bodyBoxes` 管正文避让；`poseMeta` 管每个动作的裁切边和单独高度。
- 扒边动作的切割侧由 `registry.json` 的 `poseMeta.cutEdge` 提供；渲染器会清掉切割侧的描边/光晕，避免出现直线边。
- 默认 `outlineWidth=0`、`glowRadius=0`、`glowOpacity=0`：角色直接贴在黑卡上，不画黄色/主题色描边。深蓝头发在纯黑上会略微融边；确实需要分离时再把 `outlineWidth` 调到 1–2，并把 `outlineColor` 设成 `#FFFFFF` 或指定色，避免 `auto` 跟着主题变。
- 角色越出卡片会被 `clipToCard` 裁进卡片圆角；越界同时会被 QA 记录。
- QA 会检查 `character_bounds`、`character_body_overlap`、`character_header_overlap`。
- 换角色用 `character.id` + `character.pose` + `character.placement`；不要硬编码新角色路径。显式 `character.image` 优先级最高，但不会自动套 `poseMeta`。
- 角色 id 不存在且 `enabled: true` 时直接报错，不会静默换回蛋蛋。

### 加一个动作

1. 把透明底 PNG 放进 `assets/characters/dandan/poses/<pose>.png`，高度建议 1200px 左右。
2. 在 `registry.json` 的 `poses` 里登记。
3. 如果是扒边动作，在 `poseMeta` 里写 `cutEdge`；如果头身比例和别的动作差太多，加 `height`。
4. 加一个 `examples/pose-<pose>.json`，用 `character.placement` 指定位置。
5. 跑 `python -m studio render --plan ...` 和 `python -m unittest discover -s tests -v`，QA 全过再交付。

不要直接覆盖用户的角色原图；要改裁剪框，改 `scripts/build_assets.py` 后重新生成。

## 9. 加一个配色主题

1. 复制 `themes/butter-yellow.json` 为 `themes/<new-id>.json`。
2. 必填 `colors`：
   - `background`
   - `card`
   - `text`
   - `highlight`
   - `muted`
   - `accent`
3. 只改颜色，不要往主题文件里塞布局字段。
4. 想让它出现在对比拼图里，把 id 加到 `scripts/render_themes.py` 的 `ORDER`。
5. 更新 `README.md` 的主题表和本文件第 5 节。

主题文件结构：

```json
{
  "id": "sakura-pink",
  "name": "樱花粉",
  "mood": ["可爱", "撒娇", "心情好", "被夸"],
  "colors": {
    "background": "#F3C9D4",
    "card": "#000000",
    "text": "#FFFFFF",
    "highlight": "#FFA3B8",
    "muted": "#8A8A8A",
    "accent": "#F3C9D4"
  }
}
```

## 10. 加一个图文版式

1. 新建 `templates/<new-template>/`。
2. 至少包含：
   - `template.json`：`id`、`name`、`format: "image_post"`、`theme`、`canvas`、`palette`、`typography`、`card`、`header`、`body`、`footer`、`character`。
   - `copy-prompt.md`：这个版式的文案规则。
   - `schema.json`：plan 字段约束。
3. 在 plan 里把 `template` 换成新目录名。
4. 如果新模板需要不同的绘制逻辑，不要硬塞进 `image_post.py` 的 if/else；新建 renderer 或抽出共享绘图函数。
5. 加测试，至少覆盖：正常渲染、文字溢出、角色越界、主题覆盖。

## 11. 加一个视频 / 动画 format

1. 在 `studio/renderers/` 新建 `<format>.py`，实现 `Renderer` 协议：
   - `format` 属性；
   - `render(plan, context) -> RenderResult`。
2. 返回的 `RenderResult` 必须包含：
   - 一个或多个 `Artifact`（视频、封面、字幕、关键帧）；
   - `QAReport`（时长、分辨率、音轨、字幕、关键帧连续性等）。
3. 在 `studio/renderers/registry.py` 注册新 format。
4. 不要把视频逻辑塞进 `image_post.py`；也不要让上游发布器反向依赖具体 renderer。
5. 新 format 的 plan 可以有自己的字段，但必须保留 `format`、`template`、`caption` 这类通用字段。
6. 先做可复现的最小样片，再加自动化；不要在没跑通一条完整流程前铺大架构。

计划中的 format：

| format | 说明 |
| --- | --- |
| `code_animation` | Remotion / Blender / Manim 代码动画 |
| `generative_video` | 图生视频 / 文生视频模型适配 |
| `real_composite` | 实拍素材 + 角色抠像/合成 |

## 12. 创作边界

- 工作室的职责是：上游传 `job` → `render-job` → 返回图片/结果。到此结束。
- 当前上游插件只走 `python -m studio render-job --job <job.json>`：只创作到 `data/exports/<job_id>/{image.png,result.json,plan.json,caption.txt}`。`job_spec.py` 统一解析 `plan` / `plan_path`；job 里的 `publish` 字段会被忽略。
- 上游每次按钮应生成唯一 `job_id`；同 id 默认拒绝覆盖，需显式 `--overwrite`。
- `render-job` 不创建 `data/publish`，不 import 发布器，不生成发布包。
- 抖音登录、Cookie、浏览器脚本、BGM、上传、发布、回查、账号冷却、失败重试，全部由上游插件负责；不要把这些代码加回本仓库。
- 发布是外部副作用；本仓库不点发布、不做 live、不写发布回执。
- Git 不要自动 commit；提交前必须让用户审查。

## 13. 不能做的事

- 不要让生成式模型直接画整张图文；文字会漂移。LLM 只写 plan，Pillow 负责像素。
- 不要静默忽略 QA 失败。
- 不要为了塞下文字偷偷改模板字号；先改文案或明确改模板。
- 不要覆盖用户的原图、参考图、历史成图。
- 不要自动发布、自动 commit、自动 push；发布不属于本仓库。
- 不要把 `themes/` 做成布局模板；颜色和版式分开。
- 不要把视频 renderer 塞进图文 renderer。
- 不要把发布器、发布队列、Cookie、浏览器脚本重新引入本仓库。

## 14. 完成标准

一条图文任务完成，至少满足：

- 输出 1080×1440 PNG。
- `qa.ok: true`。
- 正文没有溢出，行数在模板上限内。
- 昵称、日期、时间、星期没有超出卡片。
- 高亮 ≤3 段，且都是精确子串。
- 如果开角色层，角色在卡片内，且没有压正文/压头部；`character_pose` 和 `character_placement` 在 `metadata` 里。
- 有 `caption`。
- 交付的是最终 PNG 路径，不是中间文件。
- 走插件入口时，`data/exports/<job_id>/result.json` 的 `ok: true`，且 `image.png`、`plan.json`、`caption.txt` 都在。
