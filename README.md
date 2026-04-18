# 自动日报系统

一个基于 **RSS + Gemini + GitHub Actions** 的自动化日报项目。

它会定时抓取多个 RSS 源，过滤历史已处理内容，调用 Gemini 生成 Markdown 日报，并把结果按日期归档到仓库中。项目目标不是做成重平台，而是保持 **小而清晰、能长期自动跑** 的 `v0.1` 版本。

---

## 项目卖点

- **小而完整**：没有重型框架，核心链路短，适合个人维护。
- **自动闭环**：抓取、去重、摘要、归档、提交已串起来。
- **部署轻**：直接跑在 GitHub Actions 上，无需数据库或常驻服务。
- **输出稳定**：保留当前日报风格，不强行抹平个人表达。
- **可持续**：Gemini 高峰期失败时支持重试与 fallback，不至于当天完全断档。

---

## 核心流程

```text
+-------------+    +-------------+    +-------------+    +---------------+    +-------------+    +-------------+
| Actions 定时 | -> | RSS 抓取     | -> | 历史去重     | -> | Gemini 生成摘要 | -> | Markdown 归档 | -> | 提交回仓库   |
| / 手动触发   |    | collector   |    | memory      |    | analyst       |    | archiver    |    | git push    |
+-------------+    +-------------+    +-------------+    +---------------+    +-------------+    +-------------+
```

---

## 目录结构

```text
.
├─ .github/
│  └─ workflows/
│     └─ daily_briefing.yml
├─ utils/
│  ├─ analyst.py
│  ├─ archiver.py
│  ├─ collector.py
│  ├─ history.txt                    # 初始为空，运行后自动更新
│  └─ memory.py
├─ 每日简报/
│  └─ 2026/04/
│     └─ 2026-04-16-精选简报.md      # 示例输出
├─ .env.example
├─ .gitignore
├─ LICENSE
├─ main.py
├─ README.md
└─ requirements.txt
```

---

## 快速开始（推荐：先用 GitHub Actions 直接跑起来）

### 第一步：Fork 或创建你的仓库

把这个项目放到你自己的 GitHub 仓库里。

---

### 第二步：进入 GitHub Actions 配置页面

打开你的仓库后，依次进入：

```text
Settings → Secrets and variables → Actions
```

---

### 第三步：添加 Secret

在 **Secrets** 标签页点击 **New repository secret**，新增：

- **Name**：`GEMINI_API_KEY`
- **Secret**：你的 Gemini API Key

注意：

- 这里的 **Name 必须严格写成 `GEMINI_API_KEY`**
- 因为代码里读取的就是这个名字

---

### 第四步：添加 Variable（可选）

在 **Variables** 标签页点击 **New repository variable**，新增：

- **Name**：`GEMINI_MODEL`
- **Value**：`gemini-2.5-flash`

说明：

- 这里的 **Name 必须严格写成 `GEMINI_MODEL`**
- 如果你不配置它，程序也能跑，会自动回退到默认模型 `gemini-2.5-flash`

---

### 第五步：手动运行一次工作流

进入仓库顶部的 **Actions** 页面，找到对应工作流，点击 **Run workflow**，手动运行一次。

运行成功后，你应该能看到：

- `每日简报/` 下生成新的日报文件
- `utils/history.txt` 从初始空状态开始写入新的历史记录
- Actions 日志中能看到抓取、摘要、归档、提交过程

---

## 本地运行（适合开发和调试）

### 1. 克隆仓库到本地

```bash
git clone https://github.com/Small-fish-QAQ/auto-daily-briefing.git
cd auto-daily-briefing
```

解释：

- `git clone`：把 GitHub 上的仓库下载到你电脑本地
- `cd auto-daily-briefing`：进入这个项目文件夹

如果你的仓库名不是 `auto-daily-briefing`，请把命令中的目录名改成你自己的仓库名。

---

### 2. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

---

### 3. 配置本地环境变量

复制 `.env.example` 为 `.env`，然后填写你的 Gemini API Key。

`.env` 示例：

