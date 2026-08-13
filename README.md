# AI 网文作者 Agent

基于 **DeepSeek API + 本地知识库** 的网络小说大纲与章节正文生成系统。

你提供小说创意需求（类型、主题、关键词、字数、其他要求、txt 附件），系统从本地知识库按板块读取参考小说原文注入 Prompt，调用 DeepSeek 生成结构化大纲，并支持按卷生成章节标题、角色卡、可编辑的章节正文（续写 / 从修改处重写），大纲与章节可整体保存、随时调出。

---

## 功能特性

- **大纲生成**：按用户输入（类型 / 主题 / 关键词 / 字数 / 其他要求 / txt 附件）生成书名、梗概、世界观、角色、分卷计划；
- **卷章规划**：总章数 = 总字数 ÷ 每章字数（默认 4000），卷数随总章数自动规划（默认 3~8 卷），目录由系统生成，数量严格准确；
- **章节标题**：按卷分批生成前 10 章的具体标题，或根据已写正文重新生成单章标题；
- **角色卡**：按卷生成主要人物角色卡，可编辑、随项目保存，章节生成时按角色卡约束角色言行；
- **章节正文**：首次生成 / 从文末续写 / 从光标处重写；自动携带**前一章结尾**，保证跨章剧情连贯；
- **知识库驱动**：人物、世界观、剧情设定**以用户输入和知识库文本为第一优先级**，不预设角色类型；
- **项目存储**：大纲 + 全部章节 + 角色卡作为一个项目保存到后端，多项目并存，下次打开直接调出；
- **防丢失**：表单、正文、附件实时保存到浏览器本地，刷新不丢；
- **纯文本生成模式**：不依赖向量库 / Embedding 模型，安装轻量、启动快。

## 系统架构

```text
前端 Vue3 + Vite + TypeScript
        │  HTTP / JSON
        ▼
FastAPI 后端
  ├─ api/novel.py        大纲 / 章节 / 标题 / 角色卡 / 检索接口
  ├─ api/projects.py     项目保存 / 列表 / 读取 / 删除
  ├─ api/agents.py       多 Agent 接口（plan / characters / write / review / pipeline）
  ├─ agents/             多 Agent 层（Planner → Character → Writer → Reviewer）
  ├─ services/           业务编排（大纲、章节、标题、角色卡、项目、知识库压缩）
  ├─ prompts/            DeepSeek Prompt 模板（大纲、章节、标题、角色卡、压缩）
  ├─ rag/loader.py       按板块读取知识库 txt
  └─ llm/deepseek.py     OpenAI 兼容的 DeepSeek 调用 + JSON 容错
```

生成流程：

```text
用户输入（表单 + 可选 txt 附件）
        │
        ▼
读取 knowledge/ 板块 txt（世界观 / 剧情大纲 / 人物角色卡 / other）
        │  按板块截断（默认每文件 2000 字、每板块 8000 字），可选摘要压缩
        ▼
拼接 Prompt（用户输入优先 + 知识库参考 + 前一章结尾 + 角色卡）
        │
        ▼
DeepSeek 生成 → JSON/正文容错解析 → 返回前端
```

## 目录结构

```text
ai-novel-agent/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── config.py            # 配置管理（.env）
│   │   ├── api/                 # novel.py / projects.py / agents.py 路由
│   │   ├── agents/              # 多 Agent 层（协议 / Context / Agent / 编排器）
│   │   ├── rag/loader.py        # 知识库板块读取
│   │   ├── llm/deepseek.py      # DeepSeek 调用封装
│   │   ├── prompts/             # 各生成环节 Prompt 模板
│   │   ├── schemas/             # Pydantic 请求 / 响应模型
│   │   └── services/            # 业务编排
│   ├── knowledge/               # 本地知识库（世界观 / 剧情大纲 / 人物角色卡 / other）
│   ├── data/                    # 运行时生成：项目保存、压缩缓存（自动创建）
│   ├── requirements.txt
│   └── .env.example
├── frontend/                    # Vue3 + Vite + TypeScript
├── agents/                      # 多 Agent 占位说明（实现位于 backend/app/agents/）
├── docs/                        # 架构 / 集成 / 多 Agent 文档
├── docker/                      # Dockerfile 与 docker-compose.yml
└── README.md
```

## 环境要求

