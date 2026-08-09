# AI 网文作者 Agent（第一阶段）

基于 **DeepSeek API + 本地知识库** 的网络小说大纲生成系统。

用户输入小说创意需求 → 从本地知识库按板块读取参考原文 → 注入 Prompt → 调用 DeepSeek → 生成结构化小说大纲。

## 功能特性

- 本地知识库按板块直接读取参考小说原文（txt）：世界观 / 剧情大纲 / 人物角色卡 / other
- 长原文自动截断，可选 DeepSeek 摘要压缩（默认关闭）
- DeepSeek API 调用（OpenAI SDK 兼容模式，JSON 结构化输出）
- DeepSeek 输出自动容错：代码块/前后缀剥离、截断 JSON 补全，失败时自动让模型修复一次
- 生成时按板块注入知识库原文，人物/世界观/剧情设定以用户输入和知识库为第一优先级
- 完整小说大纲：书名、梗概、世界观、角色、分卷章节计划
- 章节正文写作：可编辑页面，支持「生成本章」「从文末续写」「从光标处重写」
- 章节生成自动携带前一章结尾，保证跨章剧情连贯
- 项目存储：大纲与章节草稿整体保存到后端，下次打开直接调出，可多项目并存
- Vue3 + Vite + TypeScript 前端，一键生成大纲
- 未配置 API Key 时自动进入演示模式，返回本地示例大纲，便于先跑通全流程
- 保留多 Agent 扩展目录（`agents/`，第二阶段实现）

## 项目结构

```text
ai-novel-agent/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── config.py            # 配置管理（.env）
│   │   ├── api/novel.py         # 小说生成 / 检索接口
│   │   ├── rag/                 # loader / splitter / embedding / vector_store / retriever / build_index
│   │   ├── llm/deepseek.py      # DeepSeek 调用封装
│   │   ├── prompts/novel_prompt.py  # 白金作者 Prompt 模板
│   │   ├── schemas/novel.py     # Pydantic 请求 / 响应模型
│   │   └── services/novel_service.py # 业务编排
│   ├── knowledge/               # 本地小说知识库（世界观 / 剧情大纲 / 人物角色卡 / other）
│   ├── data/                    # 运行时生成：项目保存、压缩缓存（自动创建，不入库）
│   ├── requirements.txt
│   └── .env.example
├── frontend/                    # Vue3 + Vite + TypeScript
├── agents/                      # 未来多 Agent 扩展目录（占位）
├── docker/docker-compose.yml
└── README.md
```

## 环境准备

