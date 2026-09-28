# -*- coding: utf-8 -*-
"""
搜打撤研究 —— 改进拟合（B样条 + 导数拐点检测）
=================================================
相比分段线性, 用平滑样条拟合真实曲线, 通过一阶导数最大值
精确定位"负反馈加速最剧烈"的阈值拐点.

主要 X 轴指标：total_loss_ratio（总损失率 = 丢失总价值/携带价值, 可>100%）
旧版 loss_rate（损失率 0~100%）保留在 extended 段中作为参考.

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


def spline_threshold(x, y, s_factor=0.5, n_boot=200, x_max=3.0, elbow_max=None):
    """
    用 B 样条 + 最大二阶导法找负反馈加速拐点.
    Step 1: B 样条拟合平滑曲线 (y_fit)
    Step 2: 在平滑曲线上找二阶导最大的点 = 加速度开始最强点 = 拐点阈值
    
    对于 S 形曲线（浅→陡→饱和），最大二阶导对应"加速度开始"，
    比 L 形法（找浅→陡→饱和的分段连接点）更准确。
    
    Parameters
    ----------
    x, y : 原始数据点
    s_factor : 平滑因子
    n_boot : bootstrap 次数
    x_max : 样条曲线的最大 x 值（用于可视化外推）
    elbow_max : 检测的最大 x 值限制，防止在外推区/饱和区找拐点
    """
    s = len(y) * s_factor
    spl = UnivariateSpline(x, y, s=s)
    xs = np.linspace(0, x_max, max(200, int(400 * x_max / 3.0)))
    y_fit = spl(xs)
    y_deriv = spl.derivative(1)(xs)
    y_d2 = spl.derivative(2)(xs)
    curvature = np.abs(y_d2) / (1.0 + y_deriv**2) ** 1.5

    # 将检测限制在动态范围内，排除饱和尾区
    if elbow_max is None:
        elbow_max = max(x)
    n_data = int(np.searchsorted(xs, elbow_max))
    
    # 最大二阶导法：在变化范围内找二阶导峰值
    n_min = max(10, n_data // 10)
    search = slice(n_min, n_data - n_min)
    if y_d2[search].max() > 0:
        best_idx = n_min + int(np.argmax(y_d2[search]))
    else:
        # 保底：用 L 形法
        cand = np.arange(n_min, n_data - n_min)
        if len(cand) < 2:
            cand = np.arange(20, n_data - 20)
        if len(cand) < 2:
            cand = np.arange(1, n_data - 1)
        sse_vals = []
        for k in cand:
            xl, yl = xs[:k], y_fit[:k]
            xr, yr = xs[k:], y_fit[k:]
            if len(xl) < 2 or len(xr) < 2:
                continue
            Al = np.column_stack([np.ones_like(xl), xl])
            Ar = np.column_stack([np.ones_like(xr), xr])
            bl = np.linalg.lstsq(Al, yl, rcond=None)[0]
            br = np.linalg.lstsq(Ar, yr, rcond=None)[0]
            sse_vals.append(float(np.sum((yl - Al @ bl) ** 2)) +
                            float(np.sum((yr - Ar @ br) ** 2)))
        if sse_vals:
            best_idx = cand[int(np.argmin(sse_vals))]
        else:
            best_idx = n_data // 2
    thresh = float(xs[best_idx])

    # Bootstrap 置信区间 (原始数据重采样)
    boots = []
    df_b = pd.DataFrame({"x": x, "y": y})
    for _ in range(n_boot):
        idx = RNG.choice(len(df_b), len(df_b), replace=True)
        b = df_b.iloc[idx]
        try:
            spl_b = UnivariateSpline(b["x"].values, b["y"].values, s=s)
            xb = np.linspace(0, x_max, max(200, int(400 * x_max / 3.0)))
            yb = spl_b(xb)
            yb_d2 = spl_b.derivative(2)(xb)
            n_bdata = int(np.searchsorted(xb, elbow_max))
            n_bmin = max(10, n_bdata // 10)
            rgn = slice(n_bmin, n_bdata - n_bmin)
            if yb_d2[rgn].max() > 0:
                b_idx = n_bmin + int(np.argmax(yb_d2[rgn]))
                boots.append(float(xb[b_idx]))
        except Exception:
            continue
    if len(boots) >= 20:
        lo, hi = float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))
    else:
        lo = hi = thresh
    return spl, xs, y_fit, y_deriv, curvature, thresh, lo, hi


def fig5_spline(df, xcol="total_loss_ratio"):
    """
    绘制 B 样条拟合结果图（两个子图：上=拟合曲线，下=导数）
    自动确定 elbow_max 为数据最大值，防止在外推区误检拐点.
    """
    # 按 x 排序（UnivariateSpline 要求 x 严格递增）
    df_sorted = df.sort_values(xcol)
    x = df_sorted[xcol].values
    y = df_sorted["frustration"].values

    # 自适应 x_max：基于动态范围，但限制在 8.0 以内保证分辨率
    # 对于窄范围数据（如 loss_rate 0~1），避免过度外推
    data_max = float(x.max())
    x_max = min(max(min(3.0, data_max * 2.0), data_max * 1.3), 8.0)
    # 肘点搜索仅限有意义的变化区域：frustration < 9.5 的最大 x
    non_sat = x[y < 9.5]
    elbow_max = float(non_sat.max()) if len(non_sat) > 100 else min(data_max, 2.5)

    spl, xs, y_fit, y_deriv, curvature, thresh, lo, hi = spline_threshold(
        x, y, s_factor=5.0, n_boot=200, x_max=x_max, elbow_max=elbow_max
    )

    # 绘图
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True,
                                    gridspec_kw={"height_ratios": [3, 1]})
    # 上子图：散点 + 样条曲线
    ax1.scatter(x, y + RNG.normal(0, 0.02, len(y)), s=3, alpha=0.15, color="#bdc3c7",
                label="原始数据 (jittered)", rasterized=True)
    # 分箱统计点
    st = binned_stats(df, xcol, "frustration")
    ax1.errorbar(st["bin_mid"], st["mean"], yerr=st["ci"],
                 fmt="o", color="#7f8c8d", ecolor="#95a5a6", capsize=3, label="分箱 ±95%CI")
    # 外推区标记：数据范围内实线，外推区虚线
    n_data = int(np.searchsorted(xs, elbow_max))
    ax1.plot(xs[:n_data], y_fit[:n_data], color="#c0392b", lw=2.5, label="B样条拟合")
    if n_data < len(xs):
        ax1.plot(xs[n_data - 1:], y_fit[n_data - 1:], color="#c0392b", lw=2, ls="--", alpha=0.6,
                 label="外推段")
    # 阈值线
    ax1.axvline(thresh, color="#e67e22", lw=2, ls="--", label=f"肘点: {thresh:.0%}")
    ax1.axvspan(lo, hi, color="#e67e22", alpha=0.1, label=f"95%CI: {lo:.1%}~{hi:.1%}")
    ax1.set_ylabel("挫败感")
    ax1.set_ylim(0.5, 10.5)
    ax1.legend(fontsize=8, loc="upper left")
    ax1.grid(True, alpha=0.3)
    # 下子图：导数 + 曲率
    ax2.plot(xs, y_deriv, color="#2980b9", lw=1.5, label="一阶导")
    ax2.axvline(thresh, color="#e67e22", lw=2, ls="--")
    ax2.axvline(thresh, color="#e67e22", lw=2, ls="--")
    ax2.set_xlabel(xcol)
    ax2.set_ylabel("变化率")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)
    plt.tight_layout()
    png = FIG_DIR / f"fig5_spline_fit_{xcol}.png"
    fig.savefig(png, dpi=150)
    plt.close(fig)
    print(f"[FIG] {png}")
    return spl, xs, y_fit, y_deriv, curvature, thresh, lo, hi


def export_curve_json(df, spl_tlr, xs_tlr, y_fit_tlr, y_deriv_tlr, curvature_tlr,
                      thresh_tlr, lo_tlr, hi_tlr,
                      spl_lr, xs_lr, y_fit_lr, y_deriv_lr, curvature_lr,
                      thresh_lr, lo_lr, hi_lr):
    """
    导出 JSON（total_loss_ratio 为主，loss_rate 为 extended 参考）
    """
    # 主：total_loss_ratio
    st_tlr = binned_stats(df, "total_loss_ratio", "frustration", width=0.1)
    st2_tlr = binned_stats(df, "total_loss_ratio", "early_quit")
    # 副：loss_rate
    st_lr = binned_stats(df, "loss_rate", "frustration", width=0.1)
    st2_lr = binned_stats(df, "loss_rate", "early_quit")

    # LOESS 平滑（用于参考）
    from scipy.ndimage import uniform_filter1d
    idx = np.argsort(xs_tlr)
    loess_sm = np.column_stack([xs_tlr[idx],
                                uniform_filter1d(y_fit_tlr[idx], size=5)])

    data = {
        "meta": {
            "n_players": int(df["player_id"].nunique()),
            "n_matches": len(df),
            "threshold_pct": round(thresh_tlr * 100, 1),
            "threshold_ci_low_pct": round(lo_tlr * 100, 1),
            "threshold_ci_high_pct": round(hi_tlr * 100, 1),
        },
        # 主数据：total_loss_ratio
        "binned": [
            {"loss_rate_mid": round(r.bin_mid, 2), "frustration_mean": round(r.mean, 2),
             "ci": round(r.ci, 2), "n": r.n}
            for r in st_tlr.itertuples()
        ],
        "binned_behavior": [
            {"loss_rate_mid": round(r.bin_mid, 2),
             "early_quit_mean": round(r.mean, 3), "n": r.n}
            for r in st2_tlr.itertuples()
        ],
        "spline_fit": [
            {"x": round(float(xs_tlr[i]), 4), "y": round(float(y_fit_tlr[i]), 3)}
            for i in range(len(xs_tlr))
        ],
        "spline_deriv": [
            {"x": round(float(xs_tlr[i]), 4),
             "dydx": round(float(y_deriv_tlr[i]), 4)}
            for i in range(len(xs_tlr))
        ],
        "spline_curvature": [
            {"x": round(float(xs_tlr[i]), 4),
             "kappa": round(float(curvature_tlr[i]), 6)}
            for i in range(len(xs_tlr))
        ],
        # 副数据：loss_rate（旧版，保留参考）
        "extended": {
            "meta": {
                "threshold_pct": round(thresh_lr * 100, 1),
                "threshold_ci_low_pct": round(lo_lr * 100, 1),
                "threshold_ci_high_pct": round(hi_lr * 100, 1),
            },
            "binned": [
                {"loss_rate_mid": round(r.bin_mid, 4), "frustration_mean": round(r.mean, 2),
                 "ci": round(r.ci, 2), "n": r.n}
                for r in st_lr.itertuples()
            ],
            "spline_fit": [
                {"x": round(float(xs_lr[i]), 4), "y": round(float(y_fit_lr[i]), 3)}
                for i in range(len(xs_lr))
            ],
        },
        "loess": [
            {"x": round(float(loess_sm[i, 0]), 4),
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
    print(f"[JSON] {out} ({len(data['spline_fit'])} 个样条点, extended {len(data['extended']['spline_fit'])} 个)")


def main():
    csv = Path(sys.argv[1]) if len(sys.argv) > 1 else DATA_DIR / "matches.csv"
    df = pd.read_csv(csv)
    print(f"载入 {len(df)} 局 / {df['player_id'].nunique()} 名玩家: {csv}")
    print(f"  total_loss_ratio 范围: {df['total_loss_ratio'].min():.4f} ~ {df['total_loss_ratio'].max():.4f}")
    print(f"  loss_rate 范围: {df['loss_rate'].min():.4f} ~ {df['loss_rate'].max():.4f}")

    # 主拟合：total_loss_ratio
    spl_tlr, xs_tlr, y_fit_tlr, y_deriv_tlr, curvature_tlr, thresh_tlr, lo_tlr, hi_tlr = \
        fig5_spline(df, xcol="total_loss_ratio")
    print(f"\n>> B样条(总损失率) 检测阈值: {thresh_tlr:.1%}  (95%CI {lo_tlr:.1%} ~ {hi_tlr:.1%})")

    # 副拟合：loss_rate（旧版，保留参考）
    spl_lr, xs_lr, y_fit_lr, y_deriv_lr, curvature_lr, thresh_lr, lo_lr, hi_lr = \
        fig5_spline(df, xcol="loss_rate")
    print(f">> B样条(损失率, 副) 检测阈值: {thresh_lr:.1%}  (95%CI {lo_lr:.1%} ~ {hi_lr:.1%})")

    export_curve_json(df,
                      spl_tlr, xs_tlr, y_fit_tlr, y_deriv_tlr, curvature_tlr,
                      thresh_tlr, lo_tlr, hi_tlr,
                      spl_lr, xs_lr, y_fit_lr, y_deriv_lr, curvature_lr,
                      thresh_lr, lo_lr, hi_lr)


if __name__ == "__main__":
    main()