'''
负责综合回答和生成简报
'''

from .base import BaseAgent
from memory.short_term import ShortTermMemory
from context.assembler import assemble_context

class EditorAgent(BaseAgent):
    '''编辑：综合回答、生成简报'''

    def __init__(self, session: ShortTermMemory | None = None, llm_call_func = None):

        self.session = session
        self._llm_call = llm_call_func
        self._answer_func = self._build_answer_func()
        
        super().__init__(
            name = "editor",
            tools={
                "answer_with_search":{
                    "description": "在知识库中搜索并综合回答用户问题",
                    "params": {"question": "用户的问题"},
                    "function": self._answer_func,
                },
            }
        )
    
    def _build_answer_func(self):
        import core.llm as llm_mod

        async def answer_with_search(question: str) -> str:
            # 先用 Librarian 的方式检索
            from retrieval.retriever import retrieve

            llm_call_func = llm_mod.llm_call
            results = await retrieve(question, llm_call_func, top_k=3)

            if not results:
                return "抱歉，知识库中没有找到相关信息"
            
            # 拼接检索结果，生成综合回答
            # 拼接检索结果，生成综合回答
            docs_text = "\n\n".join(
                f"[来源{i+1}] {r['content'][:400]}" for i, r in enumerate(results)
            )
            answer_prompt = f"""基于以下检索结果回答用户问题。标注信息来源。如果信息之间有矛盾，明确指出。

检索结果：
{docs_text}

用户问题：{question}

请回答："""

            response = await llm_call_func(
                system_prompt="你是一个知识助手，基于给定的检索结果回答用户问题。必须标注信息来源编号。",
                user_message=answer_prompt,
                provider=self.provider,
                model=self.model,
            )
            return response

        return answer_with_search

    @property
    def system_prompt(self) -> str:
        return """你是知识编辑。你的职责是基于知识库的内容回答用户问题。

核心要求：
1. 检索相关文档后，综合多个来源给出完整回答
2. 每个观点都要标注来源（[来源1]、[来源2]）
3. 如果不同来源的信息有矛盾，明确指出冲突

你是用户直接对话的对象。保持回答友好、准确。"""

