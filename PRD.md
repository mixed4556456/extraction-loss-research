# PRD：搜打撤「单局损失价值 → 玩家负反馈」曲线研究（v1.5 及后续迭代）

| 项 | 内容 |
|---|---|
| 文档版本 | v1.5（已评审；承接 v1.4 交付物） |
| 日期 | 2026-10-13 |
| 状态 | 已评审 — 决策 D-01~D-04 已确认（见 §11）；P0 进入开发 |
| 仓库根 | `C:\Users\LENOVO\Desktop\extraction_loss_research` |
| 上游交付 | git `a0cbbaf feat(v1.4):网页视图修复 + 项目结构整理` |
| 相关文档 | `README.md`（使用说明）、`docs/methodology.md`（方法论）、`questionnaire_design.md`（问卷设计）、`agent.md`（AI/自动化开发指南）、`docs/research_log.md`（待填充） |

---

## 1. 背景与问题陈述

研究美国式搜打撤（Extraction Shooter，如《暗区突围》《逃离塔科夫》）玩家的负反馈机制：
**一局游戏中丢失的物品总价值，如何影响玩家局后的主观挫败感与行为层退出决策？**

- 自变量主口径：`total_loss_ratio` = 丢失总价值 / 携带价值（死亡时含被丢弃的战利品，可 > 100%，本数据集最高 600%+）
- 自变量副口径：`loss_rate` = 仅装备损失率（0~100%，兼容旧版分析）
- 因变量主观层：`frustration`（局后挫败感 1~10）
- 因变量行为层：`early_quit`（局后秒退 / 不打下一局，0/1）、`next_gap_min`（下一局间隔）

核心待答问题：曲线是平滑上升，还是存在**加速点**？越过「最大加速点」后负反馈是否陡增？

**当前项目状态**：在拿到真实数据之前，用一条已知的「上帝视角」真值公式生成模拟数据（500 名玩家 / 14,094 局），
跑通并验证整条分析流水线，同时把结论做成可离线打开的交互式网页报告。真实数据（游戏遥测 + 问卷）**尚未接入**。

---

## 2. 现状盘点（v1.4 已交付）

### 2.1 已交付能力

| 能力 | 入口 | 产物 |
|---|---|---|
| 模拟对局数据 | `python src/simulate_data.py` | `data/matches.csv`（14,094 行 / 16 列 / 1.19 MB） |
| 基础分析（分箱 / LOESS / 分段回归 / 分层 / 混合效应） | `python src/analyze.py [csv]` | `figs/fig1~fig4*.png`、`summary_report.md` |
| 阈值检测（B 样条加速度 + 三次函数拐点 / 外推标记） | `python src/fit_improved.py [csv]` | `data/curve_data.json`（341 KB）、`figs/fig5_spline_fit_{total_loss_ratio,loss_rate}.png` |
| 交互式网页报告 | `python src/gen_webpage.py [--inline]` | `index.html`（194 KB）；`--inline` 内嵌 Plotly（实测 4.54 MB）|
| 问卷材料（路线 A 单局回溯 / 路线 B 场景法） | `python survey/survey_template.py`、`python survey/survey_vignette.py [N]` | `survey/*.csv`（列名与 `matches.csv` 对齐） |
| 自动部署 | push `main` | GitHub Pages（`.github/workflows/pages.yml`，根目录整包上传） |

### 2.2 关键结论（模拟数据，主口径 total_loss_ratio）

| 口径 / 方法 | 「最大加速点」 | 95% CI | 是否落在观测范围 | 备注 |
|---|---|---|---|---|
| **真值（上帝视角）** | **70%** | — | — | 生成公式二次项起点，分析脚本事先不知道 |
| 三次函数拐点（主口径） | 181.7% | 156.6%~218.8% | **否（外推）** | 截断 y≥9.99；`cubic_truncated_x_max=1.6622`；`a<0` |
| B 样条一阶导峰值（参考） | 142.7% | 142.7%~142.7%（退化） | 否 | CI 未真正 bootstrap，等同点估计 |
| 分段线性（仅 loss_rate，对照） | ~9.8% | — | 是 | 方法对照，见 `summary_report.md` |
| 三次函数（仅 loss_rate，副口径） | 50.9% | 50.1%~52.0% | **是（范围内）** | `cubic_inflection_in_range=true` |

> 结论表述必须严格区分：**「真值 70%」是生成公式的二次项起点**；数据驱动方法定位的是**「最大加速点」（二阶导峰值）**，一般晚于该起点。
> 两者不可互相替代，任何对外材料都要写清是哪一个。

