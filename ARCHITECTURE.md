# 个人知识管理与深度研究助手 — 多 Agent 协同系统

## 场景定位

一个**真正需要文档处理 + RAG + 混合检索 + 记忆 + 多 Agent 协同**的个人知识管理系统。

**日常使用流程**：
1. 你收藏了一篇博客、一篇论文、几条推文 → 系统自动解析、分块、embedding、入库
2. 你想回顾"之前看过关于 agent memory 的内容" → 混合检索（向量语义召回 + 关键词精确匹配 + 重排）返回最相关的
3. 你问一个问题 → Agent 从你的知识库中检索相关文档，综合回答，标注来源
4. 每天早上 → 系统根据你的兴趣模型生成个性化简报
5. 你的兴趣从 RAG 转向 Agent 了 → 长期记忆自动衰减旧兴趣，提升新兴趣权重

**为什么 ChatGPT 对话解决不了**：需要一个持续增长的个人知识库、自动化定时收集、兴趣模型随时间演化、跨文档关联发现——这些都不是单次对话能做的。

---

## 四个 Agent 定义

| Agent | 职责 | 工具 | 关键行为 |
|-------|------|------|---------|
| **Collector** 收集员 | 从 RSS/Twitter/GitHub 等源抓取内容，走 ingestion pipeline | fetch_rss, fetch_bookmarks, parse_document, chunk_and_embed | 定时抓取，质量下降时自动降频 |
| **Curator** 分析员 | 筛选、分类、去重、判断内容价值 | classify_content, check_duplicate, score_relevance | 跟 Librarian 来回确认"这篇是不是看过了"，质量太低就建议 Collector 降频 |
| **Librarian** 馆员 | 管理知识库：存储、索引、检索、去重合并、衰减 | hybrid_search, rerank, merge_documents, evict_low_value | 接收 Curator 的查重请求，响应 Editor 的检索请求，在存储压力大时主动要求 Curator 提高收录门槛 |
| **Editor** 编辑 | 回答用户问题、生成日报/周报、综合多个检索结果 | query_librarian, generate_briefing, synthesize_answer | 检索不到满意结果时要求 Librarian 换策略重搜，发现信息矛盾时标注置信度 |

### 真正的多 Agent 通信（非 Workflow）

```
Curator: "新抓到一篇《Building Effective Agents》的解读文章，Librarian 帮我查下有没有类似内容？"
Librarian: [hybrid_search] "72% 相似度，你 5 月 10 号存过 Anthropic 的原文。这篇是中文解读，建议作为'衍生阅读'关联到原文，不单独建索引。"
Curator: "同意，关联到原文。另外这篇文章质量一般，我建议给个低权重。"

Editor: "用户问'2026年Agent架构有什么新趋势'，Librarian 检索。"
Librarian: [hybrid_search + rerank] "找到 5 篇高相关，3 篇中相关。但其中有 2 篇观点互相矛盾——一篇说多Agent是未来，一篇说单Agent+好工具更优。"
Editor: "这个矛盾本身很有价值。回答时把两篇都引用，标注出观点冲突。"

Librarian: "警告：本月新增了 3000 个 chunk，存储压力大。Curator 你提高收录门槛？"
Curator: "好，relevance threshold 从 0.5 提到 0.7。低相关性内容只存摘要不存全文。"

Collector: "RSS源 'AI Weekly' 最近 3 天只返回了 2 篇文章，而且都是营销软文。"
Curator: "建议将其降级为每周抓取一次，我在下次 briefing 中告诉用户是否需要取消订阅。"
```

**关键设计**：Agent 之间不是固定管道，而是有查重、否决、策略调整、矛盾标注、资源协商。这才是真正的多 Agent。

---

## 技术选型（每一个都有 why）

