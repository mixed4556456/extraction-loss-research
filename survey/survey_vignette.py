# -*- coding: utf-8 -*-
"""
搜打撤研究 —— 场景法问卷（路线 B）刺激材料 + 长表答题模板 生成器
================================================================
设计说明见 questionnaire_design.md §3。

使用方法:
  python survey_vignette.py            # 打印 1 条示例行（确认列含义用）
  python survey_vignette.py 50         # 生成 50 人份空白答题表（P01~P50 × 22 情境）
  收完后另存为 data/survey_matches.csv，即可直接跑:
      python src/fit_improved.py data/survey_matches.csv

产物:
  survey_vignette_scenarios.csv   情境刺激表（22 条, 含完整题面文本）
  survey_vignette_responses.csv   长表答题模板（列名与 data/matches.csv 一致）
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent      # 产物写在脚本同目录（survey/），与运行时的 CWD 无关

CARRY_A = 50000.0                       # Block A 固定携带价值（关键：不能变）
# Block A：损失率梯度 —— 50%~100% 加密，否则拐点估不出来（见设计文档 §0）
LOSS_LEVELS = [0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.65, 0.70, 0.75, 0.80, 0.90, 1.00]
# Block B：固定 80% 损失率，只改携带/损失金额（尺度效应）
SCALE_VALUES = [10000.0, 50000.0, 200000.0, 1000000.0]
# Block C：固定 80% + 50,000，只改"怎么没的"（归因分离）
CAUSES = [
    ("player", "你被一名真人玩家击杀"),
    ("ai", "你被一个 AI 精英怪击杀"),
    ("extract", "你成功带着东西跑到撤离点，但撤离读条最后一秒失败"),
    ("extract", "你没死，但被毒圈 / 环境伤害拖到时间结束，东西全没"),
]

RESP_COLS = ["player_id", "match_id", "block", "carry_value", "lost_value", "loss_rate",
             "frustration", "willingness", "died", "death_cause", "frust_source", "note"]
RESP_CMTS = ["玩家编号", "情境序号", "区块 A/B/C/D", "携带总价值", "损失总价值", "损失率(0~1)",
             "挫败感 1~10 ★必填", "继续意愿 1~10", "是否死亡", "死因(player/ai/extract/survive/na)",
             "挫败来源(C-2: death/loss/both/other)", "备注"]


def build_scenarios():
    """构造 22 条情境刺激（A×13 + B×4 + C×4 + D×1）。"""
    rows = []
    for i, L in enumerate(LOSS_LEVELS, 1):
        lost = CARRY_A * L
        rows.append({
            "scenario_id": f"A{i}", "block": "A", "slot": i,
            "carry_value": CARRY_A, "lost_value": lost, "loss_rate": L,
            "died": 1, "death_cause": "na",
            "text": (f"🎮 情境 #{i}\n你带进场的装备、子弹和容器，总价值 {CARRY_A:,.0f} 金币。\n"
                     f"这一局你打得很不顺，最终阵亡，损失总价值 {lost:,.0f} 金币"
                     f"（相当于携带总价值的 {L*100:.0f}%）。\n场上没有任何队友能帮你带回东西。"),
        })
    for i, cv in enumerate(SCALE_VALUES, 1):
        lost = cv * 0.8
        rows.append({
            "scenario_id": f"B{i}", "block": "B", "slot": 20 + i,
            "carry_value": cv, "lost_value": lost, "loss_rate": 0.8,
            "died": 1, "death_cause": "na",
            "text": (f"🎮 情境 #B{i}\n你带进场的装备、子弹和容器，总价值 {cv:,.0f} 金币。\n"
                     f"这一局你打得很不顺，最终阵亡，损失总价值 {lost:,.0f} 金币"
                     f"（相当于携带总价值的 80%）。"),
        })
    for i, (cause, desc) in enumerate(CAUSES, 1):
        lost = CARRY_A * 0.8
        rows.append({
            "scenario_id": f"C{i}", "block": "C", "slot": 30 + i,
            "carry_value": CARRY_A, "lost_value": lost, "loss_rate": 0.8,
            "died": 1, "death_cause": cause,
            "text": (f"🎮 情境 #C{i}\n你带进场的装备、子弹和容器，总价值 {CARRY_A:,.0f} 金币。\n"
                     f"{desc}，损失总价值 {lost:,.0f} 金币（相当于携带总价值的 80%）。"),
        })
    rows.append({
        "scenario_id": "D1", "block": "D", "slot": 40,
        "carry_value": CARRY_A, "lost_value": 0.0, "loss_rate": 0.0,
        "died": 0, "death_cause": "survive",
        "text": (f"🎮 情境 #D1\n你带了 {CARRY_A:,.0f} 金币的装备进场，这一局成功撤离，"
                 f"一件东西都没丢，还额外赚了 20,000。"),
    })
    return rows


def write_scenarios(path, scenarios):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scenario_id", "block", "order_slot", "carry_value", "lost_value",
                    "loss_rate_pct", "died", "death_cause", "stimulus_text"])
        w.writerow(["# 情境编号", "# 区块", "# 建议呈现位", "# 携带总价值", "# 损失总价值",
                    "# 损失率%", "# 是否死亡", "# 死因", "# 题面文本(换行用 / 表示)"])
        for s in scenarios:
            w.writerow([s["scenario_id"], s["block"], s["slot"], f'{s["carry_value"]:.0f}',
                        f'{s["lost_value"]:.0f}', f'{s["loss_rate"]*100:.0f}',
                        s["died"], s["death_cause"], s["text"].replace("\n", " / ")])
    print(f"[OK] 情境刺激表已生成: {path}  ({len(scenarios)} 条)")


def write_responses(path, scenarios, n_players):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(RESP_COLS)
        w.writerow([f"# {c}" for c in RESP_CMTS])
        if n_players <= 1:
            # 只给 1 条示例行，用来确认每一列该填什么
            ex = scenarios[8]      # A9 = 损失率 70%（模拟数据的真拐点）
            w.writerow(["P01(示例)", ex["slot"], ex["block"], f'{ex["carry_value"]:.0f}',
                        f'{ex["lost_value"]:.0f}', f'{ex["loss_rate"]:.4f}', "7", "4",
                        ex["died"], ex["death_cause"], "loss", "这把卡没了三级甲"])
            print(f"[OK] 答题模板已生成: {path}  (1 条示例行; 加参数 N 生成 N 人份空白表)")
        else:
            for p in range(1, n_players + 1):
                pid = f"P{p:02d}"
                for s in scenarios:
                    w.writerow([pid, s["slot"], s["block"], f'{s["carry_value"]:.0f}',
                                f'{s["lost_value"]:.0f}', f'{s["loss_rate"]:.4f}',
                                "", "", s["died"], s["death_cause"], "", ""])
            print(f"[OK] 答题模板已生成: {path}  ({n_players} 人 × {len(scenarios)} 情境)")


def main():
    n_players = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    sc = build_scenarios()
    write_scenarios(ROOT / "survey_vignette_scenarios.csv", sc)
    write_responses(ROOT / "survey_vignette_responses.csv", sc, n_players)
    print("[提示] Block A 的 13 题是核心（估曲线+拐点）；资源紧张时可只做 A 块。")
    print("[提示] 收完后另存为 data/survey_matches.csv，再跑 fit_improved.py / analyze.py")


if __name__ == "__main__":
    main()