### 2.3 已知缺口与技术债（本 PRD 的需求来源）

| ID | 缺口 | 证据 |
|---|---|---|
| G-01 | `gen_webpage.py --inline` **写入的仍是 `index.html`**（覆盖 CDN 版主文件），并不产出 `index.inline.html` | `src/gen_webpage.py:122` 恒写 `ROOT/"index.html"`；README:15 却宣称仓库内已有 `index.inline.html` |
| G-02 | 口径不一致：`analyze.py` **全文未使用 `total_loss_ratio`**，fig1~fig4 / 混合效应 / 分箱表仍用 `loss_rate`，与 README 宣称的「主口径」冲突 | `Select-String total_loss_ratio src\*.py` 仅命中 `fit_improved.py`、`simulate_data.py` |
| G-03 | B 样条阈值 CI 退化为点值（142.7~142.7），无不确定性含义 | `data/curve_data.json: meta.threshold_ci_low_pct == high_pct == 142.7` |
| G-04 | 主口径三次拐点 `a<0` 且超出观测上限，属**外推**；「拐点」在 `a<0` 时并非"最大加速点"语义，仅靠文字标注，无代码级校验 | `meta.cubic_a_sign="negative"`、`cubic_inflection_in_range=false` |
| G-05 | 无数据校验：换真实数据/问卷 CSV 时列缺失、取值越界、`died` 与 `carry/lost` 矛盾均静默出错 | 无 `validate` 相关代码 |
| G-06 | 无自动化测试；`pytest` 未安装；无 `requirements.txt`（依赖仅写在 README 一行） | `import pytest` 失败；`git ls-files` 无 requirements.txt |
| G-07 | 四个脚本需手动按序执行，缺少一键编排与产物一致性断言（易出现「图新、JSON 旧、网页更旧」）| 无 `run_all`/`Makefile` |
| G-08 | `index.inline.html` 已被 `.gitignore` 忽略，但**仍在 git 索引中**（ignore 对已跟踪文件无效），4.5 MB 大文件长期入库 | `git ls-files` 含 `index.inline.html`；`.gitignore:27` |
| G-09 | 陈旧产物/文件残留与命名漂移：`figs/fig5_spline_fit.png`、`figs/fig5_spline_fit_ext.png`、`survey/summary_report_beta.md` 已在暂存区删除但未提交；`docs/research_log.md` 为 0 字节 | `git status --short`（D 状态三项）|
| G-10 | 行为层已生成 `early_quit` / `next_gap_min`，但只有分箱比例图，未做正式建模（生存分析 / logistic） | `analyze.py:46` 仅分箱 |
| G-11 | 天花板效应（frustration 截断 1~10）仅用「截断 y≥9.99」粗暴处理，无 Tobit / 有序 logit 对照 | `fit_improved.py: cubic_fit_inflection(truncate_at=9.99)` |

---

## 3. 目标与非目标

### 3.1 目标（本迭代要达成）

1. **可换数据**：把「模拟数据演示」升级为「真实数据可跑通」——一条命令接入游戏遥测 CSV 与问卷 CSV，且坏数据能被明确拒绝而不是静默出错。
2. **口径唯一**：全仓库（脚本 / JSON / 报告 / 网页 / 文档）只有一个主口径（`total_loss_ratio`）与一套阈值术语；外推必须被机器标注，不依赖人记得。
3. **结论可复现**：固定随机种子下，任一次完整重跑，`curve_data.json` 数值可逐位复现；关键数值由测试守住。
4. **产物同源同时**：一次编排生成全部产物，且断言「CSV 行数 = JSON 的 `meta.n_matches` = 报告里写的样本量」。
5. **统计严谨性补齐**：不确定性（CI）与敏感性（分箱宽度、平滑参数、截断阈值、剔除以死亡为主样本）可查。

### 3.2 非目标（本迭代明确不做）

- 不做在线多人在线问卷平台 / 后端服务；问卷仍以 CSV 离线回收（路线 B 已够用）。
- 不引入深度学习或复杂 ML 拟合（保持可解释的参数化曲线）。
- 不重构 `index.html` 的视觉设计体系（现有单文件 + Plotly 方案保留）。
- 不做真实第三方遥测 SDK 对接（只约定 CSV schema）。
- 不改动「上帝视角真值公式」以迎合拟合结果——真值公式是校验基准，只能改 `docs/methodology.md` 记录，不能为了好看而调。