| 技术 | 为什么用它 | 为什么不用别的 |
|------|----------|-------------|
| **FastAPI** | Python 原生、async、SSE 流式 | Django 太重 |
| **Next.js + React + TailwindCSS** | 部署 Vercel 一条命令，面试官能体验 | - |
| **PostgreSQL + pgvector** | **一个数据库解决所有**：文档存储、chunk 存储、向量检索、全文检索、用户数据、Agent 状态 | 不用 Milvus/ChromaDB/Pinecone：此项目数据量（个人知识库）不需要分布式向量库。pgvector 的 HNSW 索引完全够用。不用 MySQL：PG 是 2026 新项目默认。不用 Neo4j：文档间关系用关系表存，不需要图库。不用 Elasticsearch：PG 的 tsvector 做关键词检索够用 |
| **多模型分级** | 按 Agent 职责分配不同模型：成本、延迟、能力三者匹配 | 博客明确指出"所有 Agent 都用同一个模型"是减分项。模型不分级就体现不出多 Agent 的真正价值 |
| **自建 Agent 编排** | 可以解释每一行代码 | **不用 LangGraph**：4 Agent 的通信模式（查重协商、资源协商、矛盾标注）是自定义的，自建编排才能展示对这些模式的理解。LangGraph 会遮住核心逻辑 |
| **SSE** | 实时推送 Agent 讨论到前端 | WebSocket 也可以但更重，此场景不需要双向流 |
| **不用 Redis** | 无分布式锁/跨节点同步需求。Agent 状态在编排层内存管理，用户数据在 PostgreSQL | Redis 的合理用途在此项目中不成立。博客明确指出：不要把用户数据当缓存来对待 |
| **不用独立向量库** | pgvector 的 HNSW 索引在百万级 chunk 以下表现足够，个人知识库远达不到这个量 | 详见 PG 选型理由 |
| **不用图库** | 文档间关系（衍生、矛盾、更新）用关系表 + 外键表达 | Neo4j 增加运维复杂度，此场景的图关系简单 |
| **不用微调** | System prompt + 工具定义 + 检索增强 已经足够 | 微调需要持续维护训练数据，ROI 不高。面试时讨论"如果要微调，哪些场景值得"是加分项 |

---

## 模型选型详解

### 模型分级策略

**一个 Agent ≠ 一个模型**。博客明确指出"所有 Agent 都用同一个模型"是减分项。按职责分配：

| Agent | 核心任务 | 推荐模型 | 备选模型 | 选型理由 |
|-------|---------|---------|---------|---------|
| **Collector** 收集员 | 抓取网页、解析文档、调用 ingestion pipeline | **GPT-4o-mini** | Qwen3-8B (百炼) | 任务简单重复，不需要强推理。GPT-4o-mini 便宜($0.15/1M input)且支持 function calling |
| **Curator** 分析员 | 内容分类、质量打分、去重判断 | **Claude Haiku 4.5** | Qwen3-32B (百炼) | 需要判断力（这篇文章值不值得存？），但不需要深度推理。Haiku 快且便宜，足够胜任 |
| **Librarian** 馆员 | 检索策略决策、相似度判断、存储管理 | **Claude Sonnet 4.6** | Qwen3-235B (百炼) | 需要理解复杂检索意图、判断文档间关系。检索质量直接影响下游 Editor，值得用强模型 |
| **Editor** 编辑 | 综合写作、问答、简报生成 | **Claude Sonnet 4.6** | GPT-4o | 用户直接看到输出，质量要求最高。需要强写作能力 + 多源信息综合 |

**成本视角**（面试加分）：
- Collector 和 Curator 占了 80% 的调用量但用便宜模型
- Librarian 和 Editor 是核心体验链路但调用频率低
- 整体成本可控，且模型选择有明确的工程理由

### Embedding 模型选型

| 候选 | 维度 | 最大Token | 中文效果 | 部署 | 混合检索适配 |
|------|------|----------|---------|------|------------|
| **bge-m3** (BAAI) | 1024 | 8192 | ⭐⭐⭐⭐⭐ | 自托管/需要GPU | **原生输出 dense + sparse 双向量，完美契合混合检索** |
| text-embedding-3-small (OpenAI) | 512/1536 | 8191 | ⭐⭐⭐ | API | 只输出 dense，sparse 需要单独维护 BM25 |
| voyage-multilingual-2 | 1024 | 32000 | ⭐⭐⭐⭐ | API | 长文档好，但中文不如 bge-m3 |

**推荐 bge-m3，理由**：

1. **一个模型产出两种向量**：dense vector（语义相似度）+ sparse vector（关键词匹配），不需要另外维护 BM25 索引。这意味着混合检索的两路召回来自**同一个模型的两种表示**，设计上更简洁
2. **中英混合场景最佳选择**：BAAI 专门针对中英双语训练，中文检索质量显著优于 OpenAI embedding
3. **免费自托管**：基于 HuggingFace sentence-transformers 部署，无 API 费用
4. **面试时这是大加分项**："我选 bge-m3 不仅因为它中文效果好，更因为它原生支持 dense+sparse dual-vector 输出——我的混合检索的 sparse 通路不是另外搭的 BM25，而是同一个 embedding 模型的 lexical representation，这让两路召回在语义空间上更一致"