- Python 3.11+（推荐 3.12）
- Node.js 18+（推荐 20+）
- DeepSeek API Key（[platform.deepseek.com](https://platform.deepseek.com)）

> 本项目不依赖 Embedding 模型 / 向量数据库，安装体积小。

## 快速开始

### 1. 安装后端依赖

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. 配置 DeepSeek API Key

```bash
cd backend
cp .env.example .env
```

编辑 `.env`，填入真实 Key：

```ini
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
```

> 不配置也可以启动：系统会以「演示模式」返回本地示例内容，便于先跑通全流程。

### 3. 准备知识库（可选但推荐）

把参考小说原文按板块放入 `backend/knowledge/`：

```text
knowledge/
├── 世界观/xxx.txt          # 力量体系、地图、势力 → 用于构建新作世界观
├── 剧情大纲/xxx.txt        # 剧情推进、节奏、爽点 → 用于学习剧情设计
├── 人物角色卡/xxx.txt      # 人物性格、关系、成长 → 用于人物塑造
└── other/xxx.txt           # 其它参考
```

放入后**无需任何命令**，重启后端即可生效。

### 4. 启动后端

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

验证：

- 健康检查：<http://localhost:8000/api/health>
- 接口文档（Swagger UI）：<http://localhost:8000/docs>

### 5. 启动前端

```bash
cd frontend
npm install
npm run dev
```

打开 <http://localhost:5173>。

### 一键启动（Windows）

- `start.bat`：同时启动后端（8000）与前端（5173）
- `start_backend.bat` / `start_frontend.bat`：分别启动
- `start_backend_verbose.bat`：前台运行后端，便于查看报错
- `start_services.ps1` / `stop_services.ps1`：重启 / 停止服务
- `check_backend.bat`：检查后端健康状态

## 配置说明（backend/.env）

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | 空 | DeepSeek API Key，必填（否则演示模式） |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com/` | API 地址 |
| `DEEPSEEK_MODEL` | `deepseek-chat` | 模型名；如报“模型不存在”请确认该值 |
| `DEEPSEEK_TEMPERATURE` | `0.7` | 生成随机性 |
| `DEEPSEEK_MAX_TOKENS` | `8192` | 输出上限；大纲章节较多时可调大 |
| `DEEPSEEK_TIMEOUT` | `120` | API 请求超时（秒） |
| `DEEPSEEK_AUTO_REPAIR_JSON` | `true` | 返回非法 JSON 时自动让模型修复一次 |
| `KNOWLEDGE_DIR` | `./knowledge` | 知识库根目录 |
| `KNOWLEDGE_CATEGORY_MAX_CHARS` | `8000` | 每个板块最多注入的字符数（不压缩时） |
| `KNOWLEDGE_FILE_MAX_CHARS` | `2000` | 单个 txt 文件最多注入的字符数 |
| `KNOWLEDGE_COMPRESS` | `false` | 是否对长原文做 DeepSeek 摘要压缩（大文件首次很慢，谨慎开启） |
| `KNOWLEDGE_COMPRESS_SOURCE_MAX` | `30000` | 每个板块最多参与压缩的原文长度 |
| `KNOWLEDGE_COMPRESS_CHUNK_SIZE` | `2500` | 压缩分块大小 |
| `KNOWLEDGE_COMPRESS_SUMMARY_MAX` | `700` | 每块摘要目标字数 |
| `KNOWLEDGE_COMPRESS_WORKERS` | `4` | 压缩并发线程数 |
| `KNOWLEDGE_CATEGORY_MAX_CHARS_COMPRESSED` | `16000` | 压缩后每板块注入上限 |
| `INSPIRATION_ENABLED` | `false` | 是否让「灵感剧情添加」板块参与生成 |
| `OUTLINE_CHAPTER_WORDS` | `4000` | 每章标准字数（总章数 = 总字数 ÷ 此值） |
| `OUTLINE_CHAPTERS_PER_VOLUME` | `30` | 约每多少章分一卷 |
| `OUTLINE_VOLUME_MIN` / `OUTLINE_VOLUME_MAX` | `3` / `8` | 卷数上下限 |
| `OUTLINE_DEFAULT_TOTAL_WORDS` | `1000000` | 解析不出字数时的默认总字数 |
| `APP_NAME` | `AI 网文作者 Agent` | 应用名 |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | 允许的前端来源 |

## 知识库使用指南

### 板块与作用

| 板块 | 内容 | 生成时的作用 |
| --- | --- | --- |
| `世界观/` | 参考小说的世界观原文 | 构建新作的力量体系、地图、势力与背景 |
| `剧情大纲/` | 参考小说的剧情原文 | 学习分卷结构、节奏、爽点、悬念伏笔 |
| `人物角色卡/` | 参考小说的人物原文 | 学习人物塑造方法 |
| `other/` | 其它参考文本 | 按需吸收 |

### 读取规则

- 只读取 `.txt` 文件；
- 默认不压缩：每个文件取开头 2000 字、每个板块累计最多 8000 字，超出截断并标注；
- 需要更多内容时调大 `KNOWLEDGE_FILE_MAX_CHARS` / `KNOWLEDGE_CATEGORY_MAX_CHARS`（注意模型上下文预算）；
- 长原文压缩为可选功能（`KNOWLEDGE_COMPRESS=true`），压缩结果按文件哈希缓存到 `backend/data/knowledge_cache/`；
- 「灵感剧情添加」目录平时不参与生成，设置 `INSPIRATION_ENABLED=true` 后随其它板块一起注入。

### 重要原则

人物、世界观、剧情设定**完全以用户输入和知识库文本为第一优先级**：
模型不会预设“女主”“导师”等角色类型，只设计知识库和输入中明确出现或剧情合理需要的人物。

## 功能使用流程

### 1. 生成大纲

填写：小说类型（默认武侠）、主题（默认无敌流）、关键词（默认系统流,极道流）、字数规模、其他要求，可选上传本地 txt 附件（内容视为最高优先级素材）。

点击「生成大纲」后：

- 系统按字数规划卷章数（例如 100 万字 → 250 章 / 8 卷），目录自动生成；
- 结果可查看知识库实际注入的内容；
- 点「保存大纲为项目」把大纲存入后端，或直接「进入章节写作」。

### 2. 生成章节标题

大纲页每个卷有「生成前 10 章标题」按钮：AI 分批生成该卷前 10 章的具体标题并替换编号目录；其余章节保持编号。

### 3. 生成 / 编辑角色卡

章节写作页切换到「角色卡」：

- 选择卷 → 「AI 生成本卷角色卡」；
- 每张卡可编辑：姓名、定位、年龄、外貌、性格、背景、目标、说话风格、备注；
- 可手动「添加角色卡」或删除；
- 角色卡随「保存项目」持久化，生成正文时按卡片约束角色言行。

### 4. 生成章节正文

- 左侧选择卷与章节；
- 「生成本章开头」：按大纲 + 前一章结尾 + 本卷角色卡 + 知识库生成；
- 「从文末续写」：以编辑后的全文为上文继续追加；
- 「从光标处重写」：把光标放在修改处，光标前内容作为上文，重新生成光标后内容并替换；
- 「根据正文生成标题」：按当前正文重新设计章节标题；
- 可选手生成字数（300/600/800/1200/2000），可填写其他要求，可上传章节级 txt 附件。

### 5. 保存与调出项目

- 「保存项目」：大纲 + 所有章节 + 角色卡整体保存到 `backend/data/projects.json`；
- 「打开项目」：列出全部项目，点击整体调出；
- 打开章节写作页时自动恢复上次项目；
- 表单、正文、附件实时保存在浏览器本地，刷新不丢。

## API 参考

基础地址：`http://localhost:8000`

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/novel/generate` | 生成小说大纲 |
| POST | `/api/novel/chapter/generate` | 生成 / 续写 / 重写章节正文 |
| POST | `/api/novel/titles/generate` | 生成章节标题（按卷前 10 章 / 根据正文） |
| POST | `/api/novel/character-cards/generate` | 按卷生成角色卡 |
| POST | `/api/novel/retrieve` | 查看知识库按板块读取（压缩后）的内容 |
| GET | `/api/projects` | 列出已保存项目 |
| POST | `/api/projects` | 保存（新建 / 更新）项目 |
| GET | `/api/projects/{id}` | 读取完整项目 |
| DELETE | `/api/projects/{id}` | 删除项目 |
| GET | `/api/health` | 健康检查 |

### 生成大纲示例

```json
POST /api/novel/generate
{
  "title": "",
  "genre": "武侠",
  "theme": "无敌流",
  "keywords": "系统流,极道流",
  "requirement": "100万字",
  "extra_requirements": "节奏明快，不要添加感情线和引路长辈",
  "attachment_name": "设定.txt",
  "attachment_text": "主角必须姓沈，金手指是武学熔炉。"
}
```

响应中的 `outline` 结构：

```json
{
  "title": "拟定的小说书名",
  "summary": "全书核心梗概",
  "world": "世界观设定",
  "characters": [{ "name": "", "role": "", "description": "" }],
  "volume_plan": [{ "volume": "第一卷", "chapters": ["第一章", "第二章"] }]
}
```

## Docker 部署（可选）

```bash
cd docker
cp ../backend/.env.example .env   # 填入 DEEPSEEK_API_KEY
docker compose up --build
```

- 后端：<http://localhost:8000>
- 前端：<http://localhost:5173>

compose 已挂载 `../backend/knowledge`（知识库）与 `../backend/data`（项目 / 缓存），数据不会因容器重建丢失。

## 常见问题（FAQ）

### 生成时提示“无法连接到 DeepSeek API”

检查网络能否访问 `https://api.deepseek.com`；需要代理时请配置系统代理，或调大 `DEEPSEEK_TIMEOUT`。

### 提示“DeepSeek 返回内容不是合法 JSON”

系统已内置多种容错（代码块剥离、截断补全、自动修复）。仍失败时：调大 `DEEPSEEK_MAX_TOKENS`，或在“其他要求”中让模型精简输出。

### 生成结果还是出现“女主 / 导师”等角色

请确认后端已重启加载最新代码，且知识库中没有相关内容；当前 Prompt 明确禁止预设这些角色类型。

### 知识库放了 txt 但生成时没生效

- 确认文件是 `.txt` 且放在对应板块目录；
- 确认文件为 UTF-8 编码（GBK 也会自动尝试读取）；
- 重启后端；
- 调用 `POST /api/novel/retrieve` 查看实际注入的内容。

### 卷 / 章数量不对

总章数 = 总字数 ÷ `OUTLINE_CHAPTER_WORDS`（默认 4000），由系统程序化生成目录，数量严格准确；调整字数或 `OUTLINE_*` 配置后重启后端。

### 章节之间剧情不连贯

生成正文时会自动携带前一章结尾；请先写 / 生成前一章再生成下一章。

### API Key 会不会泄露

`.env` 已被 `.gitignore` 忽略，不会进入 Git；请勿把真实 Key 提交到仓库。

## 多 Agent 扩展（第二阶段）

多 Agent 小说创作系统已实现，新增入口（不改变原有接口）：

- `POST /api/agents/plan`：Planner Agent 生成结构化小说规划；
- `POST /api/agents/characters`：Character Agent 建立人物系统（档案 + 状态 + 关系）；
- `POST /api/agents/write`：Writer Agent 生成章节正文；
- `POST /api/agents/review`：Reviewer Agent 审校章节；
- `POST /api/agents/pipeline`：完整流程（规划 → 人物 → 写作 → 审校 → 必要时修订循环）；
- `POST /api/agents/pipeline/async` + `GET /api/agents/runs/{run_id}`：异步执行与进度轮询；
- `POST /api/agents/sequence`：连续章节创作（自动继承人物状态 / 记忆 / 时间线）。

未配置 API Key 时全部返回演示结果；审校失败默认最多修订 2 次（`AGENT_MAX_REVISIONS`），
达到上限返回最高分版本并显式标记 `revision_exhausted`。每章完成后 MemoryAgent 更新
人物状态与长期事实、TimelineAgent 维护时间线（均可通过环境变量关闭）。

前端大纲生成页已提供“一键 Pipeline（多 Agent）”入口：选择连续章数后异步启动，
实时显示当前阶段 / Agent / 修订次数 / 审校评分，完成后自动保存项目并可进入章节写作。

详细说明见 [docs/multi-agent.md](docs/multi-agent.md)、[docs/pipeline.md](docs/pipeline.md)、
[docs/memory.md](docs/memory.md)、[docs/architecture.md](docs/architecture.md)、[docs/integration.md](docs/integration.md)。

## License

本项目仅供学习交流使用，未附带开源许可证；引用或再分发请注明出处并自行承担合规责任。
