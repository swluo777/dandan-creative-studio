# Dandan Creative Studio

蛋蛋的独立创作工作室。这里不是“一个图文脚本”，而是一条**内容生产管线**：

```text
idea / brief
  -> plan（文案、素材、角色、时间、模板）
  -> renderer（按媒介渲染）
  -> QA（尺寸、溢出、素材、字幕/音轨检查）
  -> export（图/视频 + 生效 plan + QA 结果）
```

图文只是第一个 renderer。后面的代码动画、生成式视频、实拍 + 角色合成，都会接同一套 plan / render / QA / export 接口。

**发布不在这里。** 抖音登录、Cookie、浏览器脚本、BGM、上传、发布、回查都由上游插件负责；工作室只接收参数、创作、返回结果。

## 当前能力

| 能力 | 状态 |
| --- | --- |
| `image_post` 图文 renderer | 已实现 |
| `black-card` 黑卡大字版式 | 已实现 |
| 参数化（颜色/文案/头像/昵称/时间/星期/角色） | 已实现 |
| 预设 + 参数覆盖 | 已实现 |
| 6 个配色主题 | 已实现，可切换 |
| 黄白字分层 / 高亮规则 | 已实现 |
| 可选角色层（透明立绘 / 贴纸，底部/左/右三套位置） | 已实现，5 个动作 |
| QA（尺寸、正文溢出、行数、昵称/时间越界、角色越界、角色/正文/头部重叠） | 已实现 |
| 插件创作入口：`render-job` | 已实现，输出到 `data/exports/<job_id>/`，只创作 |
| 抖音自动发布 | 不在本仓库；由上游插件负责 |
| 代码动画 / 生成式视频 / 实拍合成 | 未实现 |

### 不是网页生成

参考图是你在抖音网页手动发的；这个仓库里的成图是 **Pillow 按 `template.json` 本地渲染**出来的。LLM 只写 `hook`、`body`、`highlights`、`caption`，字体、字号、行距、卡片、头像、日期、时间、星期全部由模板控制。这样文字不会错、头像和颜色可替换、每次输出稳定。

## 拿到仓库后先跑通

需要 Python 3.11+。所有命令都在仓库根目录执行：

```powershell
python -m pip install -r requirements.txt
python -m studio themes
```

能列出 6 个主题就说明依赖和主题目录都可用。模板、预设、字体、角色素材都随仓库提交，不需要另外下载；也不需要配置抖音账号。

不要只复制 `studio/` 文件夹：模板、主题、预设、字体和角色素材都在仓库根目录，`render-job` 会按仓库根目录找它们。要分发就整仓克隆。

## 快速使用

```powershell
# 默认奶油黄
python -m studio render --plan examples\first-post.json --out examples\first-post.png

# 查看可用主题
python -m studio themes

# 带角色层（正面站立，底部）
python -m studio render --plan examples\first-post-with-character.json --out examples\first-post-with-character.png

# 坐姿 / 左扒边 / 右扒边
python -m studio render --plan examples\pose-sit-bottom.json --out examples\pose-sit-bottom.png
python -m studio render --plan examples\pose-peek-left.json --out examples\pose-peek-left.png
python -m studio render --plan examples\pose-peek-right.json --out examples\pose-peek-right.png

# 招手 / 站立
python -m studio render --plan examples\pose-wave-bottom.json --out examples\pose-wave-bottom.png
python -m studio render --plan examples\pose-stand-bottom.json --out examples\pose-stand-bottom.png

# 临时覆盖配色
python -m studio render --plan examples\first-post.json --theme sakura-pink --out examples\themes\first-post-sakura-pink.png

# 一次渲染全部主题，并生成对比拼图
python scripts\render_themes.py

# 用预设只传变化参数
python -m studio render --plan examples\first-post-preset.json --out examples\first-post-preset.png

# 换昵称、颜色、时间、角色层的参数演示
python -m studio render --plan examples\parameterized-demo.json --out examples\parameterized-demo.png

# 插件入口：只创作，输出 data/exports/<job_id>/
python -m studio render-job --job examples\render-job-sit.json

# 测试
python -m unittest discover -s tests -v
```