---

## 4. 用户与使用场景

| 角色 | 场景 | 诉求 |
|---|---|---|
| 游戏策划 / 数值策划 | 问「损失到多少玩家会崩」，要一个可引用的阈值与图 | 阈值 + CI + 是否外推一目了然；网页可现场输入「玩家带 5 万、丢了 4 万」 |
| 数据分析师 | 拿到遥测导出 CSV 后替换模拟数据 | 列名契约、校验器、一条命令重跑全链 |
| 行为研究员 | 需要方法论可辩护（分层、天花板、重复测量） | 方法论文档 + 敏感性分析 + 混合效应/生存分析结果 |
| 问卷执行人 | 用场景法问卷收 22 情境评分 | 模板列名与 `matches.csv` 一致，收完直接跑分析 |
| 后续 AI Agent / 自动化开发 | 在仓库内继续迭代 | 见 `agent.md`：产物归属、验证命令、硬规则 |

---

## 5. 需求清单

优先级定义：**P0 = 阻塞真实数据接入或造成结论错误**；**P1 = 显著提升结论可信度**；**P2 = 工程化/体验完善**。

### 5.1 P0（本迭代必须完成）

#### R-01｜修复 `--inline` 产物路径与体积治理（对应 G-01、G-08）

- 需求：`gen_webpage.py` 支持 `--out <path>`（默认 `index.html`）；`--inline` 默认输出到 `index.inline.html`，**不再覆盖 CDN 版 `index.html`**。
- 体积治理（决策 **D-01**，已批准）：`index.inline.html` **移出版本跟踪**（`git rm --cached`，文件保留在本地磁盘），改由本地/发布流程生成；`.gitignore` 保留该条目；README 需写明生成命令。
- 验收标准：
  1. `python src/gen_webpage.py` → `index.html` < 400 KB；`python src/gen_webpage.py --inline` → `index.inline.html` > 4 MB，且 `index.html` 的 mtime/大小**不变**。
  2. `git status --short` 在 `--inline` 之后不出现 `M index.html`。
  3. `git ls-files | Select-String index.inline` 无输出（即 D-01 已执行）。

#### R-02｜统一主口径为 `total_loss_ratio`（对应 G-02）

- 需求：`analyze.py` 增加 `XCOL` 常量（默认 `total_loss_ratio`）与 `--xcol` 覆盖参数；fig1（分箱双面板）、fig2（LOESS）、fig3（分段回归）、fig4（分层）、混合效应公式、`summary_report.md` 分箱表全部改用该 x 轴；`loss_rate` 版本作为 `--xcol loss_rate` 的对照路径保留。
- 验收标准：
  1. `python src/analyze.py` 输出的 `summary_report.md` 中，分箱表区间中点上限 ≥ 2.5（证明用的是可 >100% 的主口径），且「方法对照」段落仍保留 `loss_rate` 分段结果。
  2. `python src/analyze.py --xcol loss_rate` 可跑通并产出同样的 4 张图（对照模式）。
  3. `Select-String -Path src\analyze.py -Pattern 'total_loss_ratio'` 至少命中 fig1~fig4 与混合模型处。

#### R-03｜数据校验器 `src/validate_data.py`（对应 G-05）

- 需求：新增独立校验模块，既可作为 CLI（`python src/validate_data.py 你的数据.csv`）也可被其它脚本 import（`from validate_data import validate`）。
- 校验项（每条给出明确报错文案与退出码）：
  1. 必需列存在：`player_id, loss_rate, total_loss_ratio, frustration, early_quit, died, died_to_player`（`wealth_group` 可选，缺失则分层图跳过并提示）。
  2. 取值域：`frustration ∈ [1,10]`；`early_quit ∈ {0,1}`；`died ∈ {0,1}`；`loss_rate ∈ [0,1]`；`total_loss_ratio ≥ 0`。
  3. 一致性：`carry_value > 0` 时 `lost_value / carry_value ≈ total_loss_ratio`（容差 1e-3）；`died=1` 时不应出现 `lost_value == 0`。
  4. 结构：`player_id` 唯一值数 ≥ 2（混合效应需要）；每名玩家局数 `n` 报告出来；`n<10` 的玩家只提示不报错。
  5. 缺失值：上述必需列 NaN 计数与占比打印；占比 > 5% 时以非零退出码失败。
