# -*- coding: utf-8 -*-
"""
搜打撤 (Extraction Shooter) 研究 —— 第 1 步：生成模拟对局数据
=================================================================
目的：在拿到真实数据之前，先用一条"已知的真实规律"生成数据，
      用来跑通整条分析流水线，并检验分析方法能否把规律"恢复"出来。

内置的真实规律（生成数据的"上帝视角"，分析脚本事先不知道）：
  挫败感 = 1.2 + 2.5*min(总损失率, 1.5) + 4.0*max(0, 总损失率-0.70)^1.5
          + 1.0*死亡 + 0.6*死于玩家 + 玩家个体敏感度 + 噪声 （截断到 1~10 分）
  
  总损失率 = (装备损失 + 战利品损失) / 携带价值
  死亡时装备+战利品全丢 → 总损失率 > 100% 常见（可高达 600%+）

输出：data/matches.csv
  - total_loss_ratio 是主要 X 轴指标（取代旧版 loss_rate）
  - loss_rate 仅作为副字段保留（兼容旧版分析）
"""
from pathlib import Path

import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)
N_PLAYERS = 500
THRESHOLD = 0.70  # 上帝视角的真实拐点：总损失率 70%
OUT = Path(__file__).resolve().parent / "data" / "matches.csv"


def make_players() -> pd.DataFrame:
    """生成玩家：技术水平、库存财富、个体挫败敏感度。"""
    df = pd.DataFrame({
        "player_id": np.arange(1, N_PLAYERS + 1),
        "skill": RNG.beta(2, 2, N_PLAYERS),            # 技术水平 0~1
        "wealth": RNG.lognormal(10.0, 0.7, N_PLAYERS),  # 库存财富基准（游戏币）
        "sens": RNG.normal(0, 0.7, N_PLAYERS),          # 个体挫败敏感度
    })
    df["wealth_group"] = pd.qcut(df["wealth"], 3, labels=["穷人", "中产", "富人"])
    return df


def generate_loot(RNG, survived_min, wealth, early=False):
    """模拟局内找到的战利品价值（取决于停留时间和幸运值）。
    
    调控产出以覆盖全范围总损失率（0~0.5 存活区、0.5~1.5 过渡区、1.5+ 高危区）。
    - 早期死亡 (early=True): 几乎没找到什么东西 → tlr ≈ 1.0~1.2
    - 正常死亡: 找到中等偏多战利品 → tlr ≈ 1.2~2.5
    - 存活: 战利品带出（丢失价值不包含战利品）
    """
    base_mult = 0.4  # 调低基础倍率使 tlr 从 1.0 开始渐变
    time_factor = 0.2 + 0.8 * min(survived_min / 30.0, 1.0)
    loot = max(0, RNG.lognormal(np.log(wealth * base_mult), 1.2) * time_factor)
    if early:
        loot *= RNG.uniform(0.1, 0.6)  # 早期死亡：少量到中等战利品
    return float(loot)


def true_frustration(x, died, died_to_player, sens) -> float:
    """上帝视角的真实曲线：总损失率 -> 挫败感（分析脚本不知道这个公式）。
    
    Parameters
    ----------
    x : float  总损失率 (total_loss_ratio)，可 > 1.0（死亡时装备+战利品全丢）
    
    关键特征：
    - 0~70% 线性缓慢上升
    - 70% 后二次方加速上升（阈值效应明显）
    - 200% 左右趋近最大值，250%+ 被截断到 10
    """
    f = (1.2
         + 2.5 * x                                  # 线性成分
         + 6.0 * max(0.0, x - THRESHOLD) ** 2        # 阈值效应：超过 70% 后二次方加速
         + 1.0 * died                               # 死亡本身的挫败
         + 0.6 * died_to_player                     # 被玩家击杀额外挫败
         + sens                                     # 玩家个体差异
         + RNG.normal(0, 0.8))                      # 单局随机噪声
    return float(np.clip(f, 1, 10))