- Python 3.11+
- Node.js 18+（推荐 20+）
- DeepSeek API Key（[platform.deepseek.com](https://platform.deepseek.com)）

本项目不依赖 Embedding 模型即可运行；如需使用旧版向量索引功能
（`python -m app.rag.build_index`），需联网下载中文 Embedding 模型。

## 一、安装后端依赖

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
# source .venv/bin/activate

pip install -r requirements.txt
```

> 提示：如果 `torch` 安装过慢，可先执行 `pip install torch --index-url https://download.pytorch.org/whl/cpu` 安装 CPU 版，再安装其余依赖。

## 二、配置 DeepSeek API Key

```bash
cd backend
cp .env.example .env
```

编辑 `.env`，填入真实 Key：

```ini
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
```

> 不配置也可以启动：系统会以「演示模式」返回本地示例大纲。

## 三、准备知识库

当前生成流程**直接按板块读取 txt 原文**，不需要构建向量索引。
只需把参考小说原文放入对应板块目录：

```text
knowledge/
├── 世界观/xxx.txt
├── 剧情大纲/xxx.txt
├── 人物角色卡/xxx.txt
└── other/xxx.txt
```

放入后无需任何命令，重启后端即可生效。

> 旧版向量索引命令 `python -m app.rag.build_index` 仍可用（会构建 ChromaDB），
> 但当前生成流程已不再依赖它。

### 知识库板块（当前用法：按板块读取参考小说原文）

```text
knowledge/
├── 世界观/            参考小说的世界观原文（txt）：力量体系、地图、势力
├── 剧情大纲/          参考小说的剧情原文（txt）：节奏、爽点、分卷结构
├── 人物角色卡/        参考小说的人物原文（txt）：性格、关系、成长弧光
└── other/             其它参考资料（txt）
```

生成大纲与章节正文时，系统会**按板块直接读取**上述目录中的 txt 原文，
注入 Prompt 作为参考：世界观板块用于构建新作世界观，剧情大纲板块用于
学习剧情节奏，人物角色卡板块用于人物塑造，other 作为其它参考。

### 长原文压缩

小说原文通常远超上下文预算。**默认关闭压缩，直接按开头截断读取**
（每文件最多 `KNOWLEDGE_FILE_MAX_CHARS`、每板块最多 `KNOWLEDGE_CATEGORY_MAX_CHARS`），
避免大文件压缩耗时过长。

如需启用摘要压缩，在 `.env` 设置 `KNOWLEDGE_COMPRESS=true` 后重启后端：

1. 每个板块最多处理 30000 字原文，按 2500 字分块；
2. 用 DeepSeek 并发压缩每一块为高密度摘要（约 700 字/块，
   保留人名、地名、势力、能力体系、事件线、伏笔等关键信息）；
3. 压缩结果注入 Prompt（每板块最多 16000 字符），压缩结果按
   文件内容哈希缓存到 `backend/data/knowledge_cache/`，首次较慢、之后秒开；
4. 压缩失败或未配置 API Key 时自动回退为直接截断；
5. 注意：小说原文过大时首次压缩会非常慢，建议先拆分文件或调小
   `KNOWLEDGE_COMPRESS_SOURCE_MAX`。

相关配置（`.env`）：`KNOWLEDGE_COMPRESS`、`KNOWLEDGE_COMPRESS_SOURCE_MAX`、
`KNOWLEDGE_COMPRESS_CHUNK_SIZE`、`KNOWLEDGE_COMPRESS_SUMMARY_MAX`、
`KNOWLEDGE_COMPRESS_WORKERS`、`KNOWLEDGE_CATEGORY_MAX_CHARS_COMPRESSED`。

### 灵感剧情板块开关

「灵感剧情添加」目录**平时不参与生成**。需要启用时，在 `backend/.env` 中设置
`INSPIRATION_ENABLED=true` 并重启后端：

```bash
# backend/.env
INSPIRATION_ENABLED=true
```

启用后「灵感剧情添加」板块的 txt 会随其它板块一起读取注入 Prompt，
按灵感内容要求设计剧情走向；不需要时改为 `false` 并重启即可。

## 四、启动后端

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

验证：

- 健康检查：<http://localhost:8000/api/health>
- 接口文档（Swagger UI）：<http://localhost:8000/docs>

主要接口：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/novel/generate` | 生成小说大纲（RAG 检索 + DeepSeek） |
| POST | `/api/novel/retrieve` | 仅执行知识库检索，调试 RAG |
| POST | `/api/novel/chapter/generate` | 生成/续写/重写章节正文 |
| POST | `/api/novel/character-cards/generate` | 按卷生成角色卡 |
| POST | `/api/novel/titles/generate` | 生成章节标题（按卷前10章 / 根据正文） |
| GET | `/api/projects` | 列出已保存的小说项目 |
| POST | `/api/projects` | 保存（新建/更新）项目：大纲 + 章节 |
| GET | `/api/projects/{id}` | 读取完整项目 |
| DELETE | `/api/projects/{id}` | 删除项目 |
| GET | `/api/health` | 健康检查 |

`/api/novel/generate` 请求示例：

```json
{
  "title": "",
  "genre": "武侠",
  "theme": "无敌流",
  "keywords": "系统流,极道流",
  "requirement": "100万字",
  "extra_requirements": "风格参考古龙，节奏明快，不要添加感情线和引路长辈"
}
```

响应示例：

```json
{
  "success": true,
  "context": [{ "source": "世界观/example.txt", "content": "..." }],
  "outline": {
    "title": "...",
    "summary": "...",
    "world": "...",
    "characters": [{ "name": "", "role": "", "description": "" }],
    "volume_plan": [{ "volume": "", "chapters": [] }]
  }
}
```

## 五、启动前端

```bash
cd frontend
npm install
npm run dev
```

打开 <http://localhost:5173>，填写小说类型、主题、关键词、字数规模，点击「生成大纲」即可。

### 章节写作

生成大纲后点击「进入章节写作」：

1. 左侧选择卷与章节；
2. 「生成本章开头」按大纲生成正文（可先选生成字数）；
3. 正文区可直接编辑；
4. 把光标放在修改处，点击「从光标处重写」——光标前内容作为上文，重新生成光标之后的部分；
5. 「从文末续写」以编辑后的全文为上文，继续追加内容。

### 保存与调出项目

- 「保存项目」：把当前大纲和所有已写章节作为一个整体保存到后端
  （`backend/data/projects.json`），切换章节、刷新页面、重启浏览器都不会丢；
- 「打开项目」：列出所有已保存项目，点击即可把对应的大纲和章节一起调出；
- 大纲生成页也有「保存大纲为项目」按钮，可先保存大纲、稍后再写章节；
- 打开章节写作页时，会自动恢复上次编辑的项目；删除项目需在项目列表中操作。

> 前端开发服务器已将 `/api` 代理到 `http://localhost:8000`，无需额外配置。

## 六、Docker 部署（可选）

```bash
cd docker
cp ../backend/.env.example .env   # 并填入 DEEPSEEK_API_KEY
docker compose up --build
```

- 后端：<http://localhost:8000>
- 前端：<http://localhost:5173>

## 第二阶段规划：多 Agent 扩展

本项目已预留 `agents/` 目录，未来计划实现：

```text
agents/
├── planner_agent.py     # 大纲规划 Agent
├── character_agent.py   # 人物设计 Agent
├── writer_agent.py      # 章节写作 Agent
└── reviewer_agent.py    # 质量审校 Agent
```

当前版本的 `NovelService` 已作为编排入口设计，第二阶段可将各 Agent 作为独立服务挂入同一编排流程，并复用现有 RAG / LLM 基础设施。
