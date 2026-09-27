# -*- coding: utf-8 -*-
"""
搜打撤 (Extraction Shooter) 研究 —— 第 1 步：生成模拟对局数据
=================================================================
目的：在拿到真实数据之前，先用一条"已知的真实规律"生成数据，
     用来跑通整条分析流水线，并检验分析方法能否把规律"恢复"出来。

内置的真实规律（生成数据的"上帝视角"，分析脚本事先不知道）：
  挫败感 = 1.2 + 2.5*损失率 + 6.0*max(0, 损失率-0.70)^2   ← 70% 处存在阈值拐点
          + 1.0*死亡 + 0.6*死于玩家 + 玩家个体敏感度 + 噪声 （截断到 1~10 分）

输出：data/matches.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)
N_PLAYERS = 120
THRESHOLD = 0.70  # 上帝视角的真实拐点：损失率 70%
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


def true_frustration(x, died, died_to_player, sens) -> float:
    """上帝视角的真实曲线：损失率 -> 挫败感（分析脚本不知道这个公式）。"""
    f = (1.2
         + 2.5 * x                                  # 线性成分
         + 6.0 * max(0.0, x - THRESHOLD) ** 2       # 阈值效应：超过 70% 后陡增
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
            else:
                loss_rate = float(RNG.beta(1.5, 9))                # 成功撤离 → 损失很小
            loss_rate = min(loss_rate, 1.0)

            f = true_frustration(loss_rate, int(died), died_to_player, p.sens)
            # 行为层负反馈：挫败感越高，越可能提前结束本次会话（秒退/不打下一局）
            p_quit = 1.0 / (1.0 + np.exp(-(3.0 * (f - 5.0) / 3.0)))

            rows.append({
                "player_id": p.player_id,
                "match_id": mid,
                "skill": round(p.skill, 3),
                "wealth_group": str(p.wealth_group),
                "carry_value": round(carry, 1),
                "lost_value": round(carry * loss_rate, 1),
                "loss_rate": round(loss_rate, 4),
                "died": int(died),
                "died_to_player": died_to_player,
                "survived_min": round(float(RNG.uniform(0, 24) if died else RNG.uniform(24, 30)), 1),
                "frustration": round(f, 2),
                "early_quit": int(RNG.random() < p_quit),
                "next_gap_min": round(float(RNG.lognormal(1.5 + 1.2 * (1 - p_quit), 0.5)), 1),
            })

    df = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"已生成 {len(df)} 条对局数据（{df['player_id'].nunique()} 名玩家）-> {OUT}")
    print(f"真实拐点（上帝视角）: 损失率 = {THRESHOLD:.0%}，待分析脚本去恢复")
    print("\n字段说明: loss_rate=损失率(本局损失/携带价值), frustration=局后挫败感1~10,")
    print("          early_quit=是否提前结束会话, carry_value/lost_value=携带/丢失价值")
    print("\n前 5 行预览:")
    print(df.head().to_string(index=False))


if __name__ == "__main__":
    main()
