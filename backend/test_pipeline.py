import asyncio
from ingestion.loader import load_document
from retrieval.retriever import retrieve
from core.llm import llm_call
from db.database import init_db

async def main():
    await init_db()
    print("✅ 数据表已就绪")


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
