# CLAUDE.md — Knowledge Agent 项目索引

## 项目概述

多 Agent 协同的个人知识管理系统。4 个 Agent（Collector/Curator/Librarian/Editor）通过 MessageBus + Orchestrator 协商通信，支持文档处理、混合检索、记忆建模。

## 技术栈

- 后端：FastAPI + SQLAlchemy async + PostgreSQL/pgvector + bge-m3
- 前端：Next.js 16 + React + TailwindCSS
- LLM：DeepSeek（兼容 OpenAI SDK），可切换 Claude/GPT
- 部署：Vercel（前端）/ Railway 或 Render（后端）

## 关键文件

- `ARCHITECTURE.md` — 完整架构方案，包含所有技术选型的 why
- `backend/config.py` — 全局配置（模型路由、embedding、检索参数、记忆参数）
- `backend/main.py` — FastAPI 入口 + SSE 端点
- `backend/core/orchestrator.py` — 多 Agent 协商引擎（广播→串行动态路由）
- `backend/core/message_bus.py` — Agent 间消息通信总线
- `backend/core/llm.py` — LLM 调用封装（llm_call + llm_chat）
- `backend/agents/base.py` — Agent 基类（think_and_act 循环 + 工具解析）
- `backend/retrieval/retriever.py` — 检索编排入口
- `backend/ingestion/loader.py` — 文档加载器（解析→分块→embedding→入库）
- `backend/eval/eval_retrieval.py` — 检索质量评估

## 数据流

1. 用户消息 → `POST /chat` → `Orchestrator.route_and_execute`
2. 广播给 4 个 Agent → 每个 Agent 判断是否参与
3. Agent 通过 `@agent名` 动态路由 → MessageBus 传递
4. SSE 推送 Agent 消息到前端 `AgentMonitor`

## 常用命令

```bash
# 启动数据库
pg_ctl -D ~/pgdata -l ~/pgdata/logfile start

# 启动后端
cd backend && uvicorn main:app --reload

# 启动前端
cd frontend && npm run dev

# 跑测试
cd backend && python test_pipeline.py

# 跑评估
cd backend && python eval/eval_retrieval.py
```

## 注意

- `backend/.env` 需要 `DEEPSEEK_API_KEY`
- 首次运行会自动从 HuggingFace 下载 bge-m3 模型（~2GB）
- Agent 的 `conversation_history` 每次新请求会清空
- 协商轮数上限 20，连续 5 轮无新消息 + Editor 已回答 → 自动结束