渲染命令会输出一段 JSON；`"ok": true` 表示 QA 通过。`metadata` 里会带实际字号、行数、高亮、角色状态、昵称、头像、日期、时间、星期和当前主题。QA 失败不会静默输出坏图：正文溢出会直接报错。

`render-job` 是给上游插件使用的入口：它只负责创作，发布由上游自己处理。默认输出：

```text
data/exports/<job_id>/
  image.png
  plan.json
  result.json
  caption.txt
```

返回 JSON 里带 `output_dir`、`image`、`result`、`plan`、`caption` 和 QA；上游读这些绝对路径即可。`data/exports` 已 gitignore。上游每次按钮应生成唯一 `job_id`；同一个 `job_id` 默认拒绝覆盖，需显式 `--overwrite`。

## 参数化

这个模板不是“写死的蛋蛋第一条”，而是一个参数化渲染函数。一条图由这些参数决定：

| 参数 | 说明 |
| --- | --- |
| 颜色 | `theme` 预设，或 `colors` 局部覆盖 |
| 文案 | `hook` / `body` / `highlights` / `caption` |
| 头像 | `account.avatar` |
| 昵称 | `account.handle` |
| 日期 | `published_at` 自动推导，或 `display_time.date` |
| 时间 | `published_at` 自动推导，或 `display_time.time` |
| 星期几 | `published_at` 自动推导，或 `display_time.weekday` |
| 是否用 AI 形象 | `character.enabled` |
| 用哪个 AI 形象 | `character.id` + `character.pose`，或 `character.image` |
| 形象放哪 | `character.placement`：`bottom-right` / `left-edge` / `right-edge` |

上游传什么就用什么；怎么传（HTTP、队列、函数调用）不在这个仓库里固化。完整字段、优先级和示例见 `PARAMETERS.md`。

当前动作库有 5 个：`stand`、`wave`、`sit`、`peek-left`、`peek-right`。`peek-left` / `peek-right` 是半身扒边，注册表里用 `poseMeta.cutEdge` 告诉渲染器把哪一边贴到卡片边缘。

预设只是默认值包，当前 5 个：`dandan-default`、`dandan-with-character`、`dandan-sit-bottom`、`dandan-peek-left`、`dandan-peek-right`。plan 里写 `"preset": "dandan-peek-left"`，再用同名字段覆盖即可；预设随时可以复制、改名、删除。

## 配色主题

当前 6 个主题都在 `themes/` 下，版式完全一样，只换颜色 token：

| 主题 id | 名称 | 背景 | 高亮 | 适合情绪 |
| --- | --- | --- | --- | --- |
| `butter-yellow` | 奶油黄 | `#E3E582` | `#FFF35F` | 日常、轻松、自嘲、第一条 |
| `sakura-pink` | 樱花粉 | `#F3C9D4` | `#FFA3B8` | 可爱、撒娇、心情好、被夸 |
| `mist-blue` | 雾霾蓝 | `#C9DCEF` | `#8FD1FF` | 冷静、技术、思考、夜晚 |
| `mint-green` | 薄荷绿 | `#CDE8D6` | `#9DEFC0` | 清新、生活、治愈、放松 |
| `apricot-orange` | 杏橙 | `#F4D2AE` | `#FFB25F` | 食欲、炸鸡、热闹、开心 |
| `lavender-gray` | 灰紫 | `#DCD6EF` | `#C9B6FF` | 安静、emo、深夜、独处 |

对比图：`examples/themes/theme-sheet.png`。

`theme` 只换颜色，不换版式。后续要加新的布局模板，放在 `templates/<新模板>/`，plan 里的 `template` 换掉即可。

严格说，当前完成的是“1 个版式 + 6 个配色主题”。如果“多模板”指多个版式（白底海报、长图、对话截图等），`templates/` 已经留好入口；加新版式不需要改渲染管线。

## 角色层与三套位置

角色层不是只能贴右下角。`black-card` 现在有三套 `placement`：