- 验收标准：对 `data/matches.csv` 校验通过（退出码 0）；人为删掉 `frustration` 列、把 `frustration` 改成 15、把 `lost_value` 乘 2 三种注入错误都能被拦下（退出码非 0 且文案指出列名/行号范围）。
- 集成：`analyze.py`、`fit_improved.py` 在载入 CSV 后调用 `validate`，失败即中止。

#### R-04｜一键编排 + 产物一致性断言（对应 G-07）

- 需求：新增 `src/run_all.py`（或 `make.ps1`）：依次执行 生成数据（可选 `--keep-data` 跳过）→ `validate` → `analyze` → `fit_improved` → `gen_webpage`（+ `--inline`），任一步失败即停止并打印失败步骤。
- 一致性断言（编排末尾执行，失败则非零退出）：
  - `curve_data.json: meta.n_matches == len(matches.csv) - 1（去除注释行）`；`meta.n_players == player_id.nunique()`。
  - `summary_report.md` 内出现的样本局数与上者一致。
  - `index.html` 内含 `"n_matches": <同一数值>`（生成时已内嵌 JSON）。
- 验收标准：`python src/run_all.py` 全程退出码 0；故意在 `fit_improved` 之后手动改一行 `summary_report.md` 再跑 `--verify-only` 能报错。

#### R-05｜测试与依赖锁定（对应 G-06）

- 需求：新增 `tests/`（pytest）与 `requirements.txt`（锁定 `numpy pandas scipy statsmodels matplotlib` + `pytest`，版本以当前实测环境为基准：Python 3.13.12 / numpy 2.5.3 / pandas 3.0.6 / scipy 1.18.1 / statsmodels 0.15.0 / matplotlib 3.11.2）。
- 必测用例：
  1. `test_validate_data.py`：R-03 的四种注入错误。
  2. `test_truth_recovery.py`：用 `simulate_data` 的真值函数在固定 seed 下生成小样本（如 200 玩家 × 20 局），断言「三次拐点 / B 样条加速度点 **均位于真值 70% 的右侧**」这一方向性结论（不硬编码 181.7%，避免模拟种子变动导致脆测）；同时断言 `loss_rate` 副口径拐点落在观测范围内。
  3. `test_curve_contract.py`：`curve_data.json` 的键集合等于本文档 §6.2 的快照（防前端契约被破坏）；`meta` 中 CI 低 ≤ 点估计 ≤ CI 高（含退化情形，见 R-06）。
  4. `test_webpage_smoke.py`：`gen_webpage.py --out tmp.html` 产物包含 `Plotly.newPlot`、`frustration_source_adjust`、且不含未替换的 `{{`/`}}` 模板残留。
- 验收标准：`python -m pytest -q` 全绿；无网络环境下可运行。

#### R-06｜不确定性表述修复（对应 G-03、G-04）

- 需求：
  1. B 样条阈值必须给出**真的** bootstrap CI（对样条阈值做重抽样），或当无法给出时在 JSON 与网页中显式标注 `threshold_ci_degenerate: true` 且网页图例写作「点估计（无 CI）」——**不允许出现「CI = 点值」却仍叫 95% CI**。
  2. 三次拐点增加语义守卫：计算 `cubic_a_sign`；当 `a ≤ 0` 或 `cubic_inflection_in_range=false` 时，在 CLI 输出、`summary_report.md`、网页图例三处统一附「**外推 / 非加速点语义**」标记（网页现有 `(三次拐点·外推)` 文案保留并推广到报告）。
- 验收标准：`python src/fit_improved.py` 的终端输出包含「外推」字样（当前主口径情形下）；`data/curve_data.json` 新增上述两个布尔/字符串字段且被网页读取；`summary_report.md` 在「主口径」段落出现「外推」或「观测范围内」二者之一。

### 5.2 P1（紧随 P0，提升结论可信度）

#### R-07｜天花板效应正式处理（对应 G-11）

- 需求：对 `frustration` 的 1~10 截断，除现有「截断 y≥9.99」外，增加两条对照：
  (a) **Tobit 回归**（两侧截断，`statsmodels` 支持）估计 `total_loss_ratio` 系数；
  (b) 把 `frustration` 分为有序等级（如 1-3 / 4-6 / 7-9 / 10）跑**有序 logit**（`OrderedModel`），报告 OR 与阈值方向。
- 输出：`summary_report.md` 新增「天花板效应敏感性」小节，含三种处理下阈值/系数方向是否一致。
- 验收：三条路径的 `total_loss_ratio` 效应方向一致（均为正），且报告列出三者数值。

