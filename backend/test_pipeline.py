import asyncio
from ingestion.loader import load_document
from retrieval.retriever import retrieve
from core.llm import llm_call
from db.database import init_db

async def main():
    await init_db()
    print("✅ 数据表已就绪")

    docs = [
    ("混合检索设计", """## RRF 融合算法
Reciprocal Rank Fusion 是混合检索的标准做法。
RRF 不需要归一化向量分数和 BM25 分数，只关心排名。
k=60 是常见选择：k 越大越接近平均排名，k 越小越看重前几名。
"""),
    ("Prompt Cache 入门", """## 为什么需要 Prompt Caching
LLM API 调用中，system prompt 和工具定义几乎每次都不变。
把这些放到 prompt 最前面，API 提供商可以缓存这些前缀，
后续请求只计算变化的尾部。Anthropic 的 cache 写贵读便宜。
"""),
    ("Python 性能优化", """## async/await 最佳实践
异步函数用 asyncio.gather 并行执行独立 IO 操作。
数据库连接使用连接池复用，不要每次查询都建新连接。
uvicorn 配合 FastAPI 支持高并发异步请求处理。
"""),
]
    for title, content in docs:
        await load_document(title=title, content=content)
    
    # 1. 加载一篇测试文档
    print("=" * 50)
    print("1. 加载测试文档...")
    doc_id = await load_document(
        title="Agent Memory 设计指南",
        content="""
## Agent 记忆系统设计

Agent 的记忆系统分为短期记忆和长期记忆两个层次。

### 短期记忆

短期记忆用于跟踪当前会话的上下文。它存储：
- 最近的对话历史（通常保留最近 20 轮）
- 当前会话中检索过的文档
- 临时偏好（如"今天想了解 RAG"）

短期记忆在会话结束后会被清空，重要的信息会被提取并写入长期记忆。

### 长期记忆

长期记忆存储跨会话的用户知识，包括：
- 用户长期关注的领域（如 AI Agent、Prompt Engineering）
- 用户的偏好（喜欢深度长文、不喜欢新闻摘要）
- 用户的基本信息

长期记忆需要设计衰减机制。受艾宾浩斯遗忘曲线启发：
- 超过 30 天未巩固的记忆，权重开始衰减
- 超过 90 天未访问的记忆，进入休眠状态
- 休眠记忆可以被重新唤醒
""",
        source_type="markdown",
    )
    print(f"   ✅ 文档已入库，ID: {doc_id}")

    # 2. 检索测试
    print("\n2. 测试检索...")
    results = await retrieve(
        query="长期记忆怎么设计衰减机制",
        llm_call=llm_call,
    )

    print(f"   找到 {len(results)} 条结果：")
    for i, r in enumerate(results):
        print(f"   [{i+1}] 相关度: {r.get('rerank_score', r.get('rrf_score', 'N/A'))}")
        print(f"       内容: {r['content'][:150]}...")
        if 'rerank_reason' in r:
            print(f"       理由: {r['rerank_reason']}")
        print()


if __name__ == "__main__":
    
    asyncio.run(main())
