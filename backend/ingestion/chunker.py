"""
文档切分
"""

import re   # 正则表达式，在文本里找符号、找句子、分割、替换、清洗
from config import get_settings

settings = get_settings()

def estimate_tokens(text:str) -> int:
    '''
    粗略估算token数：中文 1字 = 1token， 英文 1 词 = 1.3 token
    '''
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    english_words = len(re.findall(r'[a-zA-Z]+', text))

    return chinese_chars + int(english_words * 1.3)


def split_by_paragraphs(text: str) -> list[str]:
    '''按段落切分：空行或MarkDown标题作为分界'''
    blocks = re.split(r'\n(?=#{1,6}\s)|\n{2,}', text)
    return [b.strip() for b in blocks if b.strip()]


def split_long_paragraph(para: str, max_tokens: int) -> list[str]:
    """
    降级策略：段落超过 max_tokens 时，按句子边界递归切分。
    切分优先级：句号/问号/感叹号 > 分号 > 逗号 > 空格
    """
    if estimate_tokens(para) <= max_tokens:
        return [para]

    # 找最佳切分点：在 para 中间附近找句子边界
    mid = len(para) // 2
    # 在中间附近往后找最近的句子结束符
    match = re.search(r'[。！？!?\n]', para[mid:])
    split_pos = mid + match.start() + 1 if match else None

    # 没找到句子边界，退而求其次找分号或逗号
    if split_pos is None or split_pos >= len(para) - 10:
        match = re.search(r'[；;，,]', para[mid:])
        split_pos = mid + match.start() + 1 if match else None

    # 实在找不到切分点，在 max_tokens 对应的字符位置切
    if split_pos is None:
        split_pos = min(int(len(para) * 2 / 3), len(para) - 50)

    left = para[:split_pos].strip()
    right = para[split_pos:].strip()

    if not left or not right:
        return [para]

    # 递归处理右边（可能仍然超长）
    return [left] + split_long_paragraph(right, max_tokens)

def chunk_text(text: str) -> list[dict]:
    '''
    语义分块：按段落切分后，合并短段落、拆分长段落
    确保每块在chunk_min ~ chunk_max token之间，且相邻块有 overlap
    
    '''
    # 先处理超长段落：每个段落如果超过 chunk_max_tokens，按句子边界切开
    all_paragraphs = []
    for p in split_by_paragraphs(text):
        all_paragraphs.extend(split_long_paragraph(p, settings.chunk_max_tokens))

    chunks = []
    current_chunk = ""
    chunk_index = 0

    for para in all_paragraphs:
        candidate = current_chunk + "\n" + para if current_chunk else para

        if estimate_tokens(candidate) <= settings.chunk_max_tokens:
            current_chunk = candidate
        else:
            # 当前 chunk 已满，保存并开启新 chunk
            if current_chunk:
                chunks.append(
                    {
                        "content": current_chunk.strip(),
                        "chunk_index": chunk_index,
                    }
                )
                chunk_index += 1

                # overlap： 把当前 chunk 尾部 10% 的内容作为新 chunk 的开头
                if settings.chunk_overlap_ratio > 0:
                    text_len = len(current_chunk)
                    overlap_len = int(text_len * settings.chunk_overlap_ratio)
                    current_chunk = current_chunk[-overlap_len:] + "\n" + para
                else:
                    current_chunk = para
            else:
                # 降级后仍然超长（极少发生）→ 直接作为一个独立 chunk
                chunks.append(
                    {
                        "content": para.strip(),
                        "chunk_index": chunk_index,
                    }
                )
                chunk_index += 1
                current_chunk = ""
    
    # 最后一个 chunk
    '''
    因为前面的循环是：
拼满了才保存
但最后一段往往没拼满，循环就结束了！
所以必须手动保存最后一块。

    '''
    if current_chunk: 
        chunks.append(
            {
                "content": current_chunk.strip(),
                "chunk_index": chunk_index,
            }
        )

    # 合并太短的 chunk 到相邻块
    merged = []
    for c in chunks:
        if estimate_tokens(c['content']) < settings.chunk_min_tokens and merged:
            merged[-1]['content'] += "\n" + c['content']
        else:
            c['chunk_index'] = len(merged)
            merged.append(c)

    return merged