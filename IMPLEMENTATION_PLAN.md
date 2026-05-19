# 项目实现计划：从 0 构建多 Agent 知识管理系统

## 已完成
- [x] Git 初始化 + .gitignore + 首次 commit
- [x] 架构方案文档 ARCHITECTURE.md

---

## Step 1: 基础设施——让项目能跑起来

### 目标
用 Docker 启动 PostgreSQL + pgvector，搭好 FastAPI 骨架，接上数据库，写好 LLM 调用封装。

### 你要写的文件

```
knowledge-agent/
├── docker-compose.yml          # 一行 docker compose up 启动数据库
├── backend/
│   ├── requirements.txt        # Python 依赖包列表
│   ├── config.py               # 所有配置（数据库地址、模型路由、embedding参数）
│   ├── main.py                 # FastAPI 入口文件，一个简单的 health 接口
│   └── db/
│       ├── init.sql            # 数据库初始化 SQL（启用 pgvector 扩展）
│       ├── database.py         # SQLAlchemy 异步连接 + 建表函数
│       └── models.py           # 数据表模型（Document、Chunk、UserInterest、AgentMessage）
```

### 每个文件要理解的关键问题

| 文件 | 面试官会问什么 |
|------|-------------|
| `docker-compose.yml` | 为什么用 pgvector 镜像？版本号为什么选 pg17？ |
| `config.py` | 为什么用 pydantic-settings？模型路由为什么要在这个文件里定义？ |
| `database.py` | 为什么用 async 而不是 sync？连接池大小怎么定的？ |
| `models.py` | 为什么 chunks 表和 documents 表要分开？pgvector 的索引类型为什么选 HNSW？ |

### Step 1 做完后的效果
- `docker compose up -d` → 数据库启动
- `uvicorn main:app --reload` → 后端启动
- `curl http://localhost:8000/health` → 返回 `{"status": "ok"}`

### 提交点
```
git add -A
git commit -m "feat: Step 1 基础设施 —— Docker+FastAPI+数据库+LLM封装"
```

---

## Step 2: 文档处理管线——把文档变成可检索的向量

### 目标
写一套完整的 ingestion pipeline：接收文档 → 解析文本 → 语义分块 → 生成 embedding → 存入数据库。

### 你要写的文件

```
backend/ingestion/
├── parser.py       # 文档解析器（HTML、Markdown、纯文本）
├── chunker.py      # 语义分块（按段落/标题边界切分，而非固定 token 数）
└── embedder.py     # Embedding 生成器（bge-m3：dense + sparse 双向量）
```

### 每个文件要理解的关键问题

| 文件 | 面试官会问什么 |
|------|-------------|
| `parser.py` | 不同格式的解析策略有什么不同？为什么要保留元数据（标题、来源、时间）？ |
| `chunker.py` | 为什么用语义分块而不是固定大小的滑动窗口？overlap 设为 10% 的依据？ |
| `embedder.py` | bge-m3 跟 OpenAI embedding 的区别？为什么要同时生成 dense 和 sparse 向量？ |

### 提交点
```
git add -A
git commit -m "feat: Step 2 文档处理管线 —— 解析+分块+embedding"
```

---

## Step 3: RAG 核心——混合检索 + 重排

### 目标
实现查询的完整链路：用户问题 → dense 检索 → sparse 检索 → RRF 融合 → LLM 重排 → 返回 top-k。

### 你要写的文件

```
backend/retrieval/
├── hybrid_search.py    # 混合检索：dense(pgvector) + sparse(tsvector) + RRF融合
├── reranker.py         # 重排：用 LLM 对候选文档打分 + 给理由
└── retriever.py        # 检索编排：串联召回→融合→重排的完整流程
```

### 难点与关键问题

| 问题 | 自己要想明白的 |
|------|-------------|
| RRF 的 k=60 是什么意思？ | 不同 k 值对融合效果的影响 |
| LLM 重排为什么不用 cross-encoder？ | 延迟 vs 精度的 trade-off |
| sparse 通路为什么用 tsvector 而不是外挂 BM25？ | 跟 pgvector 一个库，少一套基础设施 |

### 提交点
```
git add -A
git commit -m "feat: Step 3 RAG核心——混合检索+RRF融合+LLM重排"
```

---

## Step 4: 记忆系统——短期 + 长期 + 上下文装配

### 目标
实现完整的记忆系统：会话级短期记忆、用户兴趣级长期记忆、艾宾浩斯启发式衰减、prefix-cache 友好的上下文装配。

### 你要写的文件

```
backend/memory/
├── short_term.py       # 短期记忆：会话管理、检索上下文追踪、自动摘要
├── long_term.py        # 长期记忆：兴趣建模（事实/推导/偏好）、写入触发、矛盾检测
├── decay.py            # 记忆衰减：基于时间和访问频率的权重衰减
backend/context/
└── assembler.py        # 上下文装配：分层装配（静态在前、动态在后）
```

### 面试重点

| 问题 | 必须能讲清楚 |
|------|-----------|
| 记忆怎么分类？ | 事实型（高置信直接写）、推导型（不存）、偏好型（存但标置信度） |
| 什么触发记忆写入？ | 显式触发、会话结束摘要、阈值触发、矛盾检测 |
| 记忆放在 context 的哪个位置？ | 最前面！变化少→prefix cache 命中率高 |
| 记忆更新太频繁有什么问题？ | 破坏 prefix cache，成本飙升 |
| 记忆衰减 vs 删除？ | 衰减不删除，超过 90 天休眠但可被显式唤醒 |

### 提交点
```
git add -A
git commit -m "feat: Step 4 记忆系统——短期+长期+衰减+上下文装配"
```

