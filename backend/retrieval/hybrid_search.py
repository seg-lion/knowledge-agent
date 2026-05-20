from sqlalchemy import text #text():把字符串变成SQL语句
from db.database import async_session   # 异步数据库会话
from config import get_settings

settings = get_settings()

async def dense_search(query_embedding: list[float], top_k: int | None = None) -> list[dict]:
    '''Dense 通路：pgvector 余弦相似度检索'''
    if top_k is None:
        top_k = settings.dense_top_k
    
    async with async_session() as session:  # 打开异步数据库连接
        result = await session.execute(
            text(   #1 - (c.dense_embedding <=> :embedding) AS similarity 计算问题向量与库中向量的相似度
                '''
                SELECT c.id, c.content, c.document_id, c.chunk_index,
                       1 - (c.dense_embedding <=> :embedding) AS similarity
                FROM chunks c
                WHERE c.dense_embedding IS NOT NULL
                ORDER BY c.dense_embedding <=> :embedding   
                LIMIT :limit
'''
            ),
            {"embedding": query_embedding, "limit": top_k}
        )
        rows = result.fetchall()
        #取出查到的所有行：[(id, content, document_id, chunk_index, similarity), ...]


    
    return [
        {
            "chunk_id": r[0],
            "content": r[1],
            "document_id": r[2],
            "chunk_index": r[3],
            "score": float(r[4]),
        }
        for r in rows
    ]


async def sparse_search(query_text: str, top_k: int | None = None) -> list[dict]:
    '''Sparse 通路: PostgreSQL tsvector 全文检索'''
    if top_k is None:
        top_k = settings.sparse_top_k
        
    async with async_session() as session:
        result = await session.execute(
            text(   # plainto_tsquery('simple', :query) AS query 把用户问题切成关键词
                """
            SELECT c.id, c.content, c.document_id, c.chunk_index,
                    ts_rank(c.tsv, query) AS rank
            FROM chunks c,
                    plainto_tsquery('simple', :query) AS query
            WHERE c.tsv @@ query
            ORDER BY rank DESC
            LIMIT :limit
"""
            ),
            {"query": query_text, "limit": top_k},
        )
        rows = result.fetchall()

    # 这是正常写法的简写
    return [
        {
            "chunk_id": r[0],
            "content": r[1],
            "document_id": r[2],
            "chunk_index": r[3],
            "score": float(r[4]),
        }
        for r in rows  
    ]

def reciprocal_rank_fusion(
        dense_results: list[dict],
        sparse_results: list[dict],
        k: int | None = None,
) -> list[dict]:
    '''RRF 融合： dense + sparse 两路排名加权合并去重'''
    if k is None:
        k = settings.rrf_k
    
    rrf_scores: dict[str, float] = {}
    content_map: dict[str, dict] = {}

    for rank, item in enumerate(dense_results, start= 1):
        cid = item['chunk_id']
        rrf_scores[cid] = rrf_scores.get(cid, 0) + 1.0 / (k + rank)
        content_map[cid] = item


    for rank, item in enumerate(sparse_results, start=1):
        cid = item["chunk_id"]
        rrf_scores[cid] = rrf_scores.get(cid, 0) + 1.0 / (k + rank)
        content_map[cid] = item    

    
    sorted_ids = sorted(rrf_scores, key=rrf_scores.get,reverse=True)
    fused = []
    for cid in sorted_ids:
        item = dict(content_map[cid])
        item['rrf_score'] = rrf_scores[cid]
        fused.append(item)

    return fused


