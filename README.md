# Knowledge Agent — 多 Agent 协同知识管理系统

一个基于多 Agent 协同的个人知识管理与深度研究助手，支持文档处理、混合检索、长期记忆建模和 Agent 间协商通信。

## 一句话定位

**ChatGPT 直接对话解决不了**——因为需要一个持续增长的个人知识库、自动化定时收集、兴趣模型随时间演化、跨文档关联发现。

## 核心能力

- 📄 **文档处理管线**：HTML/Markdown/Text 解析 → 语义分块 → bge-m3 embedding（dense + sparse 双向量）
- 🔍 **混合检索**：pgvector 向量检索 + tsvector 全文检索 → RRF 融合 → LLM 重排
- 🧠 **记忆系统**：短期记忆（会话级）+ 长期记忆（兴趣建模，艾宾浩斯启发式衰减）
- 🤖 **多 Agent 协同**：Collector（抓取）/ Curator（策展）/ Librarian（检索）/ Editor（回答）通过 MessageBus 协商通信
- 📊 **评估体系**：MRR / HitRate@5 / NDCG@5 检索质量评估
- ⚡ **实时监控**：SSE 推送 Agent 间通信，前端可视化协商过程

## 架构概览

```
用户消息
  ↓
Orchestrator 广播 → 4 个 Agent 各自判断是否参与
  ├─ Collector：抓取 URL / 保存文档
  ├─ Curator：查重、评估质量、记录主题
  ├─ Librarian：混合检索知识库
  └─ Editor：综合回答、判断信息充分性
  ↓
MessageBus → SSE → 前端实时监控面板
```

### 为什么是多 Agent 而不是单 Agent？

每个 Agent 有不同的 system prompt、不同的工具集、不同的模型路由。Librarian 专注检索策略，Editor 专注综合写作，Curator 专注内容质量判断——独立上下文避免了单 Agent 的 prompt 膨胀和视角污染。Agent 之间通过 `@agent名` 动态决定协作对象，不是固定 Workflow。

## 技术选型（每一个都有 why）

| 技术 | 为什么用它 | 为什么不用别的 |
|------|----------|-------------|
| PostgreSQL + pgvector | 一个数据库解决结构化存储 + 向量检索 + 全文检索 | 不用 Milvus/ChromaDB：个人知识库数据量不需要分布式；不用 MySQL：PG 是 2026 新项目默认 |
| bge-m3 | 原生 dense + sparse 双向量输出，中英双语最优 | 不用 OpenAI embedding：中文效果不如 bge-m3，且需要额外搭 BM25 |
| 自建 Agent 编排 | 可以解释每一行设计决策 | 不用 LangGraph：4 Agent 通信模式自定义，自建展示对协商逻辑的理解 |
| DeepSeek API | 兼容 OpenAI SDK，中文能力强 | 可替换为 Claude/GPT，改 config 即可 |
| 不用 Redis | 无分布式场景，用户数据不应被当作缓存 | 单用户场景下 PG 完全够用 |
| SSE（非 WebSocket） | 单向推送 Agent 消息到前端，更轻量 | 此场景不需要双向通信 |

## 快速启动

### 1. 环境准备

```bash
conda create -n knowledge-agent python=3.12 -y
conda activate knowledge-agent
pip install -r backend/requirements.txt
```

### 2. 启动 PostgreSQL + pgvector

```bash
# macOS (Homebrew)
brew install pgvector
brew services start postgresql

# 或 macOS (conda)
conda install -c conda-forge postgresql pgvector -y
initdb ~/pgdata
pg_ctl -D ~/pgdata -l ~/pgdata/logfile start

createdb knowledge_agent
psql -d knowledge_agent -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql -d knowledge_agent -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
psql -d knowledge_agent -c "CREATE USER knowledge WITH PASSWORD 'knowledge123';"
psql -d knowledge_agent -c "GRANT ALL PRIVILEGES ON DATABASE knowledge_agent TO knowledge;"
psql -d knowledge_agent -c "GRANT ALL ON SCHEMA public TO knowledge;"
```

### 3. 配置 API Key

```bash
cp backend/.env.example backend/.env
# 编辑 .env，填入 DEEPSEEK_API_KEY=sk-xxx
```

### 4. 启动后端

```bash
cd backend
uvicorn main:app --reload
# http://localhost:8000/docs 查看 API 文档
```

### 5. 启动前端

```bash
cd frontend
npm install
npm run dev
# http://localhost:3000
```

### 6. 填充种子数据（可选）

```bash
cd backend
python test_pipeline.py          # 加载 4 篇种子文档
python eval/eval_retrieval.py    # 跑检索评估对比
```

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/chat` | POST | 用户对话（自动路由到合适的 Agent） |
| `/negotiate` | POST | 多 Agent 协商（返回完整通信记录） |
| `/negotiate/stream` | GET | SSE 实时流（前端监控面板数据源） |

## 面试要点索引

详见 [ARCHITECTURE.md](./ARCHITECTURE.md)，覆盖：
- 为什么这个场景（ChatGPT 解决不了）
- 为什么多 Agent（非 Workflow）
- 为什么每个技术选型（pgvector / bge-m3 / 不用 Redis / 不用 LangGraph）
- 记忆系统设计（事实型/推导型/偏好型 + 衰减机制 + prefix cache 友好）
- 混合检索设计（RRF 融合 + LLM 重排 vs cross-encoder）
- 评估体系（MRR/NDCG + Agent eval）
- AI Coding 工作流（CLAUDE.md + Skills）

## 项目结构

```
knowledge-agent/
├── ARCHITECTURE.md          # 完整架构方案
├── IMPLEMENTATION_PLAN.md   # 8步实现计划
├── README.md
├── backend/
│   ├── main.py              # FastAPI + SSE
│   ├── config.py            # 配置中心（模型路由/embedding/检索参数）
│   ├── agents/              # 4 个 Agent（collector/curator/librarian/editor）
│   ├── core/                # LLM wrapper / MessageBus / Orchestrator
│   ├── ingestion/           # 文档处理管线（parser/chunker/embedder/loader）
│   ├── retrieval/           # 混合检索 + RRF 融合 + LLM 重排
│   ├── memory/              # 短期/长期记忆 + 衰减
│   ├── context/             # 上下文装配（prefix cache 优化）
│   └── eval/                # 评估数据集 + 脚本
├── frontend/                # Next.js + TailwindCSS
│   └── src/
│       ├── app/page.tsx          # 主页面：聊天 + 监控
│       ├── components/AgentMonitor.tsx  # Agent 实时通信面板
│       └── lib/api.ts            # 后端 API 封装
├── benchmark/               # pgvector vs ChromaDB 对比
└── docker-compose.yml       # PostgreSQL + pgvector（Docker 方案）
```
