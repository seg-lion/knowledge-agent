import json
from config import get_settings

settings = get_settings()

async def llm_rerank(
    query: str,
    candidates: list[dict],
    llm_call,
    top_k: int | None = None,
) -> list[dict]:
    '''用LLM对候选文档打分重排，llm_call 由上层传入，不在这里写死'''
    if top_k is None:
        top_k = settings.final_top_k
    
    if not candidates:
        return []
    
    # 构建 Prompt ：让LLM逐个打分
    candidates_text = ""
    for i, c in enumerate(candidates):
        candidates_text += f"[{i}] {c['content'][:300]}\n\n"
    
    system_prompt = (
        "你是一个检索质量评估器。根据用户问题，对每篇候选文档的相关性打分（1-5分）"
        "并给一句话理由，只返回 JSON 数组，格式：\n"
        '[{"index": 0, "score": 4, "reason": "直接回答了问题"}, ...]'
    )
    user_message = (
        f"用户问题: {query}\n\n"
        f"候选文档: \n{candidates_text}"
    )

    response = await llm_call(system_prompt, user_message)

    # 解析 LLM 返回的 JSON
    try:
        scores = json.loads(response)
    except json.JSONDecodeError:
        # LLM 返回格式不对时，返回原始顺序的前 top_k
        return candidates[:top_k]

    # 按 LLM 给的分数重新排序
    score_map = {s["index"]: s for s in scores}
    reranked = []
    for i, c in enumerate(candidates):
        if i in score_map:
            c["rerank_score"] = score_map[i]["score"]
            c["rerank_reason"] = score_map[i]["reason"]
            reranked.append(c)

    reranked.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
    return reranked[:top_k]