#### R-08｜行为层因变量正式建模（对应 G-10）

- 需求：
  1. `early_quit`：logistic 回归（`frustration` 或 `total_loss_ratio` + 控制变量 `died/died_to_player`），输出 OR 与 95%CI 曲线（随损失率的预测概率）。
  2. `next_gap_min`：生存/间隔分析，至少给 Kaplan-Meier（按损失率四分位分层）+ Cox 或对数正态 AFT 的损失率系数。
  3. 与主观层交叉验证：主观阈值（最大加速点）与行为曲线陡增位置是否一致。
- 产物：`figs/fig6_behavior_quit.png`（预测概率曲线）、`figs/fig7_survival.png`（KM 分层）。
- 验收：`python src/analyze.py` 后上述两图存在；报告新增「行为层」小节并给出「主观 vs 行为阈值对照」一句话结论。

#### R-09｜分层与调节效应（森林图）

- 需求：在混合效应模型中加入 `wealth_group`（3 档）、`skill`（可二分为新/老手）、`died`、`died_to_player` 的交互项；产出各层 `total_loss_ratio` 斜率的点估计 + 95%CI **森林图**（`figs/fig8_forest.png`）。
- 验收：图中每层给出 n；若某层样本不足（n<200）需在图注标注「样本不足，仅参考」。

#### R-10｜敏感性分析面板

- 需求：新增 `src/sensitivity.py`，对以下参数各扫一遍并输出 CSV + 一张阈值稳定性图（`figs/fig9_sensitivity.png`）：
  - 分箱宽度 `width ∈ {0.05, 0.1, 0.2}`
  - LOESS `frac ∈ {0.2, 0.35, 0.5}`
  - 三次截断阈值 `truncate_at ∈ {9.5, 9.99, 10.01(=不截断)}`
  - 是否剔除 `died=1` 样本（保留 vs 仅存活）
- 验收：输出 `data/sensitivity.csv`（列：参数名、取值、主口径拐点、副口径拐点、是否外推）；报告中给出「阈值对参数的敏感度区间」。

#### R-11｜真实数据接入 E2E（问卷路线 B 优先）

- 需求：提供 `data/README.md`（或 PRD 附录）说明 CSV schema；提供示例真实数据路径约定：`data/survey_matches.csv`（问卷）与 `data/telemetry_matches.csv`（遥测）。`run_all.py --data <csv>` 一键全链，且网页顶部显示**数据来源标签**（模拟 / 问卷 / 遥测），避免误引用。
- 验收：用 `python survey/survey_vignette.py 30` 生成的空白模板 + 手工填 30 人的模拟答案，能跑通全链并在网页显示「数据来源：问卷」。
- 备注：问卷数据 `loss_rate` 已具全、`total_loss_ratio` 可由 `lost_value/carry_value` 推出（校验器负责）。

### 5.3 P2（工程化与体验）

| ID | 需求 | 验收标准 |
|---|---|---|
| R-12 | 文档与发布工程：填充 `docs/research_log.md`（按时间序记录每次结论与决策）、新增 `CHANGELOG.md`、提交规范化（`feat/fix/docs/test` 前缀）、PR 模板 | `research_log.md` 非空且含 v1.4/v1.5 两条记录；`CHANGELOG.md` 含 v1.5 段 |
| R-13 | 发布打包脚本：生成含 `index.html + assets/plotly.min.js + data/curve_data.json + figs/` 的 zip（`.gitignore` 已忽略 `*.zip`），可选生成 `index.inline.html` 单文件版 | `python src/build_release.py` 产出 `dist/extraction_loss_research_vX.Y.zip` 并打印清单 |
| R-14 | 网页交互增强：输入状态写入 URL hash（可分享）、导出当前视图 PNG / 分箱 CSV、移动端断点布局（现有 `flex` 断点已有，需验证 375px 宽可用） | 分享含 hash 的 URL 打开后输入框与口径开关状态一致；导出文件名含时间戳 |
| R-15 | 中文/英文双语报告（可选）：网页增加语言开关 | 切换后图例与面板文案不残留 `{{` 模板占位 |
| R-16 | 陈旧产物清理：提交当前暂存区的删除（`figs/fig5_spline_fit.png`、`figs/fig5_spline_fit_ext.png`、`survey/summary_report_beta.md`），在 README 中补登 `docs/` 与 `PRD.md`/`agent.md` 条目 | `git status --short` 干净；README 目录树与 `git ls-files` 一致 |

