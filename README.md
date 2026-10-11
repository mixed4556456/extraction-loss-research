# 搜打撤：单局损失价值 → 玩家负反馈 曲线研究（模拟数据演示版）

## 研究问题

一局游戏中丢失物品总价值（主口径：**总损失率 = 丢失总价值 / 携带价值**，死亡时含被丢掉的战利品、可 >100%；副口径：损失率 0~100%）如何影响玩家负反馈？
- 主观层：局后挫败感评分（1~10）
- 行为层：局后是否提前结束会话（秒退 / 不打下一局）
- 曲线是平滑上升，还是存在**加速点**？单局损失越过「最大加速点」后负反馈是否陡增？

## 目录结构

```
extraction_loss_research/
├── index.html                  # 交互式网页报告（Pages 站点入口；双击即可离线打开）
├── index.inline.html           # 同一报告的单文件自包含版（Plotly 内嵌，~4.5MB，便于直接转发）
├── src/                        # 分析流水线（脚本用「上一级目录」当项目根，任意 CWD 都可运行）
│   ├── simulate_data.py        #   第1步：模拟对局数据 → data/matches.csv
│   ├── analyze.py              #   第2步：分箱/LOESS/分段回归/分层/混合效应 → figs/fig1~4 + summary_report.md
│   ├── fit_improved.py         #   第3步：B样条 + 三次函数最大加速点 → data/curve_data.json + figs/fig5_*
│   └── gen_webpage.py          #   第4步：生成 index.html（--inline 输出自包含单文件）
├── data/                       # matches.csv（数据）、curve_data.json（网页数据源）
├── figs/                       # 报告用图
├── docs/                       # methodology.md（方法论迭代）、research_log.md（研究日志,暂缺失）
├── survey/                     # 问卷模板、场景生成脚本与 CSV
├── assets/plotly.min.js        # 离线 Plotly（4.35MB），网页优先加载它
├── summary_report.md           # analyze.py 生成的分析报告
├── questionnaire_design.md     # 问卷设计说明书
└── .github/workflows/pages.yml # GitHub Pages 自动部署
```

在项目根目录执行（脚本可任意 CWD 调用）：

```powershell
python src/simulate_data.py            # 第1步：生成模拟数据
python src/analyze.py                  # 第2步：4 张图 + summary_report.md
python src/analyze.py 你的数据.csv      # 换真实数据
python src/fit_improved.py             # 第3步：最大加速点 → data/curve_data.json + figs/fig5_*
python src/gen_webpage.py              # 第4步：生成 index.html（--inline 生成自包含单文件）
```


## 使用方法

```powershell
python src/simulate_data.py   # 第1步：生成 500 名玩家、14094 局模拟数据 data/matches.csv
python src/analyze.py         # 第2步：输出 4 张图 (figs/) + summary_report.md
python src/analyze.py 你的数据.csv   # 拿到真实数据后直接替换
python src/fit_improved.py     # v1.4 主口径：三次函数最大加速点（B样条作参考线）→ data/curve_data.json + figs/fig5_*
python src/gen_webpage.py      # 生成交互式网页报告 index.html（双击即可离线打开）
```

依赖：Python 3.10+，`numpy pandas matplotlib scipy statsmodels`

## 流水线输出

| 产物 | 内容 | 方法 |
|---|---|---|
| fig1_binned_curve.png | 分箱均值 ±95%CI（主观 + 行为双面板） | 分箱统计 |
| fig2_loess.png | 平滑曲线 | LOESS 局部加权回归 |
| fig3_breakpoint.png | 自动找拐点 + Bootstrap 95%CI | 分段回归 |
| fig4_stratified.png | 贫富分层曲线（调节效应） | 分组 LOESS |
| summary_report.md | 数值结论 + 分箱表 + 结论模板 | 混合效应模型等 |

## 内置的"真实规律"（用于检验分析方法是否可信）

