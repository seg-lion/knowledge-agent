"""
记忆系统评估：兴趣模型准确率、衰减曲线合理性

评估方法：
1. 兴趣准确率：模拟用户行为序列 → 检查系统产生的兴趣是否匹配预期
2. 衰减曲线：模拟时间流逝 → 检查置信度衰减是否符合预期曲线
"""

import json
from datetime import datetime, timezone, timedelta
from memory.long_term import write_interest, get_active_interests, record_access, check_auto_capture
from memory.decay import apply_decay


async def evaluate_interest_accuracy() -> dict:
    """
    兴趣模型准确率评估：
    模拟用户连续 6 次搜索 "agent-memory" → 验证 auto_capture 是否触发
    """
    topic = "agent-memory-eval-test"

    # 模拟用户连续搜索
    for _ in range(6):
        await record_access(topic)

    captured = await check_auto_capture(topic)

    # 验证：6 次访问应该触发自动捕获（阈值 = 5）
    return {
        "test": "auto_capture_trigger",
        "topic": topic,
        "access_count": 6,
        "threshold": 5,
        "captured": captured,
        "passed": captured,  # 6 >= 5 应该触发
    }


async def evaluate_decay_curve() -> dict:
    """
    衰减曲线合理性评估：
    创建一条记忆 → 模拟 0/30/60/90 天后的衰减 → 验证置信度变化
    """
    topic = "decay-curve-test"
    await write_interest(topic, memory_type="preference", confidence=1.0)

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    milestones = [
        {"label": "初始", "days": 0, "expected_min": 0.95, "expected_max": 1.0},
        {"label": "30天后", "days": 30, "expected_min": 0.85, "expected_max": 0.95},
        {"label": "60天后", "days": 60, "expected_min": 0.75, "expected_max": 0.90},
        {"label": "90天后", "days": 90, "expected_min": 0.65, "expected_max": 0.85},
    ]

    results = []
    for m in milestones:
        past = now - timedelta(days=m["days"])
        conf = apply_decay(1.0, past, now)
        passed = m["expected_min"] <= conf <= m["expected_max"]
        results.append({
            "label": m["label"],
            "confidence": round(conf, 4),
            "expected_range": f"{m['expected_min']}~{m['expected_max']}",
            "passed": passed,
        })

    all_passed = all(r["passed"] for r in results)

    return {
        "test": "decay_curve",
        "results": results,
        "all_passed": all_passed,
        "note": "衰减曲线遵循 0.9^(days/30) 公式，30天衰减10%，90天衰减约27%"
    }


async def evaluate_memory_consolidation() -> dict:
    """
    记忆巩固效果评估：
    同一主题被反复访问 → 置信度应该上升（巩固），而不是一直衰减
    """
    topic = "memory-consolidation-test"

    await write_interest(topic, memory_type="preference", confidence=0.5)

    # 模拟 5 次巩固（每次访问 +0.1 上限 1.0）
    for _ in range(5):
        await record_access(topic)

    interests = await get_active_interests()
    target = next((i for i in interests if i["topic"] == topic), None)

    if target is None:
        return {"test": "memory_consolidation", "passed": False, "error": "未找到测试记忆"}

    # 5 次巩固后，置信度应从 0.5 提升
    passed = target["confidence"] > 0.5

    return {
        "test": "memory_consolidation",
        "initial_confidence": 0.5,
        "after_consolidation": target["confidence"],
        "access_count": target["access_count"],
        "passed": passed,
    }


async def run_memory_evaluation() -> dict:
    """跑完整记忆系统评估"""
    results = {}

    print("\n🧪 兴趣模型准确率（自动捕获）...")
    r1 = await evaluate_interest_accuracy()
    results["interest_accuracy"] = r1
    print(f"   {'✅ 通过' if r1['passed'] else '❌ 失败'}: {r1['access_count']}次访问 → {'已捕获' if r1['captured'] else '未捕获'}")

    print("🧪 衰减曲线合理性...")
    r2 = await evaluate_decay_curve()
    results["decay_curve"] = r2
    for item in r2["results"]:
        print(f"   {item['label']}: confidence={item['confidence']} {'✅' if item['passed'] else '❌'}")

    print("🧪 记忆巩固效果...")
    r3 = await evaluate_memory_consolidation()
    results["memory_consolidation"] = r3
    print(f"   {'✅ 通过' if r3['passed'] else '❌ 失败'}: 置信度 {r3.get('initial_confidence', 0)} → {r3.get('after_consolidation', 0)}")

    passed_count = sum(1 for r in results.values() if r.get("passed", False))
    total = len(results)
    print(f"\n记忆系统评估：{passed_count}/{total} 项通过")

    return {
        "results": results,
        "passed": passed_count,
        "total": total,
    }


def print_memory_eval_report(output: dict) -> None:
    print("\n" + "=" * 50)
    print("记忆系统评估报告")
    print("-" * 50)
    print(f"  通过项: {output['passed']}/{output['total']}")
    print("=" * 50)


if __name__ == "__main__":
    import asyncio
    from db.database import init_db
    async def main():
        await init_db()
        result = await run_memory_evaluation()
        print_memory_eval_report(result)
    asyncio.run(main())
