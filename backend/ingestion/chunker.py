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


def split_by_paragraphs(text:str) -> list[str]:
    '''
    按段落切分：空行或MarkDown标题作为分界
    '''
    # 在 Markdown 标题前和连续空行处切开
    blocks = re.split(r'\n(?=#{1,6}\s)|\n{2,}', text)
    return [b.strip() for b in blocks if b.strip()]

def chunk_text(text: str) -> list[dict]:
    '''
    语义分块：按段落切分后，合并短段落、拆分长段落
    确保每块在chunk_min ~ chunk_max token之间，且相邻块有 overlap
    
    '''
    paragraphs = split_by_paragraphs(text)
    chunks = []
    current_chunk = ""
    chunk_index = 0

    for para in paragraphs:
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
                    # 直接用字符数取尾部——中英文都适用
                    current_chunk = current_chunk[-overlap_len:] + "\n" + para
                else:
                    current_chunk = para
            else:
                current_chunk = para # 处理第一个段落就超长的情况
    
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