**降级方案（如果 GPU 不可用）**：
- 用 text-embedding-3-small（OpenAI API）+ PostgreSQL tsvector 做 sparse 通路
- 在 README 中注明"如果有 GPU 资源，切换到 bge-m3 可以获得...好处"

### 数据库对比方案

**主线**：PostgreSQL + pgvector（理由见技术选型表）

**对比实验**（写到项目 README / 面试用）：

写一个 `benchmark/compare.py` 脚本，相同条件下对比 pgvector vs ChromaDB：

| 维度 | pgvector | ChromaDB | 结论 |
|------|---------|----------|------|
| 部署复杂度 | Docker 一个容器 | pip install 即可，嵌入式运行 | ChromaDB 更轻 |
| 1000条 chunk 检索延迟 | ~5ms | ~3ms | 基本持平 |
| 10000条 chunk 检索延迟 | ~8ms | ~5ms | 基本持平 |
| 结构化数据支持 | ✅ 原生 SQL | ❌ 需要另外的 DB | **pgvector 胜** |
| 全文检索 | ✅ tsvector 原生 | ❌ 需要另外的方案 | **pgvector 胜** |
| 元数据过滤 | ✅ SQL WHERE | ✅ ChromaDB metadata filter | 平手 |
| 生态/运维 | ✅ PG 生态 20 年 | ⚠️ 相对年轻 | pgvector 更稳 |

**结论**：此项目选择 pgvector 是因为需要频繁的结构化查询（文档元数据、用户数据、Agent 状态）和全文检索——这些 ChromaDB 做不了，需要额外接 PostgreSQL。与其维护两套存储，不如 PostgreSQL 一个搞定。

**Milvus 何时才值得上**：当数据量达到千万级 chunk，需要分布式索引、多副本、GPU 加速检索时。个人知识管理项目远达不到。

---

## 项目结构

```
knowledge-agent/
├── backend/
│   ├── main.py                    # FastAPI app, SSE endpoint
│   ├── requirements.txt
│   ├── agents/
│   │   ├── base.py                # BaseAgent: system prompt, tools,消息收发
│   │   ├── collector.py           # Collector Agent
│   │   ├── curator.py             # Curator Agent
│   │   ├── librarian.py           # Librarian Agent (检索核心)
│   │   └── editor.py              # Editor Agent (问答+简报)
│   ├── core/
│   │   ├── orchestrator.py        # 多 Agent 协商协调器
│   │   ├── message_bus.py         # Agent 间结构化消息通信
│   │   └── llm.py                 # Claude API wrapper
│   ├── ingestion/
│   │   ├── parser.py              # 文档解析 (HTML, MD, PDF, text)
│   │   ├── chunker.py             # 语义分块 (段落/标题感知)
│   │   └── embedder.py            # Embedding 生成 + 存储
│   ├── retrieval/
│   │   ├── hybrid_search.py       # 向量 + 关键词 混合检索 (RRF融合)
│   │   ├── reranker.py            # LLM-based 重排序
│   │   └── retriever.py           # 检索编排: 召回→融合→重排
│   ├── memory/
│   │   ├── short_term.py          # 会话级短期记忆
│   │   ├── long_term.py           # 用户兴趣模型 + 长期记忆
│   │   └── decay.py               # 艾宾浩斯遗忘曲线 + 兴趣衰减
│   ├── context/
│   │   └── assembler.py           # 上下文装配 (prefix caching优化)
│   ├── sources/
│   │   ├── rss.py                 # RSS 抓取
│   │   └── web.py                 # 网页抓取
│   ├── db/
│   │   ├── models.py              # SQLAlchemy 模型
│   │   └── database.py            # PostgreSQL + pgvector 初始化
│   └── config.py
├── benchmark/
│   └── compare.py                 # pgvector vs ChromaDB 对比实验脚本
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx           # 主页面
│   │   │   └── layout.tsx
│   │   ├── components/
│   │   │   ├── SourceManager.tsx   # 信息源管理
│   │   │   ├── DocumentUpload.tsx  # 文档上传
│   │   │   ├── KnowledgeSearch.tsx # 知识搜索 + 问答
│   │   │   ├── AgentMonitor.tsx    # Agent 实时活动面板 (SSE)
│   │   │   ├── DailyBriefing.tsx   # 每日简报
│   │   │   ├── InterestProfile.tsx # 用户兴趣可视化
│   │   │   └── MemoryViewer.tsx    # 系统记忆查看
│   │   └── lib/
│   │       └── api.ts
│   ├── package.json
│   └── tailwind.config.ts
├── CLAUDE.md
└── README.md
```

