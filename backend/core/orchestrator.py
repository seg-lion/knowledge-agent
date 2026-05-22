'''
Agent的指挥中心----创建、注册到消息总线，协调协商回合
'''

import asyncio
from core.message_bus import MessageBus
from agents.collector import CollectorAgent
from agents.curator import CuratorAgent
from agents.librarian import LibrarianAgent
from agents.editor import EditorAgent
from memory.short_term import ShortTermMemory

class Orchestrator:
    '''多 Agent 协商协调器'''

    def __init__(self):
        self.bus = MessageBus()
        self.collector = CollectorAgent()
        self.curator = CuratorAgent(message_bus= self.bus)
        self.librarian = LibrarianAgent()
        self.editor = EditorAgent()
        self.session: ShortTermMemory | None = None

        # 四个 Agent 全部注册到消息总线
        for name in ['collector', 'curator', 'librarian', 'editor']:
            self.bus.register(name)

        
    def new_session(self, session_id: str) -> None:
        '''创建一个新的会话'''
        self.session = ShortTermMemory(session_id)
        self.editor.session = self.session

    async def route_and_execute(self, user_message: str) -> dict:
        '''
        用户消息入口，根据意图路由到合适的Agent
        这是一个简化版--真正的多Agent 协商在后面扩展
        '''

        if self.session is None:
            self.new_session('default')
        
        # 记录用户消息
        self.session.add_message("user", user_message)

        # 简单意图判断：包含”http“ -> Collector
        if "http://" in user_message or "https://" in user_message:
            result = await self.collector.think_and_act(user_message)
            agent_used = "collector"
        elif any(kw in user_message for kw in ["搜", "找", "查", "什么是", "怎么", "为什么", "?"]):
            result = await self.editor.think_and_act(user_message)
            agent_used = "editor"
        else:
            result = await self.editor.think_and_act(user_message)
            agent_used = "editor"
        
        response_text = result.get("response", str(result))
        self.session.add_message(agent_used, response_text)

        # 记录主题
        from memory.long_term import record_access, check_auto_capture
        for topic in self.session.get_top_topics(3):
            await record_access(topic)
            await check_auto_capture(topic)
        

        return {
            "agent": agent_used,
            "response": response_text,
            "tool_calls": result.get("tool_calls", []),
            "session_id": self.session.session_id
        }
    
    async def negotiate(self, task: str, max_rounds: int = 5) -> dict:
        """
        真正的多 Agent 协商——每个 Agent 自主决定何时发言、对谁发言。
        不是固定的 pipeline，是 Agent 通过 MessageBus 自由通信。
        """
        # 注册所有 Agent
        for name in ["collector", "curator", "librarian", "editor"]:
            self.bus.register(name)

        # 广播任务
        await self.bus.broadcast(
            from_agent="orchestrator",
            msg_type="proposal",
            content=task,
            round_num=0,
        )

        # 每个 Agent 的处理逻辑
        agent_instances = {
            "collector": self.collector,
            "curator": self.curator,
            "librarian": self.librarian,
            "editor": self.editor,
        }

        # 每个 Agent 独立运行：收消息 → 思考 → 发消息
        async def agent_loop(name: str, agent):
            for _ in range(max_rounds):
                try:
                    msg = await self.bus.receive(name, timeout=10)
                except asyncio.TimeoutError:
                    continue

                # 收到消息 → 让 Agent 思考并决定下一步
                prompt = self._build_negotiation_prompt(name, msg)
                result = await agent.think_and_act(prompt)

                response_text = result.get("response", "")

                # Agent 自主决定给谁发消息
                targets = self._parse_targets(response_text)
                for target in targets:
                    await self.bus.send(
                        from_agent=name,
                        to_agent=target,
                        msg_type="response",
                        content=response_text,
                        round_num=msg.get("round_num", 0) + 1,
                    )

        # 四个 Agent 并发运行
        await asyncio.gather(
            agent_loop("curator", self.curator),
            agent_loop("librarian", self.librarian),
            agent_loop("editor", self.editor),
            agent_loop("collector", self.collector),
        )

        return {
            "task": task,
            "message_history": self.bus.get_history(),
            "rounds": max_rounds,
        }

    def _parse_targets(self, response_text: str) -> list[str]:
        """从 Agent 回复中提取目标 Agent 名（@agent名 格式）"""
        import re
        targets = re.findall(r'@(\w+)', response_text)
        valid = {"collector", "curator", "librarian", "editor", "all"}
        return [t for t in targets if t in valid]

    def _build_negotiation_prompt(self, agent_name: str, msg: dict) -> str:
        """构造协商时的 system prompt 补充，让 Agent 知道怎么参与协商"""
        return f"""[协商消息]
发送者: {msg['from_agent']}
消息类型: {msg['msg_type']}
内容: {msg['content']}

你是 {agent_name}。收到上述消息后：
1. 如果你是相关方，给出你的专业判断
2. 如果你需要其他 Agent 的信息，明确指出你要问谁、问什么。格式：@agent名 你的问题
3. 如果消息与你无关，回复 "PASS"
4. 如果你认为当前方案有问题，直接指出并给出修改建议"""



