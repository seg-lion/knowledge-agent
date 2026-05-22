'''
所有 Agent 的父类---定义了Agent 的通用行为：怎么调LLM，怎么执行工具、怎么收消息
'''
import json
import asyncio
from core.llm import llm_chat
from config import get_settings

settings = get_settings()


class BaseAgent:
    """
    Agent 基类。
    每个 Agent 有独立的 system_prompt、工具集、模型路由、对话历史。
    """

    def __init__(self, name: str, tools: dict | None = None):
        self.name = name
        self.tools = tools or {}
        model_cfg = settings.model_routing.get(name, {"provider": "deepseek", "model": "deepseek-chat"})
        self.provider = model_cfg["provider"]
        self.model = model_cfg["model"]
        self.conversation_history: list[dict] = []

    @property
    def system_prompt(self) -> str:
        raise NotImplementedError

    def tools_description(self) -> str:
        if not self.tools:
            return ""
        lines = []
        for tool_name, tool_info in self.tools.items():
            params = tool_info.get("params", {})
            lines.append(f"- {tool_name}: {tool_info['description']}")
            if params:
                lines.append(f"  参数: {json.dumps(params, ensure_ascii=False)}")
        return "\n".join(lines)

    def _build_full_system_prompt(self) -> str:
        parts = [self.system_prompt]
        if self.tools:
            parts.append(f"\n\n## 可用工具\n{self.tools_description()}")
            parts.append('\n调用工具时，回复一个 JSON：\n{"tool": "工具名", "params": {"参数": "值"}}')
            parts.append("不需要调工具时，直接回复用户。")
        return "\n".join(parts)

    async def think_and_act(self, user_message: str) -> dict:
        """核心循环：多轮对话 + 工具调用，完整保留对话历史"""

        # 首次调用时设置 system prompt
        if not self.conversation_history:
            self.conversation_history.append(
                {"role": "system", "content": self._build_full_system_prompt()}
            )

        # 新消息追加到历史
        self.conversation_history.append({"role": "user", "content": user_message})

        tool_calls_made = []
        max_turns = 3

        for _ in range(max_turns):
            response = await llm_chat(
                messages=self.conversation_history,
                provider=self.provider,
                model=self.model,
            )

            tool_call = self._parse_tool_call(response)
            if tool_call and tool_call["name"] in self.tools:
                tool_result = await self._execute_tool(tool_call["name"], tool_call["params"])
                tool_calls_made.append({
                    "tool": tool_call["name"],
                    "params": tool_call["params"],
                    "result": tool_result,
                })
                self.conversation_history.append({"role": "assistant", "content": response})
                self.conversation_history.append({
                    "role": "user",
                    "content": f"工具 {tool_call['name']} 返回:\n{tool_result}",
                })
            else:
                self.conversation_history.append({"role": "assistant", "content": response})
                return {"response": response, "tool_calls": tool_calls_made}

        return {"response": response, "tool_calls": tool_calls_made}

    def _parse_tool_call(self, response: str) -> dict | None:
        text = response.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        try:
            parsed = json.loads(text)
            if "tool" in parsed and "params" in parsed:
                return {"name": parsed["tool"], "params": parsed["params"]}
        except json.JSONDecodeError:
            pass
        return None

    async def _execute_tool(self, tool_name: str, params: dict) -> str:
        func = self.tools[tool_name]["function"]
        try:
            result = await func(**params) if asyncio.iscoroutinefunction(func) else func(**params)
            return str(result)[:2000]
        except Exception as e:
            return f"工具执行错误: {e}"
