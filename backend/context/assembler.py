'''
把 short_term + long_term + 检索结果 + 配置信息
系统提示 + 长期记忆+ 短期 + 检索文档 + 工具 + 当前问题
'''

from memory.long_term import get_active_interests
from memory.short_term import ShortTermMemory
from ingestion.embedder import embed_text
from config import get_settings
import numpy as np

settings = get_settings()


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """两个向量的余弦相似度（0~1）"""
    a_arr, b_arr = np.array(a), np.array(b)
    return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr) + 1e-8))


async def get_relevant_interests(query: str, top_k: int = 5) -> list[dict]:
    """
    选出跟当前 query 最相关的活跃兴趣。
    综合得分 = confidence × 0.6 + query 相关度 × 0.4
    """
    all_interests = await get_active_interests()
    qualified = [i for i in all_interests if i["confidence"] > 0.3]

    if not qualified or not query.strip():
        return qualified[:top_k]

    query_emb = embed_text(query)
    scored = []
    for i in qualified:
        topic_emb = embed_text(i["topic"])
        relevance = _cosine_similarity(query_emb, topic_emb)
        combined = i["confidence"] * 0.6 + relevance * 0.4
        scored.append((combined, i))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:top_k]]


async def assemble_context(
        agent_system_prompt: str,
        session: ShortTermMemory,
        tools_description: str = "",
        user_query: str = "",
        retrieved_docs: list[dict] | None = None,
) -> list[dict]:
    '''
    分层装配上下文，顺序至关重要--变化少的在前，变化多的在后，
    保证 prefix cache 命中率最大
    '''

    # 用户兴趣层：按 query 相关度 + 置信度综合排序
    interests = await get_relevant_interests(user_query)

    if interests:
        interest_text = "## 用户长期兴趣\n"
        for i in interests:
            interest_text += f"-{i["topic"]} (置信度： {i['confidence']:.2f})\n"
    else:
        interest_text = "## 用户长期兴趣\n暂无记录\n"

    # 会话摘要层：每N轮可能变
    session_text = f"## 当前会话上下文\n{session.get_recent_context()}"

    # 完整 system prompt
    full_system = (
        f"{agent_system_prompt}\n\n"
        f"{interest_text}\n"
        f"{session_text}"
    )

    messages = [{"role": "system", "content": full_system}]

    # 工具层（变化少，放在 system message之后）
    if tools_description:
        messages.append(
            {
                "role": "system",
                "content": f"## 可用工具\n {tools_description}",
            }
        )

    # 检索结果层：每次query不同
    if retrieved_docs:
        docs_text = "## 检索结果\n"
        for i, doc in enumerate(retrieved_docs):
            docs_text += f"[{i}] {doc['content'][:300]}\n"
        messages.append(
            {
                "role": "system",
                "content": docs_text,
            }
        )

    # 当前 query 层： 每次都变
    messages.append(
        {
            "role": "user",
            "content": user_query,
        }
    )

    return messages
