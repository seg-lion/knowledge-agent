'''
记忆衰减， 超过30天不访问就摔衰减，超过90天就休眠

'''

from datetime import datetime,timezone
import math

def apply_decay(confidence: float, last_accessed: datetime, now: datetime | None = None) -> float:
    '''
    艾宾浩斯启发式衰减：距离上次访问越久，置信度越低
    返回新置信度（0.0～1.0），不会被减到0以下
    confidence 是这条记忆/片段本身自带的“基础置信度”
    '''
    if now is None:
        now = datetime.now(timezone.utc).replace(tzinfo=None)  # 世界统一时间，datetime.now() 你电脑当前时区的时间
    
    days_since_access = (now - last_accessed).days  # 计算现在和最后访问时间之间相差了多少天
    if days_since_access <= 0:
        return confidence


    # 衰减系数：每30天乘一次0.9（每次衰减10%）
    decay_periods = days_since_access / 30
    decay_factor = math.pow(0.9, decay_periods)
    return max(confidence * decay_factor, 0.01) # 防止分数变成0 ，保留一点点权重，还能被检索到

def is_dormant(last_accessed: datetime, dormant_days: int = 90, now: datetime | None = None) -> bool:
    '''判断记忆是否进入休眠状态'''
    if now is None:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
    
    return(now - last_accessed).days > dormant_days