生成数据用的上帝视角公式（分析脚本事先不知道）：

```
挫败感 = 1.2 + 2.5×损失率 + 6.0×max(0, 损失率−0.70)²
        + 1.0×死亡 + 0.6×死于玩家 + 个体敏感度 + 噪声（截断 1~10）
```

→ **真实阈值：总损失率 70%**（生成公式里二次项的起点）。注意：数据驱动方法定位的是「最大加速点」（加速度最强处：三次 181.7% / B样条 142.7%），一般晚于该起点；
拿到真实数据后可以直接信任同样的分析流程。

## 换成真实数据

CSV 至少包含以下列（多可以，少不行）：

| 列名 | 含义 |
|---|---|
| player_id | 玩家唯一 ID（混合效应模型分组用） |
| loss_rate | 本局损失率；若只有绝对损失 `lost_value`，可改 analyze.py 的 xcol 并重新分箱 |
| frustration | 局后挫败感评分 1~10（问卷）；或用留存/局数等行为指标替换 |
| early_quit | 局后提前结束会话 0/1（遥测可得） |
| died / died_to_player | 控制变量：是否死亡 / 是否死于玩家 |
| wealth_group | 分层用（也可换成 skill 技术分层） |

## 问卷建议（收集 frustration 用）

完整设计见 **`questionnaire_design.md`**（两条路线的取舍、逐题题面、抽样量、质控剔除规则、分析路线图、避雷清单）。

- **路线 A｜单局回溯日志**：单局结束后 30 秒内填写，只问 2 题，避免流失
  1. "这一局的损失让你有多沮丧？" 1（毫无感觉）~ 10（非常愤怒）
  2. "你现在还想继续玩吗？" 1~10（可换算成行为意愿交叉验证）
     模板：`python survey/survey_template.py` → `survey/survey_template.csv`
- **路线 B｜场景法问卷**（推荐：一次收齐、可随机化、直接出曲线）
  22 个固定情境（损失率 5%~100%，其中 50%~100% 加密，携带价值固定 5 万），每人评"挫败感 + 继续意愿"
  生成：`python survey/survey_vignette.py [人数]` → `survey/survey_vignette_scenarios.csv` + `survey/survey_vignette_responses.csv`

两份模板的列名都与 `data/matches.csv` 对齐：问卷数据收完直接 `python src/fit_improved.py 你的数据.csv` 即可，无需改分析代码。

## 网页版报告（index.html）

`python src/gen_webpage.py` 生成单文件交互报告：左侧曲线（B样条 + 三次函数 + 分箱 ±95%CI），右侧输入本局数据即时定位。

- **默认与推荐口径：总损失率（含战利品）**，判读点为三次函数「最大加速点」= 181.7%（95%CI 156.6%~218.8%；超出观测上限 166.2%，属外推，页面已标注）
- 可切换「损失率（仅装备）」口径：最大加速点 50.9%（95%CI 50.1%~52.0%，落在观测范围内）
- Plotly 加载顺序：本地 `assets/plotly.min.js` → `jsd.onmicrosoft.cn` → jsdelivr → unpkg，断网也能正常渲染
- 需要单个可转发的文件：`python src/gen_webpage.py --inline`（把 Plotly 内嵌，产出约 4.5MB 自包含 HTML；仓库内已生成 `index.inline.html` 可直接转发）
- 已配 GitHub Pages（`.github/workflows/pages.yml`）：push 到 `main` 自动部署，务必一并提交 `assets/plotly.min.js`
- 页面「检测结果」区同时列出两种口径的数值与 95%CI，避免只看一条线

## 注意事项

- 挫败感可能来自"死亡"本身而非"损失金额" → 分析时务必控制 `died`，并保留"死了但带白装"的样本做对照

- 同一玩家多局数据不独立 → 用混合效应模型（已内置），或按玩家聚合后再分析

- 主观评分与行为指标交叉验证，结论才站得住

  