---

## 核心模块设计

### 1. 文档处理管线 (Ingestion Pipeline)

```
Raw Content (HTML/MD/PDF/text)
  → Parser: 提取纯文本 + 保留结构元数据
  → Cleaner: 去噪、标准化空白字符
  → Chunker: 语义边界检测 (按段落/标题切分，而非固定 token 数)
  → Embedder: 批量生成 embedding
  → Storage: chunks + embeddings + metadata → PostgreSQL/pgvector
```

**分块策略**（面试可讲）：
- 优先在段落边界、Markdown 标题处分块
- 最小 chunk 200 tokens，最大 1500 tokens
- 相邻 chunk 保留 10% overlap 防止语义断裂
- 每个 chunk 保留父文档元数据（来源、位置、标题层级）

### 2. 混合检索 (Hybrid Search)

```
Query
  ├── Dense 通路: pgvector cosine similarity (top_k=20)
  ├── Sparse 通路: PostgreSQL tsvector @@ tsquery (top_k=20)
  └── Fusion: Reciprocal Rank Fusion (RRF, k=60)
       ↓
  Reranker: LLM 对每个候选打分 (1-5) + 一句话理由
       ↓
  Return: top_k=5, 每篇带分数、来源、相关性理由
```

**为什么用 RRF 而不是简单的分数加权？**
- 向量相似度和 BM25 分数的取值范围差异巨大，直接加权需要归一化
- RRF 只关心排名不关心绝对值，天然适合异构检索结果融合
- 这是学术界和工业界验证过的标准做法

**为什么用 LLM 重排而不是 cross-encoder 模型？**
- MVP 阶段不想增加模型依赖（减少运维复杂度）
- LLM 重排可以同时给理由（可解释性）
- 面试时可讨论"什么场景下应该换 cross-encoder"（延迟敏感场景、大批量场景）

### 3. 记忆系统

#### 短期记忆 (Short-Term)
- 当前会话的对话历史（最近 N 轮）
- 当前会话中检索过的文档列表
- 存储位置：编排层内存 + DB 持久化（用于会话恢复）
- 会话结束后 → 触发异步摘要 → 写入长期记忆

#### 长期记忆 (Long-Term)

**记忆分类**（博客框架）：

| 类型 | 例子 | 写入策略 | 置信度 |
|------|------|---------|--------|
| 事实型 | "用户关注 AI Agent 领域" | 检测到 N 篇同主题阅读后自动写入 | 高 |
| 推导型 | "用户最近在准备面试" | 不显式存储，从阅读模式推导 | - |
| 偏好型 | "用户喜欢深度技术文章，不喜欢新闻摘要" | 写入但标注置信度 + 时效性 | 中，需持续验证 |

**记忆写入触发机制**：
- 显式触发：用户说/点"记住这个"
- 会话结束：异步用便宜模型对会话做摘要提取
- 阈值触发：同一主题阅读超过 N 篇 → 自动捕获为兴趣
- 矛盾检测：新事实 vs 旧事实冲突 → 基于时间戳判断，旧的降权

**记忆衰减**（艾宾浩斯曲线启发）：
- 每个兴趣/记忆带时间戳 + 最近访问时间
- 超过 30 天未被巩固（未再阅读相关主题）→ 权重衰减
- 超过 90 天 → 标记为"休眠"，检索时不主动注入，但可被显式唤醒

**记忆注入位置**（面试重点）：
```
System Prompt (几乎不变)
  → 工具定义 (几乎不变)
    → 长期记忆：用户兴趣摘要 (低频更新)
      → 短期上下文：当前会话摘要 (高频更新，但前缀不变)
        → 当前 Query (每次都变)
          → 检索结果 (每次都变)
```

排序原则：**变化越少越靠前，让 prefix cache 命中率最大化**。

#### 面试时能深入讨论的记忆问题

