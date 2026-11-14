# 上游插件对接：创作工作室只负责创作

这个仓库的边界是：**接收参数 → 按模板创作 → 返回结果**。抖音登录、Cookie、浏览器脚本、BGM、发布、失败重试、发布后回查，全部由上游插件负责。

```text
上游插件
  -> 生成参数（文案/颜色/头像/昵称/时间/角色/模板）
  -> 写 job JSON
  -> python -m studio render-job
  <- 返回 image / result / plan / caption 的绝对路径
  -> 上游自己决定预览、保存、上传、发布
```

工作室不提供发布队列、不提供发布 worker、不保存账号登录态。

## 1. 上游传什么

### 最小 job

```json
{
  "job_id": "mood-20261114-231000",
  "source": "dsh-fish-dandan",
  "plan": {
    "format": "image_post",
    "template": "black-card",
    "theme": "lavender-gray",
    "hook": "今天有点困。",
    "body": "不聊冷知识了，就趴这儿看看谁在偷看。",
    "highlights": ["今天有点困。", "偷看"],
    "character": {
      "enabled": true,
      "pose": "peek-left",
      "placement": "left-edge"
    },
    "caption": "今天有点困。",
    "published_at": "2026-11-14T23:10:00+08:00"
  }
}
```

### 用已有 plan

```json
{
  "job_id": "mood-20261114-231001",
  "plan_path": "examples/pose-sit-bottom.json"
}
```

`plan_path` 相对路径优先按 job 文件所在目录解析，其次按工作室仓库根目录解析。

### 字段

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `job_id` | 是 | 输出目录名；不能含路径分隔符或文件系统保留字符；每次按钮应唯一 |
| `plan` | 二选一 | 完整 plan 对象 |
| `plan_path` | 二选一 | 已有 plan 文件路径 |
| `source` | 否 | 上游标识，默认 `upstream` |
| `idempotency_key` | 否 | 保留字段；当前创作路径不用于发布幂等 |

`publish`、`bgm`、账号 Cookie 这类字段不归工作室管；job 里带了也会被忽略。

## 2. 输出在哪里

默认：

```text
data/exports/<job_id>/
  image.png
  plan.json
  result.json
  caption.txt
```

- `image.png`：最终 1080×1440 图文。
- `plan.json`：实际生效的 plan（含预设合并结果），用于复盘。
- `result.json`：QA、metadata、artifact 路径、创建时间。
- `caption.txt`：发布页文案；上游要改文案自己处理。
- `data/exports` 已 gitignore；同一 `job_id` 默认拒绝覆盖。

也可以用 `--out-root` 输出到上游仓库：

```powershell
python -m studio render-job --job job.json --out-root C:\path\to\upstream-repo\data\studio-output
```

但推荐默认留在工作室的 `data/exports`，上游只拿返回的绝对路径。

## 3. 返回 JSON

```json
{
  "ok": true,
  "job_id": "mood-20261114-231000",
  "source": "dsh-fish-dandan",
  "output_dir": "C:\\path\\to\\dandan-creative-studio\\data\\exports\\mood-20261114-231000",
  "image": "C:\\path\\to\\dandan-creative-studio\\data\\exports\\mood-20261114-231000\\image.png",
  "result": "C:\\path\\to\\dandan-creative-studio\\data\\exports\\mood-20261114-231000\\result.json",
  "plan": "C:\\path\\to\\dandan-creative-studio\\data\\exports\\mood-20261114-231000\\plan.json",
  "caption_file": "C:\\path\\to\\dandan-creative-studio\\data\\exports\\mood-20261114-231000\\caption.txt",
  "caption": "今天有点困。",
  "qa": {"ok": true, "checks": [...], "errors": []}
}
```

上游必须检查：

- `ok` 与 `qa.ok`；
- `qa.errors` 为空；
- `image` 存在且是 1080×1440；
- `result.json` 可以二次读取。

`ok: false` 时不要展示为成功，也不要把图传给发布器。

## 4. 两种接入方式

### CLI（推荐）

```powershell
python -m studio render-job --job job.json
```

上游用 `subprocess` 调，解析 stdout JSON。工作目录设为本仓库根目录，或把本仓库加入 `PYTHONPATH`。

### Python 函数

```python
from pathlib import Path
from studio.render_job import render_job

result = render_job(
    job_path=Path("job.json"),
    project_root=Path("E:/Projects/dandan-creative-studio"),
)
```

只在同一个 Python 环境/同一台机器时使用；不要复制工作室内部代码到上游。

## 5. 上游负责什么

- 根据心情/选题决定是否创作、用什么文案、主题、角色、时间。
- 生成唯一 `job_id`。
- 调 `render-job`，处理返回 JSON。
- 展示/审核图片和文案。
- 抖音登录、Cookie、浏览器操作、BGM、上传、发布、回查、重试、冷却、数据复盘。
- 发布失败和“点了但结果未知”的对账。

## 6. 工作室不做什么

- 不登录抖音、不保存 Cookie、不操作浏览器。
- 不选 BGM、不生成发布包、不建发布队列、不跑发布 worker。
- 不自动发布、不自动重试、不写发布回执。
- 不因为下游要发布就修改 renderer 或模板。

## 7. 加内容类型

当前只有 `image_post`。以后加视频/动画时，仍然走同一个入口：

1. 在 `studio/renderers/` 新增 renderer，注册 format。
2. `render_job` 返回 `result.artifacts`；如果第一个产物不是图片，需要按新 format 扩展输出命名（当前 `image.png` 只适用于 `image_post`）。
3. 上游只需要读 `result.json` 的 artifacts，不关心工作室用了 Pillow、Remotion 还是别的东西。

## 8. 常见错误

| 错误 | 原因 | 处理 |
| --- | --- | --- |
| 输出目录已存在 | 同一个 `job_id` 重复按钮 | 上游换唯一 id，或明确 `--overwrite` |
| `job 需要 plan 对象或 plan_path` | job 里两者都没有 | 补 plan |
| `plan 不存在` | `plan_path` 写错 | 检查相对路径基准 |
| QA 失败 | 文案溢出/角色压字/越界 | 上游改参数，不要绕过 |
| 图片不是 1080×1440 | 模板/format 不对 | 检查 plan 的 format/template |
