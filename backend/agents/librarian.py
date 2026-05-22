'''
负责检索
'''

from .base import BaseAgent
from retrieval.retriever import retrieve


class LibrarianAgent(BaseAgent):
    '''馆员：管理知识库，执行检索'''

    def __init__(self, llm_call_func = None):
        self._llm_call = llm_call_func

        super().__init__(
            name = "librarian",
            tools = None,
        )

        self._search_func = self._build_search_func()

        self.tools = {
            "search": {
                "description": "在知识库中检索相关文档。query应该是一个完整的自然语言问题",
                "params": {"query": "自然语言查询"},
                "function": self._search_func,
            },
        }

    def _build_search_func(self):
        agent = self

        async def search(query:  str) -> str:
            if agent._llm_call is None:
                from core.llm import llm_call
                agent._llm_call = llm_call
            results = await retrieve(query, agent._llm_call, top_k=3)
            if not results:
                return "未找到相关文档"
            return "\n\n---\n".join(
                f"[{i+1}] 相关度={r.get('rerank_score', r.get('rrf_score', 0)):.1f}\n{r['content'][:400]}"
                for i, r in enumerate(results)
            )
        return search

    @property
    def system_prompt(self) -> str:
        return """你是知识库管理员。你负责从知识库中检索信息。

当收到搜索请求时：
1. 理解用户的真实信息需求
2. 用 search 工具检索相关文档
3. 返回最相关的内容片段

当知识库存储压力大时（频繁写入、内容增长快），主动建议提高收录门槛。"""