- "用户说'我对多Agent感兴趣'，这是该记还是不该记？" → 分析了短期偏好 vs 长期兴趣的区分
- "如果用户兴趣变了很多，旧记忆怎么办？" → 衰减而非删除，可被唤醒
- "记忆写入太频繁怎么办？" → 破坏 prefix cache，需要平衡。写入频率 = min(用户行为触发, cache 友好窗口)
- "你怎么处理矛盾记忆？" → 基于时间戳 + 上下文判断当前事实

### 4. 上下文装配 (Context Assembly)

**设计目标**：在有限上下文窗口中，装下最有价值的信息。

**分层设计**：

| 层 | 内容 | 更新频率 | Cache 友好 |
|----|------|---------|-----------|
| 系统层 | Agent 角色定义、行为规范 | 几乎不变 | ✅ 总是命中 |
| 工具层 | 可用工具列表 + 简要描述 | 几乎不变 | ✅ 总是命中 |
| 记忆层 | 用户兴趣摘要 | 每周更新 | ⚠️ 更新时失效 |
| 会话层 | 当前会话摘要 | 每 N 轮更新 | ⚠️ 更新时失效 |
| 检索层 | 当前 query 的检索结果 | 每次 query 不同 | ❌ 不缓存 |
| 对话层 | 最近消息历史 | 每轮变化 | ❌ 不缓存 |

**上下文剪枝策略**：
- 旧的工具调用结果保留摘要，删除原始返回（大段 JSON/文本）
- 检索结果只保留 top_k 的摘要 + 来源链接，不塞全文
- 对话历史超过 N 轮 → 滑动窗口截断，旧轮次转化为一句话摘要

### 5. 评估体系 (Evaluation)

**为什么需要 eval**（博客核心观点）：简历上所有"准确率 90%+"都会被追问。

**检索质量评估**：
- 构造测试集：50 个查询，覆盖 5 类意图（精确查找、语义查找、跨文档关联、时间范围查询、否定查询）
- 指标：MRR (Mean Reciprocal Rank)、Hit Rate@5、NDCG@5
- 自动化：每次改 retrieval pipeline 后跑一遍 eval

**Agent 质量评估**：
- 最终回答是否标注了来源？
- 多源信息存在矛盾时是否标注了？
- 简报是否覆盖了用户真正关注的主题？（用户反馈打分）
- 使用 Promptfoo 做回归测试

---

## 实现步骤（按优先级：RAG > Memory > 多Agent > 评估）

### Step 1: 基础设施 (Day 1-3)
- FastAPI 项目骨架 + Next.js 初始化
- PostgreSQL + pgvector Docker Compose 一键启动
- 建表（documents, chunks, user_interests, agent_messages）
- 多模型 LLM wrapper：统一接口，支持 Claude / GPT / Qwen 按 Agent 切换
- Embedding 服务：部署 bge-m3（sentence-transformers），输出 dense + sparse 双向量
- 环境配置（API keys、模型路由映射）

### Step 2: 文档处理管线 (Day 3-5)
- Parser: HTML, Markdown, plain text 支持
- Chunker: 语义分块 + overlap（段落边界感知）
- Embedder: bge-m3 批量生成 dense + sparse 双向量 → 同时写入 pgvector
- 测试：上传 5 篇不同类型的文档，验证分块质量和 embedding 质量

### Step 3: RAG 核心 — 混合检索 + 重排 (Day 5-8) ⭐重点
- Dense 检索：pgvector HNSW 索引 + cosine distance
- Sparse 检索：利用 bge-m3 的 sparse vector 做关键词匹配（不需要额外搭 BM25）
- RRF 融合：dense top-20 + sparse top-20 → RRF → top-20
- 重排：用 Curator Agent 的模型（Haiku）对候选打分 + 给理由
- **数据库对比实验**：写 benchmark/compare.py，同数据量对比 pgvector vs ChromaDB 的延迟和召回率

### Step 4: 记忆系统 (Day 8-12) ⭐重点
- 短期记忆：会话管理 + 检索上下文追踪 + 会话结束异步摘要
- 长期记忆：用户兴趣建模（事实型/推导型/偏好型分类）、衰减曲线（艾宾浩斯启发）
- 记忆写入触发：显式触发、会话结束、阈值触发、矛盾检测
- 记忆读取：注入到 system prompt 前面（prefix cache 友好）
- 上下文装配器：分层装配（静态在前、动态在后）

