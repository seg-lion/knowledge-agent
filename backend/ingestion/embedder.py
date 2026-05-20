from sentence_transformers import SentenceTransformer
from config import get_settings

settings = get_settings()

# 模型只加载一次，全局复用
model = SentenceTransformer(settings.embedding_model, device=settings.embedding_device)

def embed_texts(texts: list[str]) -> list[list[float]]:
    '''
    批量生成 dense embedding
    '''
    if not texts:
        return []
    embeddings = model.encode(
        texts,
        normalize_embeddings= True,
        show_progress_bar= False,
    )
    return embeddings.tolist()

def embed_text(text: str) -> list[float]:
    '''
    单条文本 embedding
    '''
    return embed_texts([text])[0]