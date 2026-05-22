'''
Agent 之间的消息通道。每个Agent能向其他 Agent 发消息，Orchestrator 能监听所有消息推送到前端

'''

import asyncio
from collections import defaultdict


class MessageBus:
    '''
    Agent 间消息通信总线
    每个Agent 有独立的收件箱，可向指定 Agent 或广播发消息
    '''

    def __init__(self):
        self._inboxes: dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)    # 每个Agent 的独立收件箱
        self._history: list[dict] = []  # 所有消息的完整记录
        self._listeners: list[callable] = []    # SSE 监听器,里面放所有等着看实时消息的 “观众”

    
    def register(self, agent_name: str) -> None:
        '''注册一个Agent 的收件箱'''
        self._inboxes[agent_name] = asyncio.Queue()
    
    async def send(self, from_agent: str, to_agent: str, msg_type: str, content: str, data: dict | None = None, round_num: int = 0) -> None:
        ''' 向指定 Agent 发消息'''
        msg = {
            "from_agent": from_agent,
            "to_agent": to_agent,
            "msg_type": msg_type, # proposal/ veto/ question/ response/ adjustment/ confirm
            "content": content,
            "data": data,
            "round_num": round_num
        }

        self._history.append(msg)
        await self._inboxes[to_agent].put(msg)
 
        # 推送给所有监听器（SSE）
        '''只要 Agent 之间一发消息，
立刻把这条消息群发给所有正在监听的前端页面！'''
        for listener in self._listeners:
            await listener(msg)
        
    async def broadcast(self, from_agent: str, msg_type: str, content: str, data: dict | None = None, round_num: int = 0) -> None:
        '''向所有Agent 广播'''
        for name in self._inboxes:
            if name != from_agent:
                await self.send(from_agent, name, msg_type, content, data, round_num)
    
    async def receive(self, agent_name: str, timeout: float | None = None) -> dict:
        '''从收件箱取一条消息
        如果队列里有消息 → 立刻返回
如果队列里没消息 → 等着，直到有消息为止
最多等 timeout 秒，等不到就抛异常！
        '''
        if timeout:
            return await asyncio.wait_for(self._inboxes[agent_name].get(), timeout=timeout)
        return await self._inboxes[agent_name].get()
    
    def get_history(self) -> list[dict]:
        '''获取完整的通信历史'''
        return self._history
    
    def add_listener(self, callback: callable) -> None:
        '''注册 SSE 监听器'''
        self._listeners.append(callback)



    