### Step 5: 评估体系 (Day 12-14) ⭐重点
- **检索质量评估**：
  - 构造测试集：50 个查询，覆盖 5 类意图（精确查找、语义查找、跨文档关联、时间范围、否定查询）
  - 指标：MRR、Hit Rate@5、NDCG@5
  - 自动化脚本：每次改 retrieval pipeline 跑一遍
- **Agent 质量评估**：
  - 来源标注率、矛盾检测率、回答相关性
  - Promptfoo 配置
- **记忆系统评估**：
  - 兴趣模型 accuracy（用户反馈验证）
  - 记忆衰减合理性

### Step 6: 多 Agent 实现 (Day 14-18)
- BaseAgent 基类（模型路由、工具注册、消息收发）
- Collector + Curator + Librarian + Editor 四个 Agent
- 每个 Agent 独立 system prompt + 独立工具集 + 独立模型
- MessageBus + Orchestrator（协商协议引擎）
- SSE 实时推送 Agent 对话到前端

### Step 7: 前端 (Day 18-22)
- 知识搜索 + 问答界面
- Agent 实时活动监控面板（SSE 流式展示 Agent 间的讨论）
- 每日简报展示
- 兴趣管理 + 记忆查看面板
- 文档上传 + 信息源管理

### Step 8: 部署 + 文档 (Day 22-25)
- 后端 → Railway/Render
- 前端 → Vercel
- bge-m3 → HuggingFace Inference Endpoint 或 GPU 实例
- README 写清楚每一个技术决策的 why（按本文技术选型表来写）
- CLAUDE.md 写清楚项目结构和 AI Coding 最佳实践

---

## 面试 80 分钟能讲什么

| 话题 | 能展开的内容 |
|------|-----------|
| 为什么这个场景 | 个人知识管理天然需要多步检索+持续记忆+跨源整合，ChatGPT 对话解决不了 |
| 为什么多 Agent | Agent 之间有查重协商、资源协商、矛盾标注、策略调整——不是 Workflow |
| 模型分级的依据 | Collector 用 GPT-4o-mini（便宜）、Curator 用 Haiku（快+判断力）、Librarian + Editor 用 Sonnet（强推理+好写作）。按任务复杂度 × 调用频率 × 成本做工程决策 |
| 为什么 bge-m3 做 embedding | 原生 dense+sparse 双向量输出，一个模型同时服务混合检索的两路召回，设计上比单独搭 BM25 更简洁。中英双语效果好 |
| 为什么 pgvector 不单独起向量库 | 个人知识库数据量百万级 chunk 以下，HNSW 索引 + tsvector 全文检索完全够用。ChromaDB 能做的 pgvector 都能做，pgvector 还能做结构化查询——少一套基础设施 |
| pgvector vs ChromaDB vs Milvus | 实际跑过对比脚本，有数据支撑：ChromaDB 更轻但缺全文检索和结构化查询，Milvus 百万级以下大材小用 |
| 为什么不用 Redis | 无分布式场景，用户数据不应被当作可 evict 的缓存 |
| 为什么自建编排不用 LangGraph | 4 Agent 的协商模式是自定义的，自建才能展示对多 Agent 通信的理解 |
| 为什么 LLM 重排不用 cross-encoder | MVP 减依赖，且 LLM 重排可解释。面试时讨论 trade-off |
| prefix caching 怎么设计 | 分层上下文装配，变化少的在前，记忆更新频率的 trade-off |
| 记忆系统怎么设计 | 事实型/推导型/偏好型分类 + 写入触发 + 衰减 + 矛盾处理 + cache 友好 |
| eval 怎么做 | 检索 eval（MRR/NDCG）+ Agent eval（来源标注率/矛盾检测率）+ 记忆 eval（兴趣准确率）+ Promptfoo |
| 怎么用 AI Coding | CLAUDE.md + Skills + 项目 doc tree |

---

## 验证方式

1. 启动 `docker-compose up`（PostgreSQL + pgvector）
2. 启动 `uvicorn main:app --reload`
3. 启动 `npm run dev`
4. 上传 5 篇不同类型的文档（博客、论文摘要、推文、README）
5. 搜索 "agent memory 怎么设计" → 验证混合检索返回相关结果
6. 查看 Agent Monitor → 验证 SSE 实时推送 Agent 活动
7. 查看用户兴趣面板 → 验证长期记忆是否正确建模
8. 生成每日简报 → 验证 Editor 综合能力
9. 运行 eval 脚本 → 验证检索质量指标
