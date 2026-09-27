# -*- coding: utf-8 -*-
"""
搜打撤研究 —— 调查问卷模板 + 批量录入脚本
============================================
使用方法:
  1. 打印/导出 survey_template.csv, 手动填写玩家数据
  2. 运行 python validate_survey.py survey.csv
  3. 将验证通过的 csv 放入 data/ 目录
  4. python fit_improved.py data/你的调查数据.csv  (生成新曲线)
  5. python analyze.py data/你的调查数据.csv         (完整报表)
"""

SURVEY_COLUMNS = [
    # === 必填字段 ===
    ("player_id", "int", "玩家唯一ID（可匿名编号, 如 A01, B02）"),
    ("match_id", "int", "第几局（每人可填多局）"),
    ("carry_value", "float", "本局携带总价值（装备+子弹+容器等）"),
    ("lost_value", "float", "本局丢失总价值（装备+战利品中未回收部分）"),

    # === 核心因变量 ===
    ("frustration", "int", "局后挫败感评分（1=毫无感觉, 10=非常愤怒）"),
    ("willingness", "int", "继续游玩意愿（1=完全不想玩, 10=立刻再来一局）"),

    # === 情境控制变量 ===
    ("died", "int", "本局是否死亡（0=成功撤离, 1=死亡/被淘汰）"),
    ("death_cause", "text", "死因（player=被玩家击杀, ai=被AI击杀, extract=撤离失败, survive=成功撤离）"),

    # === 挫败感来源 (核心调节变量) ===
    ("frust_source", "text", "挫败感主要来源（death=死亡本身, loss=丢失物品价值, both=两者都有, other=其他）"),

    # === 可选辅助字段 ===
    ("survived_min", "float", "本局存活时间（分钟, 可选）"),
    ("wealth_group", "text", "库存水平自我评估（poor=较穷, medium=中等, rich=较富裕, 可选）"),
    ("skill_level", "text", "技术水平自评（beginner=新手, intermediate=中等, veteran=老手, 可选）"),
    ("note", "text", "备注/补充信息（可选）"),
]


def generate_template(path="survey_template.csv"):
    """生成空白调查问卷 CSV 模板。"""
    import csv, os
    headers = [c[0] for c in SURVEY_COLUMNS]
    comments = [c[2] for c in SURVEY_COLUMNS]
    rows = []
    # 第一行: 表头
    rows.append(headers)
    # 第二行: 注释行 (以 # 开头标记为注释)
    rows.append([f"# {c}" for c in comments])
    # 第三行: 示例数据
    example = {
        "player_id": "A01",
        "match_id": "1",
        "carry_value": "50000",
        "lost_value": "42000",
        "frustration": "8",
        "willingness": "3",
        "died": "1",
        "death_cause": "player",
        "frust_source": "death",
        "survived_min": "12.5",
        "wealth_group": "medium",
        "skill_level": "intermediate",
        "note": "这把卡没了三级甲",
    }
    rows.append([example.get(h, "") for h in headers])
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerows(rows)
    print(f"[OK] 问卷模板已生成: {path}")


if __name__ == "__main__":
    generate_template()