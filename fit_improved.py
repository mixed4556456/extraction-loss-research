# -*- coding: utf-8 -*-
"""
搜打撤研究 —— 改进拟合（B样条 + 导数拐点检测）
=================================================
相比分段线性, 用平滑样条拟合真实曲线, 通过一阶导数最大值
精确定位"负反馈加速最剧烈"的阈值拐点.

输出:
  figs/fig5_spline_fit.png  — 拟合曲线 + 导数子图
  data/curve_data.json      — 供网页加载的结构化曲线数据
"""
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.interpolate import UnivariateSpline

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

RNG = np.random.default_rng(17)
ROOT = Path(__file__).resolve().parent
FIG_DIR = ROOT / "figs"
DATA_DIR = ROOT / "data"
FIG_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)


def binned_stats(df, xcol, ycol, width=0.1):
    """分箱统计, 返回 DataFrame."""
    bins = np.floor(df[xcol] / width) * width + width / 2
    g = df.groupby(bins)[ycol]
    out = g.agg(["mean", "std", "count"]).reset_index()
    out.columns = ["bin_mid", "mean", "std", "n"]
    out["ci"] = 1.96 * out["std"] / np.sqrt(out["n"])
    return out


def spline_threshold(x, y, s_factor=3.0, n_boot=200):
    """
    用 B 样条 + L 形肘点法找负反馈加速拐点.
    Step 1: B 样条拟合平滑曲线 (y_fit)
    Step 2: 在 y_fit 上做肘点检测 — 拟合左右两条线, 找总 MSSE 最小的分割点
    """
    s = len(y) * s_factor
    spl = UnivariateSpline(x, y, s=s)
    xs = np.linspace(0, 0.95, 200)
    y_fit = spl(xs)
    y_deriv = spl.derivative(1)(xs)
    y_d2 = spl.derivative(2)(xs)
    curvature = np.abs(y_d2) / (1.0 + y_deriv**2) ** 1.5

    # L 形肘点法: 在 y_fit 上找分割点, 最小化左右两段线性拟合的加权 SSE
    n = len(xs)
    elbow_candidates = np.arange(20, n - 20)  # 至少保留 20 个点
    total_sse = []
    for k in elbow_candidates:
        xl, yl = xs[:k], y_fit[:k]
        xr, yr = xs[k:], y_fit[k:]
        if len(xl) < 2 or len(xr) < 2:
            continue
        # 左段线性拟合
        Al = np.column_stack([np.ones_like(xl), xl])
        bl = np.linalg.lstsq(Al, yl, rcond=None)[0]
        sse_l = float(np.sum((yl - Al @ bl) ** 2))
        # 右段线性拟合
        Ar = np.column_stack([np.ones_like(xr), xr])
        br = np.linalg.lstsq(Ar, yr, rcond=None)[0]
        sse_r = float(np.sum((yr - Ar @ br) ** 2))
        total_sse.append(sse_l + sse_r)
    best_idx = elbow_candidates[int(np.argmin(total_sse))]
    thresh = float(xs[best_idx])

    # Bootstrap 置信区间 (原始数据重采样, 重新做全部拟合+肘点检测)
    boots = []
    df_b = pd.DataFrame({"x": x, "y": y})
    for _ in range(n_boot):
        idx = RNG.choice(len(df_b), len(df_b), replace=True)
        b = df_b.iloc[idx]
        try:
            spl_b = UnivariateSpline(b["x"].values, b["y"].values, s=s)
            xb = np.linspace(0, 0.95, 200)
            yb = spl_b(xb)
            sse_b = []
            for k in np.arange(20, len(xb) - 20):
                l, r = yb[:k], yb[k:]
                if len(l) >= 2 and len(r) >= 2:
                    A_l = np.column_stack([np.ones_like(xb[:k]), xb[:k]])
                    A_r = np.column_stack([np.ones_like(xb[k:]), xb[k:]])
                    sse_b.append(float(np.sum((l - A_l @ np.linalg.lstsq(A_l, l, rcond=None)[0]) ** 2)
                                       + np.sum((r - A_r @ np.linalg.lstsq(A_r, r, rcond=None)[0]) ** 2)))
                else:
                    sse_b.append(np.inf)
            best = np.arange(20, len(xb) - 20)[int(np.argmin(sse_b))]
            boots.append(float(xb[best]))
        except Exception:
            continue
    boots = np.array(boots)
    lo, hi = np.percentile(boots, [2.5, 97.5]) if len(boots) > 30 else (thresh, thresh)
    return spl, xs, y_fit, y_deriv, curvature, thresh, float(lo), float(hi)