def main() -> None:
    players = make_players()
    rows, mid = [], 0
    for p in players.itertuples():
        for _ in range(int(RNG.integers(15, 41))):     # 每人 15~40 局
            mid += 1
            carry = max(p.wealth * RNG.lognormal(0, 0.6), 300.0)  # 白装保底
            died = RNG.random() < (0.55 - 0.35 * p.skill)         # 技术越好越容易撤离
            died_to_player = 0
            if died:
                loss_rate = RNG.beta(6, 2) * 0.95 + 0.05           # 死亡 → 损失惨重
                cause = RNG.choice(["player", "ai", "extract_fail"], p=[0.7, 0.2, 0.1])
                died_to_player = int(cause == "player")
                # 双峰死亡分布：早期死亡(搜到很少) vs 晚期死亡(搜到很多)
                early_death_flag = RNG.random() < 0.50
                if early_death_flag:
                    survived_min = round(float(RNG.uniform(1, 10)), 1)  # 开局就死
                else:
                    survived_min = round(float(RNG.uniform(10, 28)), 1) # 搜了挺久
            else:
                # 部分存活局仍有较大装备损失（激战幸存、装备严重损坏）
                if RNG.random() < 0.35:
                    loss_rate = float(RNG.beta(2, 2))              # 重损幸存（均值0.5，分布宽，覆盖0.3~0.9）
                else:
                    loss_rate = float(RNG.beta(1.5, 9))            # 轻损幸存
                survived_min = round(float(RNG.uniform(20, 30)), 1)
            loss_rate = min(loss_rate, 1.0)

            # --- 局内找到的战利品（死亡时才会丢失） ---
            found_loot = generate_loot(RNG, survived_min, p.wealth, early=early_death_flag) if died else generate_loot(RNG, survived_min, p.wealth)
            if died:
                # 死亡：装备+战利品全丢
                total_lost = carry + found_loot
                potential_change_ratio = -(carry + found_loot) / carry  # 负值 = 净损失
            else:
                # 成功撤离：仅消耗/损坏的装备，战利品带出
                total_lost = carry * loss_rate
                potential_change_ratio = (found_loot - total_lost) / carry  # 正值 = 净收益

            total_loss_ratio = total_lost / carry  # 可超过 1.0
            # 挫败感由总损失率驱动（取代旧版 loss_rate）
            f = true_frustration(total_loss_ratio, int(died), died_to_player, p.sens)
            # 行为层负反馈
            p_quit = 1.0 / (1.0 + np.exp(-(3.0 * (f - 5.0) / 3.0)))

            rows.append({
                "player_id": p.player_id,
                "match_id": mid,
                "skill": round(p.skill, 3),
                "wealth_group": str(p.wealth_group),
                "carry_value": round(carry, 1),
                "found_loot_value": round(found_loot, 1),
                "lost_value": round(total_lost, 1),
                "loss_rate": round(loss_rate, 4),
                "total_loss_ratio": round(total_loss_ratio, 4),
                "potential_change_ratio": round(potential_change_ratio, 4),
                "died": int(died),
                "died_to_player": died_to_player,
                "survived_min": survived_min,
                "frustration": round(f, 2),
                "early_quit": int(RNG.random() < p_quit),
                "next_gap_min": round(float(RNG.lognormal(1.5 + 1.2 * (1 - p_quit), 0.5)), 1),
            })

    df = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"已生成 {len(df)} 条对局数据（{df['player_id'].nunique()} 名玩家）-> {OUT}")
    print(f"真实拐点（上帝视角）: 总损失率 = {THRESHOLD:.0%}，待分析脚本去恢复")
    print(f"\n数据分布特征:")
    print(f"  total_loss_ratio 范围: {df['total_loss_ratio'].min():.4f} ~ {df['total_loss_ratio'].max():.4f}")
    print(f"  >100%%: {(df['total_loss_ratio']>1).sum()} 条  ({((df['total_loss_ratio']>1).mean()*100):.1f}%%)")
    print(f"  >200%%: {(df['total_loss_ratio']>2).sum()} 条")
    print(f"  >300%%: {(df['total_loss_ratio']>3).sum()} 条")
    print(f"  最高: {df['total_loss_ratio'].max():.2f}x")
    print(f"\n前 5 行预览:")
    print(df.head().to_string(index=False))


if __name__ == "__main__":
    main()
