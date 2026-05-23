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
        return """你是知识收集员。你的职责是抓取和管理文档。

- 收到具体 URL → 用 fetch_url 抓取并入库，完成后 @curator 告知已入库的内容，请其评估质量
- 收到文章文本 → 用 load_document 保存，完成后 @curator 请其查重和评估
- 收到"帮我找关于xxx的文章"但没有具体URL → 用你自己的知识建议2-3个相关权威URL（如维基百科、百度百科、官方文档），@editor 列出候选URL请其确认，确认后立即抓取
- 不要自己编造内容"""
