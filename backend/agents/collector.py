'''
负责抓取外部内容，走 ingestion pipeline ， 它的工具已经在ingestion/loader.py写好了

'''
import httpx
from bs4 import BeautifulSoup
from .base import BaseAgent
from ingestion.loader import load_document
from ingestion.parser import parse_document


class CollectorAgent(BaseAgent):
    """收集员：自动抓取文章、解析入库"""

    def __init__(self):
        super().__init__(
            name="collector",
            tools={
                "fetch_url": {
                    "description": "抓取一个 URL 的内容并存入知识库",
                    "params": {"url": "网页URL"},
                    "function": self._fetch_url,
                },
                "load_document": {
                    "description": "把一篇文档直接存入知识库",
                    "params": {"title": "标题", "content": "正文", "source_type": "markdown"},
                    "function": self._load_doc_wrapper,
                },
            },
        )

    async def _fetch_url(self, url: str) -> str:
        """抓取网页 → 解析 → 入库"""
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        content = resp.text
        source_type = "html"

        # 从 <title> 提取标题
        soup = BeautifulSoup(content, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else url

        doc_id = await load_document(
            title=title,
            content=content,
            source_type=source_type,
            source_url=url,
        )
        return f"已抓取并入库：{title}，ID: {doc_id}"

    async def _load_doc_wrapper(self, title: str, content: str, source_type: str = "markdown") -> str:
        doc_id = await load_document(
            title=title,
            content=content,
            source_type=source_type,
        )
        return f"已入库：{title}，ID: {doc_id}"

    @property
    def system_prompt(self) -> str:
        return """你是知识收集员。你的职责是从各种来源收集和管理文档。

当用户提供一篇文章或一个 URL 时：
- 用 fetch_url 抓取网页内容并自动入库
- 用 load_document 直接保存文档

不要自己编造内容。只处理用户实际给你的内容。"""
