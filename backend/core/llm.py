from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from config import get_settings

settings = get_settings()

# 只初始化用得到的客户端
openai_client: AsyncOpenAI | None = None
anthropic_client: AsyncAnthropic | None = None

def _get_openai() -> AsyncOpenAI:
    global openai_client
    if openai_client is None:
        openai_client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,    # DeepSeek兼容OpenAI接口
        )
    
    return openai_client

async def llm_call(system_prompt: str, user_message: str, provider: str = 'deepseek', model: str = 'deepseek-v4-flash') -> str:
    '''
    统一的llm调用入口
    provider： 'deepseek' | 'openai' | 'anthropic'
    返回模型输出的文本内容
    '''
    if provider in ('deepseek', 'openai'):
        client = _get_openai()
        response = await client.chat.completions.create(
            model = model,
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.0 # 检索/分类场景，降低随机性
        )
        return response.choices[0].message.content or ""
    
    elif provider == 'anthropic':
        global anthropic_client
        if anthropic_client is None:
            anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await anthropic_client.messages.create(
            model=model,
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content":user_message}]

        )
        return response.content[0].text
    
    else:
        raise ValueError(f"Unknown provider:{provider}")

