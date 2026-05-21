from datetime import datetime, timezone
from sqlalchemy import select, update
from db.database import async_session
from db.models import UserInterest
from .decay import apply_decay, is_dormant
from config import get_settings

settings = get_settings()

async def get_active_interests() -> list[dict]:
    '''获取所有活跃兴趣（记忆）（未休眠）, 按置信度降序，用于注入context'''
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    async with async_session() as session:
        result = await session.execute(
            select(UserInterest).where(UserInterest.is_dormant == False)
            .order_by(UserInterest.confidence.desc())
        )

        interests = result.scalars().all()    # 把数据库返回的行变成python列表
    
    active = []
    for i in interests:
        # 实时衰减
        new_conf = apply_decay(i.confidence, i.last_accessed_at, now)
        if is_dormant(i.last_accessed_at, settings.interest_dormant_days, now):
            await _mark_dormant(i.id)
            continue
        if new_conf != i.confidence:
            await _update_confidence(i.id, new_conf)
        active.append(
            {
                "topic": i.topic,
                "confidence": round(new_conf, 3),
                "memory_type": i.memory_type,
                "access_count": i.access_count,
            }
        )
    return active

async def write_interest(
        topic: str,
        memory_type: str = "preference",
        confidence: float = 1.0,
) -> None:
    '''写入一条记忆，如果是事实性且已存在，覆盖旧的'''
    topic = topic.strip().lower()   # 格式化记忆文本，防止重复、统一格式

    async with async_session() as session:
        # 查重
        result = await session.execute(
            select(UserInterest).where(UserInterest.topic == topic)
        )
        existing = result.scalar_one_or_none() # 如果找到 -》 返回这条记忆

        now  = datetime.now(timezone.utc).replace(tzinfo=None)

        if existing:
            if memory_type == "factual" and existing.memory_type == "factual":
                # 事实型 -》 覆盖
                existing.confidence = confidence
            else:
                # 偏好型 -》 新旧加权平均
                existing.confidence = max(existing.confidence * 0.7 + confidence * 0.3, confidence)
            existing.last_accessed_at = now
            existing.access_count += 1
            existing.is_dormant = False # 这属于唤醒吗
        else:   # 没有重复的，就写进
            interest = UserInterest(
                topic = topic,
                confidence = confidence,
                memory_type = memory_type,
                last_accessed_at = now,
                access_count = 1,
            )
            session.add(interest)
        
        await session.commit()

async def record_access(topic: str) -> None:
    '''记录用户访问了某话题，更新 access_count 和 last_accessed_at'''
    topic = topic.strip().lower()

    async with async_session() as session:
        result = await session.execute(
            select(UserInterest).where(UserInterest.topic == topic)
        )

        existing = result.scalar_one_or_none()

        now = datetime.now(timezone.utc).replace(tzinfo=None)  

        if existing:
            existing.access_count += 1
            existing.last_accessed_at = now
            existing.is_dormant = False
        else:
            # 还没记录过的主题，建一条低置信度的
            interest = UserInterest(
                topic = topic,
                confidence = 0.5,
                memory_type = "perference",
                last_accessed = now,
                access_count = 1,
            )
        session.add(interest)
    await session.commit()


async def check_auto_capture(topic: str) -> bool:
    '''检查是否达到自动捕获阈值： 同一主题访问超过N篇，用户反复访问同一个主题，自动把他升级为“重要事实记忆”，并提高置信度'''
    topic = topic.strip().lower()

    async with async_session() as session:
        result = await session.execute(
            select(UserInterest).where(UserInterest.topic == topic)
        )
        existing = result.scalar_one_or_none()

        if existing and existing.access_count >= settings.interest_auto_capture_threshold:
            existing.memory_type = "factual"
            existing.confidence = min(existing.confidence + 0.1, 1.0)   # 为什么这样写
            await session.commit()  # 这里对existing操作的，数据库里面的会被同步吗
            return True
    
    return False
    


async def _update_confidence(interest_id: str, new_confidence: float) -> None:
    async with async_session() as session:
        await session.execute(
            update(UserInterest).where(UserInterest.id == interest_id).values(
                confidence = new_confidence,
                last_accessed = datetime.now(timezone.utc).replace(tzinfo=None)
            )
        )



async def _mark_dormant(interest_id: str) -> None:  # 修改休眠状态

    async with async_session() as session:
        await session.execute(
            update(UserInterest).where(UserInterest.id == interest_id).values(is_dormant = True)
        )

        await session.commit()