---

## Step 5: 评估体系——能证明项目是好的

### 目标
构造评估数据集，建立可复现、可自动化的评估流程。面试官问"你的准确率怎么算的"时能讲清楚。

### 你要写的文件

```
backend/eval/
├── test_queries.json     # 50 个测试查询，覆盖 5 类意图
├── eval_retrieval.py     # 检索质量评估：MRR、Hit Rate@5、NDCG@5
└── eval_agent.py         # Agent 质量评估：来源标注率、矛盾检测率、回答相关性
benchmark/
└── compare.py            # pgvector vs ChromaDB 对比实验脚本
```

### 测试集设计（自己手动标注）

| 意图类型 | 例子 | 数量 |
|---------|------|------|
| 精确查找 | "我之前收藏的那篇 Anthropic Building Effective Agents" | 10 |
| 语义查找 | "关于 agent memory 设计有什么文章" | 10 |
| 跨文档关联 | "那篇讲 prompt caching 的文章和 agent memory 有什么联系" | 10 |
| 时间范围 | "上周我看过哪些关于 RAG 的内容" | 10 |
| 否定查询 | "关于 React 框架的文章"（知识库里没有） | 10 |

### 提交点
```
git add -A
git commit -m "feat: Step 5 评估体系——检索eval+Agent eval+数据库对比"
```

---

## Step 6: 多 Agent 协同——这个项目的灵魂

### 目标
实现 4 个 Agent 的协商式协作。每个 Agent 有不同的系统提示词、不同的工具集、不同的模型。Agent 之间通过 MessageBus 通信，由 Orchestrator 协调协商回合。

### 你要写的文件

```
backend/core/
├── message_bus.py       # Agent 间结构化消息通信
├── orchestrator.py      # 多轮协商协议引擎
backend/agents/
├── base.py              # BaseAgent：模型路由、工具注册、消息收发
├── collector.py         # Collector：抓取文章，走 ingestion pipeline
├── curator.py           # Curator：分类、评分、去重判断
├── librarian.py         # Librarian：混合检索、重排、存储管理
└── editor.py            # Editor：问答综合、日报生成
```

### 真正的多 Agent 通信示例（代码里要实现的样子）

```
1. Collector 抓完文章 → 发给 Curator
2. Curator 收到后 → 向 Librarian 发查重请求
3. Librarian 检索 → 返回相似度 → Curator 决策
4. Librarian 发现存储压力大 → 主动要求 Curator 提高收录门槛
5. 用户提问 → Editor 向 Librarian 检索 → 综合回答 → 标注来源+矛盾
```

### 提交点
```
git add -A
git commit -m "feat: Step 6 多Agent协同——Collector+Curator+Librarian+Editor"
```

---

## Step 7: 前端——面试官能体验的界面

### 目标
用 Next.js + React + TailwindCSS 构建前端。核心页面 3 个：知识搜索+问答、Agent 实时活动监控、每日简报。

### 你要写的文件

```
frontend/src/
├── app/
│   ├── page.tsx             # 首页：文档上传 + 知识搜索
│   └── layout.tsx
├── components/
│   ├── DocumentUpload.tsx   # 文档上传组件
│   ├── KnowledgeSearch.tsx  # 搜索框 + 问答结果展示
│   ├── AgentMonitor.tsx     # SSE 实时 Agent 活动面板
│   ├── DailyBriefing.tsx    # 每日简报展示
│   ├── InterestProfile.tsx  # 用户兴趣雷达图
│   └── MemoryViewer.tsx     # 系统记忆查看器
└── lib/
    └── api.ts               # 后端 API 调用封装
```

### 提交点
```
git add -A
git commit -m "feat: Step 7 前端——搜索+Agent监控+简报展示"
```

---

## Step 8: 部署 + 文档 + 开源

### 目标
部署到公网，写好 README 和 CLAUDE.md，推到 GitHub。让面试官能在线体验你的项目。

### 任务清单

| 任务 | 怎么做 |
|------|--------|
| 后端部署 | Railway 或 Render，一键连 GitHub 自动部署 |
| 前端部署 | Vercel，`vercel --prod` 或连 GitHub |
| bge-m3 部署 | HuggingFace Inference Endpoint 或用 CPU 本地跑 |
| README.md | 写清楚：场景、架构图、技术选型 why、怎么跑起来、面试话题索引 |
| CLAUDE.md | 写清楚项目结构，让我（AI Coding 工具）能索引项目上下文 |
| 推到 GitHub | `git remote add origin <你的仓库地址>` → `git push -u origin main` |

### 提交点
```
git add -A
git commit -m "docs: README+CLAUDE.md+部署配置"
git push origin main
```

---

## 全局 Commit 历史（面试官看到的样子）

```
5fa843d init: 项目初始化，架构方案
xxxxxxx feat: Step 1 基础设施 —— Docker+FastAPI+数据库+LLM封装
xxxxxxx feat: Step 2 文档处理管线 —— 解析+分块+embedding
xxxxxxx feat: Step 3 RAG核心 —— 混合检索+RRF融合+LLM重排
xxxxxxx feat: Step 4 记忆系统 —— 短期+长期+衰减+上下文装配
xxxxxxx feat: Step 5 评估体系 —— 检索eval+Agent eval+数据库对比
xxxxxxx feat: Step 6 多Agent协同 —— Collector+Curator+Librarian+Editor
xxxxxxx feat: Step 7 前端 —— 搜索+Agent监控+简报展示
xxxxxxx docs: README+CLAUDE.md+部署配置
```

面试官从 commit 历史就能看出：这个人是真的从 0 一步步搭起来的，每一步都有清晰的目的。