---

## 6. 数据与前端契约（**不可随意变更**）

### 6.1 输入 CSV（`data/matches.csv` 由 `simulate_data.py` 生成；真实数据须含同样列）

| 列名 | 类型 | 说明 |
|---|---|---|
| `player_id` | int/str | 玩家唯一 ID（混合效应分组） |
| `match_id` | int/str | 对局 ID |
| `skill` | float 0~1 | 技术水平（可选） |
| `wealth_group` | str | `穷人/中产/富人`（分层用；缺失则跳过 fig4/fig8） |
| `carry_value` | float >0 | 本局携带总价值（含装备/子弹/容器） |
| `found_loot_value` | float ≥0 | 局内拾取战利品价值 |
| `lost_value` | float ≥0 | 本局丢失总价值 |
| `loss_rate` | float 0~1 | 副口径：装备损失率 |
| `total_loss_ratio` | float ≥0 | **主口径**：丢失总价值 / 携带价值（死亡含战利品，可 >1） |
| `potential_change_ratio` | float | (带出 − 损失)/携带，正=净收益（目前未用于建模，保留） |
| `died` | 0/1 | 是否死亡 |
| `died_to_player` | 0/1 | 是否死于真人玩家 |
| `survived_min` | float | 局内时长（分钟） |
| `frustration` | float 1~10 | **主因变量**：局后挫败感 |
| `early_quit` | 0/1 | 行为层：局后提前结束会话 |
| `next_gap_min` | float >0 | 行为层：距下一局的时间间隔 |

- 编码：`utf-8-sig`（带 BOM），首行表头，无注释行。
- 问卷路线 B 产物（`survey/survey_vignette_responses.csv`）列名对齐且多出 `block/willingness/death_cause/frust_source/note`，分析脚本只取上表列，多余列忽略。

### 6.2 前端数据源 `data/curve_data.json`（`fit_improved.py` 生成，`gen_webpage.py` 消费）

实测顶层键（**契约快照，任何新增键须同步更新本表与 `test_curve_contract.py`**）：

| 键 | 内容 | 实测结构 |
|---|---|---|
| `meta` | 主口径（`total_loss_ratio`）元数据 | `n_players, n_matches, threshold_pct, threshold_ci_low_pct, threshold_ci_high_pct, cubic_threshold_pct, cubic_threshold_ci_low_pct, cubic_threshold_ci_high_pct, cubic_truncated_x_max, cubic_inflection_in_range, cubic_a_sign` |
| `binned` | 主口径分箱均值 | 每项 `{loss_rate_mid, frustration_mean, ci, n}` |
| `binned_behavior` | 主口径分箱行为比例 | 同上结构 |
| `spline_fit` | 主口径 B 样条曲线 | 1,066 点 `{x, y}` |
| `spline_deriv` | 样条一阶导 | `{x, y}` |
| `spline_curvature` | 样条二阶导 | `{x, y}` |
| `cubic_fit` | 主口径三次拟合曲线 | 400 点 `{x, y}` |
| `cubic_deriv2` | 三次二阶导 | `{x, y}` |
| `extended` | 副口径（`loss_rate`）镜像：`meta / binned / spline_fit / cubic_fit` | `extended.spline_fit` 265 点、`extended.cubic_fit` 400 点 |
| `loess` | 主口径 LOESS 平滑 | 1,066 点 `{x, y}` |
| `frustration_source_adjust` | 网页「挫败来源」微调量 | `{death_dominated: 0.8, loss_dominated: -0.5, mixed: 0.0}` |

- `x` 单位：主口径为**绝对值**（1.817 = 181.7%）；网页用 `*100` 显示为百分比。
- 网页 `xa='tlr'` 用顶层字段；`xa='lr'` 用 `extended`（脚本内变量名 `EX`）。

### 6.3 网页 → 用户可见的关键输出（`index.html`）

「检测结果」区必须同时给出：本局 `loss_rate`、`total_loss_ratio`、预测挫败感（含来源微调）、状态徽章（安全 / 接近最大加速点 / 最大加速区间 / 超越最大加速点）、历史样本分位。两种口径的阈值与 95%CI 并列展示。

---

## 7. 非功能需求

