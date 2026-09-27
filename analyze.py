# -*- coding: utf-8 -*-
"""
搜打撤研究 —— 第 2 步：分析流水线
分箱曲线 -> LOESS 平滑 -> 分段回归找拐点 -> 贫富分层 -> 混合效应模型 -> 结论报告
用法: python analyze.py [csv路径]   （默认 data/matches.csv）
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")  # 只出图文件，不弹窗
import matplotlib.pyplot as plt
from statsmodels.nonparametric.smoothers_lowess import lowess
import statsmodels.formula.api as smf

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]  # 中文显示
plt.rcParams["axes.unicode_minus"] = False

RNG = np.random.default_rng(7)
ROOT = Path(__file__).resolve().parent
FIG = ROOT / "figs"
FIG.mkdir(exist_ok=True)


def binned_stats(df: pd.DataFrame, xcol: str, ycol: str, width: float = 0.1) -> pd.DataFrame:
    """按损失率分箱，计算每箱均值 ± 95% 置信区间。"""
    bins = np.floor(df[xcol] / width) * width + width / 2
    g = df.groupby(bins)[ycol]
    out = g.agg(["mean", "std", "count"]).reset_index()
    out.columns = ["bin_mid", "mean", "std", "n"]
    out["ci"] = 1.96 * out["std"] / np.sqrt(out["n"])
    return out


def fig1_binned(df: pd.DataFrame) -> pd.DataFrame:
    """图1：主观挫败感 + 行为负反馈 双面板分箱曲线。"""
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    st = binned_stats(df, "loss_rate", "frustration")
    axes[0].errorbar(st["bin_mid"], st["mean"], yerr=st["ci"], fmt="o-",
                     capsize=3, color="#c0392b")
    axes[0].set(title="主观负反馈：局后挫败感 (1~10 分)",
                xlabel="本局损失率 (损失价值 / 携带价值)", ylabel="挫败感均值 ±95%CI")
    st2 = binned_stats(df, "loss_rate", "early_quit")
    axes[1].errorbar(st2["bin_mid"], st2["mean"] * 100, yerr=st2["ci"] * 100,
                     fmt="s-", capsize=3, color="#2c3e50")
    axes[1].set(title="行为负反馈：局后提前结束会话比例",
                xlabel="本局损失率", ylabel="比例 (%)")
    for ax in axes:
        ax.grid(alpha=0.3)
    fig.suptitle("图1 分箱曲线：损失率 → 负反馈", y=1.02)
    fig.tight_layout()
    fig.savefig(FIG / "fig1_binned_curve.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    return st


def fig2_loess(df: pd.DataFrame) -> None:
    """图2：LOESS 局部加权平滑曲线。"""
    sm = lowess(df["frustration"].values, df["loss_rate"].values,
                frac=0.35, return_sorted=True)
    fig, ax = plt.subplots(figsize=(8, 5))
    idx = df.sample(min(800, len(df)), random_state=0).index
    ax.scatter(df.loc[idx, "loss_rate"], df.loc[idx, "frustration"],
               s=8, alpha=0.25, color="#95a5a6", label="单局散点（抽样 800）")
    ax.plot(sm[:, 0], sm[:, 1], lw=2.5, color="#c0392b", label="LOESS 平滑")
    ax.set(title="图2 LOESS 平滑：损失率 → 挫败感", xlabel="本局损失率", ylabel="挫败感")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG / "fig2_loess.png", dpi=150)
    plt.close(fig)


def fit_piecewise(x: np.ndarray, y: np.ndarray, c: float):
    """拟合 y = a + b1*x + b2*max(0, x-c)，返回 (SSE, 系数)。"""
    X = np.column_stack([np.ones_like(x), x, np.maximum(0.0, x - c)])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    return float(resid @ resid), beta


def find_breakpoint(df: pd.DataFrame, n_boot: int = 120):
    """网格搜索拐点 + Bootstrap 95% 置信区间。"""
    x = df["loss_rate"].values.astype(float)
    y = df["frustration"].values.astype(float)
    grid = np.arange(0.20, 0.91, 0.02)
    sse = [fit_piecewise(x, y, c)[0] for c in grid]
    c_hat = float(grid[int(np.argmin(sse))])
    boots = []
    for _ in range(n_boot):
        idx = RNG.choice(len(df), len(df), replace=True)
        sse_b = [fit_piecewise(x[idx], y[idx], c)[0] for c in grid]
        boots.append(grid[int(np.argmin(sse_b))])
    lo, hi = np.percentile(boots, [2.5, 97.5])
    _, beta = fit_piecewise(x, y, c_hat)
    return c_hat, float(lo), float(hi), beta, grid, sse


def fig3_breakpoint(df: pd.DataFrame):
    """图3：分段回归找拐点 + SSE 曲线。"""
    c_hat, lo, hi, beta, grid, sse = find_breakpoint(df)
    st = binned_stats(df, "loss_rate", "frustration")
    xs = np.linspace(0, 1, 200)
    ys = beta[0] + beta[1] * xs + beta[2] * np.maximum(0, xs - c_hat)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    axes[0].plot(xs, ys, color="#8e44ad", lw=2.5, label="分段线性拟合")
    axes[0].errorbar(st["bin_mid"], st["mean"], yerr=st["ci"], fmt="o",
                     capsize=3, color="#c0392b", label="分箱均值 ±95%CI")
    axes[0].axvline(c_hat, ls="--", color="#8e44ad", alpha=0.7)
    axes[0].set(title=f"图3 分段回归：拐点≈{c_hat:.0%}（95%CI {lo:.0%}~{hi:.0%}）",
                xlabel="本局损失率", ylabel="挫败感")
    axes[0].legend()
    axes[0].grid(alpha=0.3)

    axes[1].plot(grid, sse, "-o", ms=3, color="#2c3e50")
    axes[1].axvline(c_hat, ls="--", color="#c0392b")
    axes[1].set(title="各候选拐点的残差平方和（越低越好）",
                xlabel="候选拐点（损失率）", ylabel="SSE")
    axes[1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG / "fig3_breakpoint.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    return c_hat, lo, hi, beta


def fig4_stratified(df: pd.DataFrame) -> None:
    """图4：财富分层对比（调节效应）。"""
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = {"穷人": "#e67e22", "中产": "#2980b9", "富人": "#27ae60"}
    for g, sub in df.groupby("wealth_group", observed=True):
        sm = lowess(sub["frustration"].values, sub["loss_rate"].values,
                    frac=0.45, return_sorted=True)
        ax.plot(sm[:, 0], sm[:, 1], lw=2.5, color=colors.get(str(g)), label=f"{g} (n={len(sub)})")
    ax.set(title="图4 分层对比：不同财富水平玩家的负反馈曲线",
           xlabel="本局损失率", ylabel="挫败感（LOESS）")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG / "fig4_stratified.png", dpi=150)
    plt.close(fig)


def mixed_model(df: pd.DataFrame):
    """混合效应模型：控制玩家个体随机效应（同一玩家多局的重复测量）。"""
    try:
        md = smf.mixedlm("frustration ~ loss_rate + died + died_to_player",
                         df, groups=df["player_id"])
        return md.fit(reml=False)
    except Exception as e:  # 收敛失败时不阻断流程
        print(f"[提示] 混合效应模型未能收敛: {e}")
        return None


def report(df, st, c_hat, lo, hi, beta, res) -> None:
    lines = [
        "# 搜打撤损失 → 负反馈 分析报告（模拟数据演示）", "",
        f"- 样本：{df['player_id'].nunique()} 名玩家，{len(df)} 局",
        f"- 真实拐点（上帝视角）= **70%**，分析恢复的拐点 = **{c_hat:.0%}**（95%CI {lo:.0%}~{hi:.0%}）",
        f"- 分段拟合：低段斜率 = {beta[1]:.2f}，拐点后额外斜率 = {beta[2]:.2f}",
        "- 混合效应模型（控制玩家个体随机效应）：",
    ]
    if res is not None:
        for name in ["loss_rate", "died", "died_to_player"]:
            lines.append(f"    - {name}: β = {res.params[name]:.2f}（p = {res.pvalues[name]:.3g}）")
    lines += ["", "## 分箱均值表", "", "| 损失率区间中点 | 挫败感均值 | 95%CI | n |", "|---|---|---|---|"]
    for r in st.itertuples():
        lines.append(f"| {r.bin_mid:.2f} | {r.mean:.2f} | ±{r.ci:.2f} | {r.n} |")
    lines += [
        "", "## 结论模板（拿到真实数据后按此撰写）",
        "1. 曲线形状：___（平滑上升 / 阈值陡增 / 高损失回弹）",
        "2. 拐点位置：单局损失率超过 ___% 后负反馈显著加剧",
        "3. 调节效应：___ 玩家对损失更敏感（贫富 / 新老手）",
        "4. 设计建议：当单局损失超过携带价值的 ___% 时，触发保底、安抚或补偿机制",
    ]
    out = ROOT / "summary_report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\n报告已保存: {out}")


def main() -> None:
    csv = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "matches.csv"
    df = pd.read_csv(csv)
    print(f"载入 {len(df)} 局 / {df['player_id'].nunique()} 名玩家: {csv}\n")
    st = fig1_binned(df)
    fig2_loess(df)
    c_hat, lo, hi, beta = fig3_breakpoint(df)
    fig4_stratified(df)
    res = mixed_model(df)
    report(df, st, c_hat, lo, hi, beta, res)
    print(f"\n图表已保存到: {FIG}")


if __name__ == "__main__":
    main()

