'''
文档 -》 数据库
'''

from sqlalchemy import text
from db.database import async_session
from db.models import Document, Chunk
from .parser import parse_document
from .chunker import chunk_text
from .embedder import embed_texts

async def load_document(
        title: str,
        content: str,
        source_type: str = "markdown",
        source_url: str | None = None,
) -> str:
    '''
    加载一篇文档：解析 -》 分块 -〉 embedding -》 存入数据库
    返回 document_id
    '''
    # 1. 解析：从各种格式提取纯文本
    cleaned_text = parse_document(content, source_type)

    # 2. 分块
    chunks = chunk_text(cleaned_text)
    if not chunks:
        raise ValueError("文档分块后为空")
    
    # 3. 批量embedding
    chunk_contents = [c['content'] for c in chunks]
    embeddings = embed_texts(chunk_contents)

    # 4. 存入数据库
    async with async_session() as session:
        # 存 Document
        doc = Document(
            title = title,
            source_url = source_url,
            source_type = source_type,
            raw_content = content,
        )

        session.add(doc)
        await session.flush()   # Document 存进去后需要doc.id来关联Chunk。不flush的话，doc.id可能还没生成


        # 存 chunks
        for i, (chunk_data, embedding) in enumerate(zip(chunks, embeddings)):
            chunk = Chunk(
                document_id = doc.id,
                content = chunk_data['content'],
                chunk_index = i,
                dense_embedding = embedding,
                metadata_ = {"title": title}
            )
            session.add(chunk)
        await session.commit()

    # 5. 异步更新 tsvector(SQLAlchemy 不太好自动处理)
    await _update_tsvector()

    return doc.id

async def _update_tsvector() -> None:
    '''为所有未生成 tsvector的chunk 生成全文检索向量（这里是什么意思，parse检索的关键词吗）'''
    async with async_session() as session:
        await session.execute(
            text(
                """
UPDATE chunks
SET tsv = to_tsvector('simple', content)
WHERE tsv IS NULL
"""
            )
        )
        await session.commit()