| 类别 | 要求 |
|---|---|
| 性能 | 14,094 局全链（`run_all.py`）本机 < 90 s；单脚本 < 45 s（`fit_improved.py` 已含 200 次 bootstrap，若加阈值 CI bootstrap 需控制在 +30 s 内） |
| 可复现 | 所有随机过程固定种子（现状：`simulate_data`=42、`analyze`=7、`fit_improved`=17）；同环境重跑 `curve_data.json` 数值一致（浮点容差 1e-9） |
| 离线 | `index.html` 断网可渲染（本地 `assets/plotly.min.js` 优先，多 CDN 兜底）；`--inline` 版完全自包含 |
| 兼容 | Python ≥ 3.10（实测 3.13.12）；Windows/macOS/Linux 均可；脚本用「脚本上级目录」定位项目根，任意 CWD 可运行（此约定必须保持） |
| 依赖 | 仅 `numpy pandas scipy statsmodels matplotlib`（开发期加 `pytest`）；**不得**引入额外数据处理框架或前端构建工具 |
| 文件体积 | `index.html` < 400 KB（不含内嵌 Plotly）；`index.inline.html` 属本地/发布产物，不进 git |
| 中文字体 | 绘图脚本设 `font.sans-serif = Microsoft YaHei/SimHei`；Linux/CI 缺字体时中文可能变方框 → 需降级提示 |

---

## 8. 里程碑

| 里程碑 | 内容 | 出口标准 |
|---|---|---|
| **M1 可换数据（P0）** | R-01~R-06 | `python src/run_all.py` 全绿；`python -m pytest -q` 全绿；`git status` 干净；README 命令表与实现一致 |
| **M2 结论严谨（P1 前半）** | R-07、R-10 | 报告含「天花板效应敏感性」+「敏感性面板」两组数值 |
| **M3 行为层（P1 后半）** | R-08、R-09、R-11 | 网页出现数据来源标签；行为图与森林图入库并进入报告 |
| **M4 产品化（P2）** | R-12~R-16 | 有 CHANGELOG、发布 zip、URL 状态分享；README 目录树与实际一致 |

---

## 9. 风险与对策

| 风险 | 影响 | 对策 |
|---|---|---|
| 主口径拐点属外推（181.7% > 观测上限 166.2%）被当成"实测结论"对外引用 | 结论失真 | R-06 机器标注 + CLI/报告/网页三处一致；对外材料必须同时给出观测上限 |
| 三次多项式 `a<0` 时"拐点 ≠ 最大加速点"语义被误读 | 方法学质疑 | R-06 语义守卫；`docs/methodology.md` 明确三次与 B 样条的定义差异（`a<0` 时 `-b/(3a)` 不是加速度峰） |
| 天花板截断（10 分）导致阈值估计偏移 | 阈值偏移 | R-07 Tobit + 有序 logit 对照 |
| `died` 主导挫败（死亡本身而非金额）造成混杂 | 高估损失效应 | 保留"死了但带白装"对照样本；R-09 交互项；R-10 剔除 `died=1` 敏感性 |
| 真实数据列名/口径与模拟不一致（尤其 `total_loss_ratio` 缺失） | 链条断裂 | R-03 校验器 + `--xcol` + 数据来源标签 |
| 大文件（`index.inline.html` 4.5 MB、`plotly.min.js` 4.3 MB）反复入库 | 仓库膨胀 | R-01 移出索引（`.gitignore` 已备）；发布 zip 走 `dist/` |
| 多脚本手动按序跑导致产物版本错配 | 报告与网页数字不一致 | R-04 编排 + 一致性断言 |
| 依赖版本漂移（pandas 3.x / numpy 2.x 行为变化） | 数值结果变动 | R-05 `requirements.txt` 锁定 + 回归测试 |
| 单文件 HTML 内嵌 JSON 体积增长（现 194 KB / 内嵌 Plotly 后 4.54 MB） | 加载慢 | 曲线点下采样（`spline_fit` 1,066 点 → 400 点）列入 R-14 可选项 |

---

## 10. 度量指标（DoD 量化）

1. 一条命令从零重跑全链成功：`python src/run_all.py`（退出码 0）。
2. `python -m pytest -q` 通过率 100%，用例数 ≥ 8。
3. 产物一致性断言 3/3 通过（样本量三角对齐：CSV ↔ JSON ↔ 报告/网页）。
4. 坏数据拦截率：≥ 4 类注入错误全部拦截。
5. 主口径结论在三处（CLI / `summary_report.md` / `index.html`）数值完全一致，且外推标记一致。
6. `--inline` 不再改动 `index.html`（验收脚本断言其哈希不变）。

