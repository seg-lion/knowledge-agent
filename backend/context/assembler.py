'''
把 short_term + long_term + 检索结果 + 配置信息
系统提示 + 长期记忆+ 短期 + 检索文档 + 工具 + 当前问题
'''

from memory.long_term import get_active_interests
from memory.short_term import ShortTermMemory
from config import get_settings

settings = get_settings()

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

    # 用户兴趣层：变化频率低，放前面
    interests = await get_active_interests()
    qualified = [i for i in interests if i['confidence'] > 0.3] # 选出大于0.3的

    if qualified:
        interest_text = "## 用户长期兴趣\n"
        for i in qualified[:5]:
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

    # 工具层（变化少，放在 system message之后） 这是干嘛用的，一般工具不是agent收到query之后，Thought之后按照Action再来看工具的吗
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