```env
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

> [!WARNING]
> `.env` 仅用于本地调试，请不要提交到 GitHub。
> 公开仓库时只保留 `.env.example`。
> 如果你使用 GitHub Actions，请在  
> `Settings → Secrets and variables → Actions`
> 中配置 `GEMINI_API_KEY`。

说明：

- `GEMINI_API_KEY`：必填
- `GEMINI_MODEL`：可选
- 如果你**不填写** `GEMINI_MODEL`，程序会自动回退到默认模型：

```text
gemini-2.5-flash
```

---

### 4. 本地执行一次

```bash
python main.py
```

运行成功后，日报默认会生成到：

```text
每日简报/YYYY/MM/YYYY-MM-DD-精选简报.md
```

历史去重文件位于：

```text
utils/history.txt
```

---

## 为什么适合部署在 GitHub Actions

- 日报任务天然是定时批处理，不需要常驻服务。
- 产物本身就是 Markdown 文件，直接提交回仓库即可。
- 依赖少，运维面小，适合个人项目长期运行。
- 失败时可直接在 Actions 日志中定位问题，也可以手动补跑。

---

## 故障与降级策略

为了避免 Gemini 高峰期导致当日完全断更，当前版本加入了简单的容错逻辑。

### 当前策略

- 当 Gemini 返回 `429`、`503` 或其他临时服务不可用信号时，系统会进行有限次重试。
- 当前默认采用简单指数退避：

```text
15s -> 45s -> 90s
```

- 如果多次重试后仍失败，不会直接中断当天产物，而是生成一份 **fallback 简报**。
- fallback 简报至少保留：
  - 来源
  - 标题
  - 原文链接
- fallback 简报仍会按原有目录结构归档，随后继续更新 `history.txt`，避免第二天重复处理同一批内容。

---

## 仓库存放策略

当前版本采用 **“源码 + 产物同仓库”** 的策略：

- 源码、workflow、历史去重文件、日报 Markdown 都放在同一个仓库中。
- 这样做的主要目的，是简化 GitHub Actions 的提交逻辑、归档逻辑和展示链路。
- 对 `v0.1` 来说，这比拆分产物仓库或引入对象存储更稳妥，也更易维护。
- 为了让公开仓库更适合阅读和 fork，当前默认只保留少量示例产物；实际运行后的历史日报会随着工作流执行继续累积。

如果后续历史日报规模继续扩大，再考虑：

- `gh-pages`
- 独立产物仓库
- 静态站展示层
- 对象存储

当前阶段不做这类复杂拆分。

---

## 环境变量

| 变量名 | 是否必填 | 说明 |
|---|---|---|
| `GEMINI_API_KEY` | 是 | Gemini API Key |
| `GEMINI_MODEL` | 否 | Gemini 模型名，默认 `gemini-2.5-flash` |

---

## 输出说明

默认输出为 Markdown 文件，保留当前项目已有的个人化表达风格，例如“统帅”“统帅锦囊”等。

归档文件头部会写入生成时间，正文通常为 Gemini 生成的精选摘要；若 Gemini 失败，则会退化为基础信息版 fallback 简报。

为了保持公开仓库简洁，当前仓库默认只保留 1 份示例日报用于展示；实际运行后，系统会继续按日期目录自动生成新的日报文件。

示例路径：

```text
每日简报/2026/04/2026-04-16-精选简报.md
```

---

## 当前限制

- 依赖 RSS 源质量，源站摘要不完整时会影响输入质量。
- 摘要风格默认偏个人化，暂未做完整模板系统。
- 目前抓取和分析流程仍是串行的，优先保证简单可维护。
- 还没有补充自动化测试。

---

## Roadmap

- [x] 基于 RSS 抓取内容
- [x] GitHub Actions 定时运行
- [x] 历史去重
- [x] Gemini 摘要生成
- [x] 失败重试与 fallback 简报
- [ ] 扩展更多 RSS / 信息源
- [ ] 支持飞书推送
- [ ] 支持 Telegram / 邮件推送
- [ ] 提供更通用的日报提示词模板
- [ ] 增加并行抓取
- [ ] 提供简单的 Web 前端

---

## 开源说明

本项目是个人维护的开源项目，欢迎提交 issue 或讨论改进思路，但不保证实时响应。

---

## License

本项目采用 `MIT License` 开源，详见仓库中的 `LICENSE` 文件。