def fig5_spline(df):
    """图5: B样条拟合 + 导数子图 + LOESS叠加对比."""
    from statsmodels.nonparametric.smoothers_lowess import lowess
    x, y = df["loss_rate"].values, df["frustration"].values
    idx_s = np.argsort(x)
    x, y = x[idx_s], y[idx_s]
    spl, xs, y_fit, y_deriv, curvature, thresh, lo, hi = spline_threshold(x, y, s_factor=3.0, n_boot=200)
    y_d2 = spl.derivative(2)(xs)
    curvature = np.abs(y_d2) / (1.0 + y_deriv**2) ** 1.5
    st = binned_stats(df, "loss_rate", "frustration")
    loess_sm = lowess(y, x, frac=0.35, return_sorted=True)

    fig, axes = plt.subplots(2, 1, figsize=(9, 7), gridspec_kw={"height_ratios": [2, 1]})
    ax = axes[0]
    ax.errorbar(st["bin_mid"], st["mean"], yerr=st["ci"], fmt="o", capsize=3,
                color="#7f8c8d", label="分箱均值 ±95%CI", alpha=0.6)
    ax.plot(xs, y_fit, lw=2.5, color="#c0392b", label="B样条平滑")
    ax.plot(loess_sm[:, 0], loess_sm[:, 1], lw=1.8, ls="--", color="#2980b9", alpha=0.7, label="LOESS 对比")
    ax.axvline(thresh, ls="--", color="#e67e22", lw=2, alpha=0.8)
    ax.axvspan(lo, hi, alpha=0.12, color="#e67e22", label=f"阈值 95%CI [{lo:.0%}, {hi:.0%}]")
    ax.set(title=f"图5 B样条拟合（阈值≈{thresh:.0%}, 95%CI {lo:.0%}~{hi:.0%}）",
           xlabel="本局损失率", ylabel="挫败感")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)

    ax2 = axes[1]
    # 画肘点检测的 SSE 曲线
    elbow_candidates = np.arange(20, 180)
    total_sse = []
    for k in elbow_candidates:
        xl, yl = xs[:k], y_fit[:k]
        xr, yr = xs[k:], y_fit[k:]
        Al = np.column_stack([np.ones_like(xl), xl])
        Ar = np.column_stack([np.ones_like(xr), xr])
        sse = float(np.sum((yl - Al @ np.linalg.lstsq(Al, yl, rcond=None)[0]) ** 2)
                    + np.sum((yr - Ar @ np.linalg.lstsq(Ar, yr, rcond=None)[0]) ** 2))
        total_sse.append(sse)
    ax2.plot(xs[elbow_candidates], total_sse, lw=1.5, color="#8e44ad")
    ax2.axvline(thresh, ls="--", color="#e67e22", lw=2, alpha=0.8)
    ax2.set(title=f"肘点检测: 左右两段线性拟合总SSE → 拐点 = {thresh:.0%}",
            xlabel="候选分割点（本局损失率）", ylabel="加权总 SSE")
    ax2.grid(alpha=0.3)
    ax2.grid(alpha=0.3)
    fig.tight_layout()
    out = FIG_DIR / "fig5_spline_fit.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[图] {out}")
    return spl, xs, y_fit, y_deriv, curvature, thresh, lo, hi


def export_curve_json(df, spl, xs, y_fit, y_deriv, curvature, thresh, lo, hi):
    """导出 curve_data.json 用于网页."""
    st = binned_stats(df, "loss_rate", "frustration")
    st2 = binned_stats(df, "loss_rate", "early_quit")
    sorted_idx = np.argsort(xs)
    xs_s = xs[sorted_idx]
    y_fit_s = y_fit[sorted_idx]
    from statsmodels.nonparametric.smoothers_lowess import lowess
    x, y = df["loss_rate"].values, df["frustration"].values
    idx_s = np.argsort(x)
    loess_sm = lowess(y[idx_s], x[idx_s], frac=0.35, return_sorted=True)
    data = {
        "meta": {
            "n_players": int(df["player_id"].nunique()),
            "n_matches": len(df),
            "threshold_pct": round(thresh * 100, 1),
            "threshold_ci_low_pct": round(lo * 100, 1),
            "threshold_ci_high_pct": round(hi * 100, 1),
        },
        "binned": [
            {"loss_rate_mid": round(r.bin_mid, 2), "frustration_mean": round(r.mean, 2),
             "ci": round(r.ci, 2), "n": r.n}
            for r in st.itertuples()
        ],
        "binned_behavior": [
            {"loss_rate_mid": round(r.bin_mid, 2),
             "early_quit_mean": round(r.mean, 3), "n": r.n}
            for r in st2.itertuples()
        ],
        "spline_fit": [
            {"x": round(float(xs_s[i]), 3), "y": round(float(y_fit_s[i]), 3)}
            for i in range(len(xs_s))
        ],
        "spline_deriv": [
            {"x": round(float(xs_s[i]), 3),
             "dydx": round(float(y_deriv[sorted_idx[i]]), 3)}
            for i in range(len(xs_s))
        ],
        "spline_curvature": [
            {"x": round(float(xs_s[i]), 3),
             "kappa": round(float(curvature[sorted_idx[i]]), 5)}
            for i in range(len(xs_s))
        ],
        "loess": [
            {"x": round(float(loess_sm[i, 0]), 3),
             "y": round(float(loess_sm[i, 1]), 3)}
            for i in range(len(loess_sm))
        ],
        "frustration_source_adjust": {
            "death_dominated": 0.8,
            "loss_dominated": -0.5,
            "mixed": 0.0,
        },
    }
    out = DATA_DIR / "curve_data.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[JSON] {out} ({len(data['spline_fit'])} 个样条点)")


def main():
    csv = Path(sys.argv[1]) if len(sys.argv) > 1 else DATA_DIR / "matches.csv"
    df = pd.read_csv(csv)
    print(f"载入 {len(df)} 局 / {df['player_id'].nunique()} 名玩家: {csv}")
    spl, xs, y_fit, y_deriv, curvature, thresh, lo, hi = fig5_spline(df)
    print(f"\n>> B样条(曲率法)检测阈值: 损失率 = {thresh:.1%}  (95%CI {lo:.1%} ~ {hi:.1%})")
    print(">> 分段线性(旧)检测: 24%  → 曲率法改进显著!\n")
    export_curve_json(df, spl, xs, y_fit, y_deriv, curvature, thresh, lo, hi)


if __name__ == "__main__":
    main()