---

## 11. 决策记录（Decision Log）

> 已确认的决策，作为后续开发的硬前提；如需推翻，必须先更新本表并在 `docs/research_log.md` 记录原因。

| ID | 日期 | 决策 | 依据 / 影响面 |
|---|---|---|---|
| **D-01** | 2026-10-13 | **`index.inline.html` 移出版本跟踪**：执行 `git rm --cached index.inline.html`（文件保留在本地磁盘），由本地/发布流程按需生成；`.gitignore` 保留该条目 | 4.54 MB 单文件长期入库无收益（Pages 只需要 `index.html` + `assets/plotly.min.js`）；对应 G-08 / R-01 |
| **D-02** | 2026-10-13 | **主口径唯一 = `total_loss_ratio`**；`loss_rate` 仅作方法对照（`--xcol loss_rate`） | 对应 G-02 / R-02；影响 fig1~fig4、混合效应模型、报告分箱表 |
| **D-03** | 2026-10-13 | **阈值对外表述必须带口径与外推标注**：主口径三次拐点 181.7% 超出观测上限 166.22%，任何材料（README/网页/报告/汇报）不得只给单点数字 | 对应 G-03 / G-04 / R-06 |
| **D-04** | 2026-10-13 | **「真值公式」不可改动**（`true_frustration()` / `THRESHOLD=0.70`），方法学变化只能写入 `docs/methodology.md` | 真值 70% 是整套方法的校验基准；见 §3.2 非目标 |

---

## 附录 A｜命令速查（当前实现，v1.4）

```powershell
# 第 1 步：模拟数据（500 玩家 / 14094 局）
python src/simulate_data.py
# 第 2 步：分箱 + LOESS + 分段回归 + 分层 + 混合效应 → figs/fig1~4 + summary_report.md
python src/analyze.py [你的数据.csv]
# 第 3 步：B 样条 + 三次拐点 → data/curve_data.json + figs/fig5_*
python src/fit_improved.py [你的数据.csv]
# 第 4 步：交互式网页（必须在第 3 步之后运行，JSON 是生成时内嵌的）
python src/gen_webpage.py            # → index.html（本地 plotly 优先 + 多 CDN 兜底）
python src/gen_webpage.py --inline   # → 当前实现覆盖写入 index.html（R-01 待修）
# 问卷材料
python survey/survey_template.py            # → survey/survey_template.csv
python survey/survey_vignette.py 30         # → 30 人 × 22 情境答题模板
```

> 顺序依赖：`analyze.py` 会读取 `data/curve_data.json`（缺失时不阻断，`load_curve_meta()` 返回空 dict，报告里主口径段落自动省略）；
> `gen_webpage.py` **必须**在 `fit_improved.py` 之后运行，否则网页固化的是旧 JSON。

## 附录 B｜产物清单与责任人

| 产物 | 生成者 | 可否手工编辑 |
|---|---|---|
| `data/matches.csv` | `simulate_data.py` | 否（真实数据另存新文件名） |
| `data/curve_data.json` | `fit_improved.py` | 否（前端契约） |
| `summary_report.md` | `analyze.py` | 否（结论模板由脚本生成） |
| `figs/fig1~fig5*.png` | `analyze.py` / `fit_improved.py` | 否 |
| `index.html` | `gen_webpage.py` | 否（改模板请改 `src/gen_webpage.py`） |
| `index.inline.html` | `gen_webpage.py --inline`（R-01 落地后） | 否（不进 git） |
| `survey/*.csv` | `survey/*.py` | 是（仅人工填答区） |

## 附录 C｜术语表

| 术语 | 含义 |
|---|---|
| 总损失率 / `total_loss_ratio` | **主口径**：丢失总价值 / 携带价值，死亡时含战利品，可 >100% |
| 损失率 / `loss_rate` | 副口径：仅装备损失，0~100% |
| 真值阈值 | 生成公式二次项起点 = **70%**（上帝视角，分析脚本事先不知道） |
| 最大加速点 | 拟合曲线**加速度最强处**（B 样条一阶导峰 / 三次函数二阶导过零点），一般晚于真值阈值 |
| 外推 | 估计阈值超出被截断后的观测上限（`cubic_truncated_x_max`，主口径实测 1.6622 = 166.22%） |
| 天花板效应 | `frustration` 被截断在 1~10，末端被压平导致二阶导峰值偏移 |
| 观测范围 | 截断后参与拟合的 x 最大值 |