| `placement` | 效果 | 适合姿势 |
| --- | --- | --- |
| `bottom-right` | 站在/坐在卡片底部右侧 | `stand`、`wave`、`sit` |
| `left-edge` | 半身从左侧边缘探头 | `peek-left` |
| `right-edge` | 半身从右侧边缘探头 | `peek-right` |

扒边姿势在 `registry.json` 的 `poseMeta` 里标了 `cutEdge`，渲染器会自动切掉切割侧，贴到卡片圆角里。角色层默认**不画描边、不开光晕**，直接贴在黑卡上，避免黑卡上出现黄色描边或一块方形贴纸底；如果确实需要分离，再把 `outlineWidth` 调到 1–2，`outlineColor` 指定为白色或中性色。

正文版心会按位置自动避让：底部窄、左右两侧宽，具体数值在 `template.json` 的 `character.bodyBoxes`；QA 会拦角色压字、角色压头部、角色越界。

## 文案与高亮逻辑

最终可见正文 = `hook + body`，中间不加空格。

高亮不是随便挑词，而是固定三类锚点，最多 3 段：

1. **开场钩子**：`新号第一条。`
2. **身份锚点**：`蛋蛋`
3. **主题关键词**：`冷知识`

硬规则：

- 每段必须是最终正文的精确子串。
- 单段不超过 10 个字。
- 不能重叠，不能相邻。
- 最多 3 段。
- 其余支撑细节保持白色，不要整段标亮。

规则原文在 `templates/black-card/copy-prompt.md`，校验在 `studio/highlights.py`。

## 目录

```text
README.md
AGENTS.md
PARAMETERS.md
INTEGRATION.md              # 上游插件对接：只创作、不发布
studio/
  models.py              # Artifact / QAReport / RenderResult / RenderContext
  pipeline.py            # plan -> renderer 的通用入口
  renderers/
    base.py              # Renderer 协议
    image_post.py        # 第一个 renderer：黑卡大字
    registry.py          # 按 format 注册 renderer
  job_spec.py            # job 解析：plan 对象 / plan_path
  render_job.py          # 插件入口：只渲染到 data/exports/<job_id>
  highlights.py          # 高亮规则与校验
  text_layout.py         # 字体、换行、自动适配、彩色 runs
templates/
  black-card/
    template.json        # 版式、字体、角色层参数；theme 给默认主题
    copy-prompt.md       # 给 LLM 的文案/高亮规则
    schema.json          # plan 字段约束
themes/
  butter-yellow.json     # 只有颜色 token，不参与排版
  sakura-pink.json
  mist-blue.json
  mint-green.json
  apricot-orange.json
  lavender-gray.json
presets/
  dandan-default.json    # 默认值包；plan 可覆盖任何字段
  dandan-with-character.json
  dandan-sit-bottom.json
  dandan-peek-left.json
  dandan-peek-right.json
assets/
  characters/
    registry.json        # 角色 id -> 头像/5 个动作/贴纸
    dandan/              # 头像、5 个透明动作、原始角色图
  fonts/                 # Noto Sans SC（SIL OFL 1.1）
examples/
  first-post.json        # 完整参数 plan
  first-post.png
  first-post-preset.json # 只用预设 + 变化参数的 plan
  parameterized-demo.json
  parameterized-demo.png
  first-post-with-character.json
  first-post-with-character.png
  pose-sit-bottom.json/.png
  pose-peek-left.json/.png
  pose-peek-right.json/.png
  pose-wave-bottom.json/.png
  pose-stand-bottom.json/.png
  render-job-sit.json    # 插件创作 job 示例
  themes/                # 6 个主题的成图 + theme-sheet.png
tests/
scripts/
  build_assets.py        # 从角色原图生成头像、贴纸；动作立绘是审核过的资产
  render_themes.py       # 一次渲染全部主题并拼对比图
data/
  renders/               # 直接 render 的运行产物（gitignore）
  jobs/                  # 任务记录（gitignore）
  exports/               # 插件 render-job 的每 job 输出（gitignore）
```

`PARAMETERS.md` 是给上游 AI / 调度器的参数契约；`AGENTS.md` 是给后续改仓库的 AI 的执行手册。

## 架构分层

- `format` 是媒介：`image_post`、`code_animation`、`generative_video`、`real_composite`。
- `template` 是版式/视觉语言：同一个 `image_post` 可以有很多模板，同一个视频媒介也可以有很多风格。
- `theme` 是颜色 token：只换背景、卡片、文字、高亮、弱化色，不改布局。
- `preset` 是默认值包：账号、角色、主题、时区；不是固定模板，plan 里任何字段都能覆盖。
- 所有视觉输入都走 plan：颜色、文案、头像、昵称、时间、星期、角色 id、角色素材路径。上游只负责传参，不负责画图。
- `renderer` 只负责“把 plan 变成像素/视频/字幕/封面”，不负责写文案，也不负责发布。
- `render-job` 是当前给插件用的入口：只创作到 `data/exports/<job_id>/`，上游读取返回的绝对路径。
- 创作工作室的边界在这里结束：不登录抖音、不保存 Cookie、不选 BGM、不建发布队列、不运行发布脚本。
- 发布、账号、浏览器和回查属于上游插件；工作室不生成发布包，也不 import 任何发布器。
- 所有 renderer 都返回 `RenderResult`（一个或多个 `Artifact` + `QAReport`）；上游只消费 `result.json` 和图片/视频路径。
- `data/jobs` 保存本次任务的 plan，`data/exports` 保存本次创作结果，便于复盘和重跑。

## 给后续 AI 的入口

先读 `AGENTS.md`。里面有：

- 当前能力与文件地图；
- AI 写一条新图文的标准流程；
- 情绪 → 配色主题的选择表；
- plan 字段、高亮规则、角色层参数；
- 加主题、加版式、加视频 renderer 的步骤；
- 不能做的事（不自动发布、不自动 commit、不静默忽略 QA）。

然后按需读：

- `templates/black-card/copy-prompt.md`：文案怎么写。
- `templates/black-card/schema.json`：plan 字段约束。
- `PARAMETERS.md`：给上游 AI / 调度器的完整参数契约。
- `INTEGRATION.md`：上游插件如何调 `render-job`、输出目录和职责边界。
- `examples/first-post.json`：完整参数示例。
- `examples/first-post-preset.json`：只用预设 + 变化参数的示例。
- `examples/render-job-sit.json`：插件创作 job 示例。

## 计划中的 renderer

| format | 用途 | 预计产物 |
| --- | --- | --- |
| `code_animation` | Remotion / Blender / Manim 代码动画 | mp4 + 封面 + 字幕 |
| `generative_video` | 图生视频 / 文生视频模型适配 | mp4 + 关键帧 |
| `real_composite` | 实拍素材 + 角色抠像/合成为主 | mp4 + 封面 |

它们都应该返回 `RenderResult`，这样上游不需要知道视频是怎么做出来的。

## 未实现

- 视频类 renderer。
- LLM 自动写文案的调用链。
- Git 提交：已提交基础版本；后续提交前审查，不自动 commit。

抖音登录、Cookie、BGM、发布与回查不在本仓库范围内，由上游插件实现。

## Git 策略

- 进仓库：源码、模板、主题、预设、文档、测试、脚本、角色源素材与生成素材、字体与 OFL、少量示例预览图。
- 不进仓库：`data/renders/`、`data/jobs/`、`data/exports/`、`__pycache__`、虚拟环境、缓存、日志、临时文件、`.env`、`config.local.json`、编辑器本地配置。
- 示例图是人工挑选的文档预览，不是批量运行产物；批量运行产物统一写到 `data/renders/`，已被忽略。
- 当前仓库约 24.5 MB，最大单文件是 `NotoSansSC-VF.ttf`（约 17.7 MB）；暂时不用 Git LFS，仍在普通仓库范围内。

## 字体

`assets/fonts/NotoSansSC-VF.ttf` 来自 Noto Sans SC，使用 SIL Open Font License 1.1；许可证文本在 `assets/fonts/OFL.txt`。
