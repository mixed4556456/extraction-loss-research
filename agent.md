# agent.md｜本仓库的 AI / 自动化开发指南

> 面向：在本仓库继续开发的 AI Agent、自动化脚本、以及新加入的人。
> 配套文档：`PRD.md`（要做什么、验收标准）、`README.md`（怎么用）、`docs/methodology.md`（方法论）、`questionnaire_design.md`（问卷）。
> 最近更新：2026-10-13（对齐 v1.4 交付物 `a0cbbaf`）

---

## 0. 硬规则（Red Lines，违反即返工）

1. **不要手工编辑生成物**：`index.html`、`index.inline.html`、`data/curve_data.json`、`data/matches.csv`、`summary_report.md`、`figs/*.png`、`survey/*.csv` 全部由脚本产出。要改内容 → 改 `src/*.py` 模板/逻辑后重跑。
2. **不要为了让结果"好看"而改真值公式**：`simulate_data.py` 的 `true_frustration()` 与 `THRESHOLD=0.70` 是**校验基准**（上帝视角）。只能改 `docs/methodology.md` 的记录，不能调公式去凑拟合结果。
3. **不要引入新依赖 / 框架 / 构建工具**：仅 `numpy pandas scipy statsmodels matplotlib`（测试加 `pytest`）。不使用 Flask/Node 构建/JS 打包器等。
4. **保持「脚本上级目录 = 项目根」约定**：所有脚本用 `ROOT = Path(__file__).resolve().parent.parent`。不要改成 `Path.cwd()` 或相对路径——这会让脚本只能在特定 CWD 下运行。
5. **不要改前端数据契约而不改三处**：若动 `curve_data.json` 的键 → 必须同步 `PRD.md §6.2`、`src/gen_webpage.py` 的消费代码、以及（落地后的）`tests/test_curve_contract.py`。
6. **跑 `gen_webpage.py` 前必须先跑 `fit_improved.py`**：网页把 JSON 在生成时**内嵌**进 HTML，顺序反了就固化了旧数据。
7. **不要用 `--inline` 覆盖主文件**：当前实现有缺陷（见 §7 陷阱 P-01），`--inline` 会写 `index.html`；在 R-01 修复前，若必须生成内嵌版，请**先备份 `index.html` 再跑**，并把结果另存为 `index.inline.html`。
8. **不要提交 4 MB 级大文件**：`index.inline.html`（PRD **D-01** 已批准移出版本跟踪）、`*.zip`。`assets/plotly.min.js`（4.35 MB）是**例外且必需**（离线渲染依赖它，已在索引中）。
9. **不要静默吞掉数据问题**：换真实数据时，缺列/越界/NaN 必须显式报错（R-03 校验器落地后由它负责）。
10. **保留中文注释与文档风格**：仓库所有文档、终端输出、图标题均为中文，遵循现有写法（含"口径""最大加速点""外推"等术语），不要改成英文或换术语。

---

## 1. 快速事实

| 项 | 值 |
|---|---|
| 项目根 | 仓库根目录（`README.md` 同级） |
| 数据规模（模拟） | 500 玩家 / 14,094 局 |
| 主口径 X | `total_loss_ratio`（丢失总价值/携带价值，可 >100%） |
| 副口径 X | `loss_rate`（仅装备，0~100%） |
| 真值阈值（上帝视角） | 70%（生成公式二次项起点） |
| 主口径最大加速点（当前 JSON） | 三次 181.7%（95%CI 156.6~218.8，**外推**，观测上限 166.22%）；B 样条 142.7%（CI 退化） |
| 副口径最大加速点（当前 JSON） | 三次 50.9%（CI 50.1~52.0，范围内）；B 样条 9.8% |
| 随机种子 | `simulate_data`=42、`analyze`=7、`fit_improved`=17（**固定种子 = 可复现的前提**） |
| 运行环境（实测） | Python 3.13.12；numpy 2.5.3 / pandas 3.0.6 / scipy 1.18.1 / statsmodels 0.15.0 / matplotlib 3.11.2；pytest **未安装** |
| 部署 | push `main` → GitHub Pages（根目录整包上传，依赖根目录的 `index.html`） |

---

## 2. 环境准备

```powershell
python --version                     # 期望 ≥3.10（当前实测 3.13.12）
python -c "import numpy,pandas,scipy,statsmodels,matplotlib;print('ok')"
# 缺依赖时（R-05 落地后优先用 requirements.txt）：
python -m pip install numpy pandas scipy statsmodels matplotlib
python -m pip install pytest         # 仅在写/跑测试时需要
```

- 绘图脚本已设 `matplotlib.use("Agg")`（只出文件不弹窗）与中文字体 `Microsoft YaHei/SimHei`；在无该字体的 Linux 上中文会变方框，属已知限制。
- 脚本可能打印 `warning: LF will be replaced by CRLF`（`core.autocrlf`），与本项目逻辑无关。
- PowerShell 下 `Select-String`/`Get-Content` 对 UTF-8 中文可能显示乱码，但文件本身是正常 UTF-8；**判断文件内容请用 `read_files` 工具或 Python 读取，不要以控制台乱码为准**。

---

## 3. 目录与产物归属

| 路径 | 归属 | 说明 |
|---|---|---|
| `src/simulate_data.py` | 源码 | 第 1 步，生成 `data/matches.csv`（`utf-8-sig`） |
| `src/analyze.py` | 源码 | 第 2 步，fig1~fig4 + `summary_report.md`；读取 `data/curve_data.json`（可选） |
| `src/fit_improved.py` | 源码 | 第 3 步，fig5×2 + `data/curve_data.json` |
| `src/gen_webpage.py` | 源码 | 第 4 步，`index.html`（含 `--inline`） |
| `data/matches.csv` | 产物 | 模拟数据（真实数据请另存 `data/survey_matches.csv` / `data/telemetry_matches.csv`） |
| `data/curve_data.json` | 产物/契约 | 前端唯一数据源，341 KB |
| `summary_report.md` | 产物 | `analyze.py` 生成，含结论模板（`___` 占位待人工填） |
| `figs/*.png` | 产物 | 现有：fig1_binned_curve / fig2_loess / fig3_breakpoint / fig4_stratified / fig5_spline_fit_total_loss_ratio / fig5_spline_fit_loss_rate |
| `index.html` | 产物 | 194 KB，Pages 入口 |
| `index.inline.html` | 产物 | 4.54 MB；`.gitignore` 已忽略但**仍在 git 索引中**（见陷阱 P-02） |
| `assets/plotly.min.js` | 资源 | 4.35 MB，离线渲染必备，**必须提交** |
| `docs/methodology.md` | 文档 | 方法论迭代记录（16 KB，内容详实，改方法必须同步它） |
| `docs/research_log.md` | 文档 | 目前 **0 字节**，PRD R-12 要求填充 |
| `survey/*.py` `.csv` | 源码/产物 | 问卷模板与场景生成 |
| `.github/workflows/pages.yml` | CI | push main 自动部署根目录 |

---

## 4. 标准工作流（改任何东西都从这套命令开始）

```powershell
cd <仓库根>
python src/simulate_data.py      # 1) 数据（不改模拟逻辑时可跳过；重跑会覆盖 data/matches.csv）
python src/analyze.py            # 2) fig1~4 + summary_report.md
python src/fit_improved.py       # 3) curve_data.json + fig5×2
python src/gen_webpage.py        # 4) index.html
python src/gen_webpage.py --inline   # 可选：自包含版（先读陷阱 P-01！）
```

换数据（不作弊、不改代码路径）：

```powershell
python src/analyze.py 你的数据.csv
python src/fit_improved.py 你的数据.csv     # 注意：传参不会自动更新网页，仍需第 4 步
```

顺序铁律：**4 必须在 3 之后**；2 在 3 之前跑也能出图，但报告里的「主口径」段落会缺少（因为那时 JSON 还是旧的或不存在）。
一次完整重跑后，`curve_data.json` 的数值应与上一版**逐位一致**（种子固定）；若不一致且你只改了文档/网页模板，说明你误改了统计代码。

---

## 5. 数据契约（改数据相关代码前必读）

**输入 CSV**：16 列，见 `PRD.md §6.1`（`player_id, match_id, skill, wealth_group, carry_value, found_loot_value, lost_value, loss_rate, total_loss_ratio, potential_change_ratio, died, died_to_player, survived_min, frustration, early_quit, next_gap_min`），编码 `utf-8-sig`，无注释行。

**前端 JSON**：`data/curve_data.json` 顶层键 =
`meta, binned, binned_behavior, spline_fit, spline_deriv, spline_curvature, cubic_fit, cubic_deriv2, extended, loess, frustration_source_adjust`
（`extended` 内含 `meta / binned / spline_fit / cubic_fit`）。各键结构与实测点数见 `PRD.md §6.2`。
**x 单位是绝对值**（`1.817` 表示 181.7%），网页负责 `*100` 显示——加新字段时务必遵守，否则图上刻度会差 100 倍。

**网页消费点**（改 JSON 后必须确认这些仍在）：`gen_webpage.py` 中 `const D=<embedded>; const EX=D.extended;`，随后读取
`D.meta / D.binned / D.cubic_fit / D.extended.meta / D.extended.binned / D.extended.cubic_fit / D.frustration_source_adjust`，
用 `meta.threshold_pct / cubic_threshold_pct / cubic_threshold_ci_low_pct / cubic_threshold_ci_high_pct / threshold_ci_low_pct / threshold_ci_high_pct` 画竖线与带状区间。

---

## 6. 代码地图（关键函数与返回约定）

### 6.1 `src/simulate_data.py`（161 行）

- 常量：`RNG = default_rng(42)`、`N_PLAYERS = 500`、`THRESHOLD = 0.70`、`OUT = ROOT/data/matches.csv`
- `make_players()`：skill(Beta(2,2)) / wealth(Lognormal(10,0.7)) / sens(N(0,0.7))，按 wealth 三分位得 `wealth_group`
- `generate_loot(RNG, survived_min, wealth, early=False)`：战利品价值，`early=True` 时乘 U(0.1,0.6)
- `true_frustration(x, died, died_to_player, sens)`：**真值公式**（`1.2 + 2.5x + 6.0·max(0,x−0.70)² + 1.0·died + 0.6·died_to_player + sens + N(0,0.8)`，`np.clip(f,1,10)`）
- `main()`：每人 15~40 局；死亡时 `total_lost = carry + found_loot`（故 `total_loss_ratio` 可 >1）；存活时 `total_lost = carry*loss_rate`
- 行为层：`p_quit = 1/(1+exp(−(3.0*(f−5)/3)))`，`early_quit ~ Bernoulli(p_quit)`；`next_gap_min ~ Lognormal(1.5+1.2(1−p_quit), 0.5)`

### 6.2 `src/analyze.py`（225 行）

- `RNG = default_rng(7)`；`binned_stats(df, xcol, ycol, width=0.1)` → `bin_mid/mean/std/n/ci`（`ci=1.96·std/√n`）
- `fig1_binned(df)` → 双面板（挫败感 + early_quit 比例），返回分箱表 `st`
- `fig2_loess(df)`：`lowess(frustration ~ loss_rate, frac=0.35)`，散点抽样 800
- `fit_piecewise(x, y, c)` → `(SSE, beta)`；`find_breakpoint(df, n_boot=120)`：网格 `0.20~0.90 step 0.02` + bootstrap 百分位 → `(c_hat, lo, hi, beta, grid, sse)`
- `fig3_breakpoint(df)` → `(c_hat, lo, hi, beta)`（内部调用 `find_breakpoint`）
- `fig4_stratified(df)`：按 `wealth_group` 分组 LOESS（`frac=0.45`，`groupby(observed=True)`）
- `mixed_model(df)`：`smf.mixedlm("frustration ~ loss_rate + died + died_to_player", groups=player_id).fit(reml=False)`，异常时**返回 None 不阻断**
- `load_curve_meta()`：读 `data/curve_data.json`，缺失返回 `{}` 而不报错（**这是两脚本间唯一的软依赖**）
- `report(df, st, c_hat, lo, hi, beta, res)`：写 `summary_report.md`，含「结论模板」（`___` 占位）
- `main()`：`Path(sys.argv[1])` 覆盖数据路径（**当前只认第 1 个位置参数，尚无 `--xcol`**，R-02 待加）
- ⚠️ 现状：全文**未使用** `total_loss_ratio`，fig1~4/混合模型/分箱表都用 `loss_rate`（PRD G-02）

### 6.3 `src/fit_improved.py`（432 行）

- `RNG = default_rng(17)`；`FIG_DIR`/`DATA_DIR` 均基于 `ROOT`
- `binned_stats(df, xcol, ycol, width=0.1)`：与 analyze 版同构（重复实现，勿擅自统一除非同时改两处）
- `cubic_fit_inflection(x, y, n_boot=200, truncate=True, truncate_at=9.99)`：
  截断 `y < truncate_at`（去掉 10 分饱和样本；截断后 <20 点则回退全量）→ `lstsq([x³,x²,x,1])` → 拐点 `x = −b/(3a)` → bootstrap 200 次求 CI
- `fig5_spline(df, xcol)` → **16 元组**，顺序固定：
  `0 spl_spline, 1 xs, 2 y_fit, 3 y_deriv, 4 curvature, 5 thresh, 6 ci_lo, 7 ci_hi, 8 coeffs, 9 x_infl, 10 ci_lo_c, 11 ci_hi_c, 12 xs_c, 13 y_cubic, 14 y_d2_c, 15 x_trunc_max`
  （`main()` 用切片 `[:8]` / `[8:15]` / `[15]` 解包，改动顺序会静默错配——新增返回值只能**追加在尾部**）
- `export_curve_json(...)`：33 个位置参数（先主口径 `tlr` 后副口径 `lr` 各 16/17 个），写 `data/curve_data.json`（`ensure_ascii=False, indent=2`）
- `main()`：`Path(sys.argv[1])` 可换数据；先跑 `xcol="total_loss_ratio"`（主）再跑 `xcol="loss_rate"`（副）

### 6.4 `src/gen_webpage.py`（123 行）

- `ROOT/data/curve_data.json` 在**模块导入时**读取 → `cd`、`m = cd["meta"]`、`ex = cd.get("extended", {})`
- `build_plotly_tags(inline=False)`：`--inline` 时内嵌本地 `assets/plotly.min.js`（把 `</script` 转义为 `<\/script`），否则本地 `<script src>` + 三个 CDN `document.write` 兜底（jsd.onmicrosoft.cn → jsdelivr → unpkg，版本常量 `PLOTLY_VERSION="2.35.2"`）
- 模板 `H` 是一个 f-string：**所有 JS 花括号必须写成 `{{ }}`**（改模板时最容易踩的坑）
- 页面结构：左侧 Plotly 曲线（分箱±CI + B 样条 + 三次曲线 + 两条阈值竖线 + 用户星标）、右侧输入面板（携带价值 `cr` / 战利品 `fl` / 已损失 `ls` / 口径切换 `xa=tlr|lr` / 挫败来源 `fs`）；`up()` 为唯一更新函数
- 落盘：`(ROOT / "index.html").write_text(H, encoding="utf-8")`（**硬编码路径，R-01 待加 `--out`**）

---

## 7. 任务手册（Recipe）

### R-a｜改"最大加速点"口径或算法
1. 改 `src/fit_improved.py` 的 `cubic_fit_inflection` / `fig5_spline`（**只能向 16 元组尾部追加返回值**，并同步 `main()` 的切片解包与 `export_curve_json` 的参数顺序）。
2. 重跑 `python src/fit_improved.py` → `python src/gen_webpage.py`。
3. 同步三处文字：`docs/methodology.md`（方法定义）、`README.md`（结论数值）、`PRD.md §2.2`（结论表）。
4. 若改了 JSON 键：同步 `src/gen_webpage.py` 消费代码 + `PRD.md §6.2` + `agent.md §5`。
5. 验收：网页图例、`summary_report.md`、终端输出三处阈值一致。

### R-b｜加一个新字段（如 `extract_success`）
顺序固定，缺一不可：
`src/simulate_data.py`（生成该列）→ `data/matches.csv` 重生成 → `PRD.md §6.1` 补列说明 →（R-03 落地后）`validate_data.py` 加取值域 → 分析脚本按需使用 → 若进入网页则改 `gen_webpage.py`（**JSON 花括号写成 `{{ }}`**）。
注意：`analyze.py`/`fit_improved.py` 会把多余列忽略，所以真实数据加列不会立刻报错——这也意味着**必须靠校验器兜底**。

### R-c｜加一张图
1. 命名沿用 `figN_描述.png`（全小写 + 下划线），避免 `fig5_spline_fit.png` 这类曾出现又删除的临时名。
2. 用 `plt.rcParams` 已设的中文字体；`dpi=150`；`bbox_inches="tight"`（分箱图有 CI 竖线时会用到）。
3. `plt.close(fig)` 必须调用（脚本长期运行复现时避免内存增长）。
4. 同步 `README.md` 的「流水线输出」表与 `PRD.md §5` 的验收标准。

### R-d｜改网页（`index.html`）
- 只改 `src/gen_webpage.py` 里的 CSS 常量 `S` / HTML 模板 `H` / JS 函数 `up()`、`dr()`；**不要**直接改 `index.html`。
- f-string 转义自检：跑完 `gen_webpage.py` 后，产物中不应出现未替换的 `{{`/`}}`；`node --check` 不适用于整页（含 HTML），可用 `Select-String -Path index.html -Pattern 'function up\(\)'` 与浏览器打开验证。
- 改了面板字段，记得更新 `up()` 里 `document.querySelectorAll('#cr,#fl,#ls,input[name="xa"],input[name="fs"]')` 的事件绑定列表，否则新控件不触发重绘。
- Plotly 兜底链不要删（离线可用是本项目的硬需求）；新增 CDN 只能**追加**在末尾。

### R-e｜换真实数据
1. 真实文件放 `data/`（例如 `data/survey_matches.csv`），**不要覆盖** `matches.csv`（保留模拟基准用于回归对比）。
2. 缺 `total_loss_ratio` 但有 `lost_value`/`carry_value` → 先补列（问卷路线已天然具备），别在脚本里临时改 `xcol` 硬编码。
3. 跑完把「数据来源」写进网页面板与报告（R-11 落地后为自动化）。
4. 必查：`died=0` 的局 `total_loss_ratio` 是否被人为设成 0（会造成存活区假聚集）；`frustration` 是否有大量 10（天花板，触发 R-07 分析）。

### R-f｜发版
1. 更新 `README.md`（命令/结论）、`CHANGELOG.md`（R-12 落地后）、`docs/research_log.md`（记录本轮结论变化）。
2. 重跑四步 + 校验（§8 清单）。
3. 提交策略：源码/文档/`data/curve_data.json`/`index.html`/`figs/` 一并提交；`index.inline.html`、`*.zip` 不入库。
4. `git tag vX.Y` → push `main` → Pages 自动部署（务必确认 `assets/plotly.min.js` 仍被跟踪，否则线上离线渲染失效）。

---

## 8. 验证清单（每次改动后必跑）

```powershell
cd <仓库根>
# 1) 全链重跑（R-04 落地前用四步命令代替）
python src/simulate_data.py; python src/analyze.py; python src/fit_improved.py; python src/gen_webpage.py
# 2) JSON 契约与数值自检
python -c "import json;d=json.load(open('data/curve_data.json',encoding='utf-8'));print(list(d));print(d['meta'])"
# 3) 网页产物自检
python -c "h=open('index.html',encoding='utf-8').read();print('len',len(h));print('plotly', 'Plotly.newPlot' in h);print('leftover_braces', '{{' in h)"
# 4) 样本量三角对齐
python -c "import json,pandas as pd;a=len(pd.read_csv('data/matches.csv'));b=json.load(open('data/curve_data.json',encoding='utf-8'))['meta'];print(a,b['n_matches'],b['n_players'])"
# 5) 结果一致性（R-05 落地后）
python -m pytest -q
# 6) 变更面自检
git --no-pager status --short
```

期望：步骤 2 的键列表与 `PRD.md §6.2` 一致；步骤 3 打印 `leftover_braces False` 且 `len` ≈ 190~200K（非 inline）；步骤 4 三数一致（14094 / 14094 / 500）；步骤 6 只出现你**有意**修改的文件。

---

## 9. 陷阱清单（本仓库已实际踩过）

| # | 陷阱 | 现象 | 正确做法 |
|---|---|---|---|
| P-01 | `--inline` 覆盖主文件 | 生成 4.5 MB 的 `index.html`，把 CDN 版冲掉，容易误提交 | 先备份；R-01 加 `--out` 后按新命令用 |
| P-02 | `.gitignore` 对**已跟踪**文件无效 | `index.inline.html` 已写进 `.gitignore` 却仍被 git 跟踪 | 需 `git rm --cached index.inline.html` 才真正移除（PRD **D-01** 已批准，随本次提交执行） |
| P-03 | fig5 旧文件名残留 | 曾产出 `figs/fig5_spline_fit.png`、`fig5_spline_fit_ext.png`，与现名（`..._total_loss_ratio.png`）重复 | 重跑后检查 `figs/` 是否有多余文件；删除只在一次提交里做 |
| P-04 | f-string 里的 JS 花括号 | 少写一个 `}` 导致整页 JS 语法错误，页面空白 | 一律 `{{ }}`；生成后用 `{{` 自检（§8 步骤 3） |
| P-05 | 16 元组解包静默错配 | 在 `fig5_spline` 中间插入返回值 → `thresh/ci_lo` 全错 | 只追加到尾部，且同步 `main()` 切片与 `export_curve_json` |
| P-06 | CSV 带 BOM / 注释行 | `utf-8-sig` 读入时首列名可能变成 `\ufeffplayer_id` | 统一 `encoding="utf-8-sig"` 读；`survey_vignette` 产物的第 2 行是 `# 注释行`，**不是数据**，校验/统计前必须跳过 |
| P-07 | PowerShell 中文乱码 | `Get-Content` 显示 `鍥?` 等乱码 | 用 `read_files` 或 Python 读取；不要据此判断文件损坏 |
| P-08 | 顺序错乱导致"图新数据旧" | 先跑 `gen_webpage.py` 再跑 `fit_improved.py` → 网页里是旧阈值 | 固定顺序 1→2→3→4；R-04 编排后不可拆散 |
| P-09 | 混淆"真值阈值"与"最大加速点" | 把 70% 与 181.7% 当同一个数字引用 | 对外表述两者必分开写；外推必须标注（R-06） |
| P-10 | 混合效应不收敛 | `mixedlm` 抛异常 | 现有代码捕获后返回 `None` 并提示（保留该行为，不要让它中断全链） |
| P-11 | Linux/CI 缺中文字体 | 图内中文变方框 | 本机验证用 Windows 字体；CI 若出图需装字体或接受方框（Pages 只依赖 `index.html`，不受影响） |
| P-12 | 用 `Path.cwd()` 定位文件 | 从其他目录运行时找不到 `data/` | 一律 `Path(__file__).resolve().parent.parent` |

---

## 10. 提交与发布规范

- 提交信息前缀沿用现有历史（`feat(v1.4): ...`、`fix: ...`、`docs: ...`）：`feat|fix|docs|test|chore(范围): 中文简述`。
- 一次提交只做一件事；**产物与其生成代码同一次提交**（避免"代码新、产物旧"）。
- 必须入库：`src/`、`survey/`、`docs/`、`README.md`、`PRD.md`、`agent.md`、`questionnaire_design.md`、`data/matches.csv`、`data/curve_data.json`、`figs/`、`index.html`、`assets/plotly.min.js`、`.github/workflows/pages.yml`、`.gitignore`。
- 不入库：`index.inline.html`（R-01 后）、`*.zip`、`__pycache__/`。
- 发布：`git tag vX.Y` + push `main`（Pages 自动部署；`workflow_dispatch` 可手动触发）。
- **提醒**：Pages 上传整仓库根目录，因此根目录不要放无关大文件；`assets/plotly.min.js` 必须在索引中以支持离线加载。

---

## 11. 术语表（与 PRD 附录 C 保持同步）

| 术语 | 含义 | 不要混淆成 |
|---|---|---|
| `total_loss_ratio` | 主口径：丢失总价值/携带价值，可 >100% | ≠ 装备损失率 |
| `loss_rate` | 副口径：仅装备损失，0~100% | ≠ 主口径 |
| 真值阈值 70% | 生成公式二次项起点（上帝视角） | ≠ 拟合出的最大加速点 |
| 最大加速点 | 拟合曲线加速度最强处（三次二阶导过零点 / 样条一阶导峰） | ≠ 真值阈值 |
| 外推 | 估计值超出截断后的观测上限（主口径 166.22%） | 不是"测到了" |
| 天花板效应 | `frustration` 截断 1~10 造成的末端压平 | 不是缺失值 |

---

## 12. 交接待办（按 PRD 优先级，落地后请勾掉并更新本文件）

- [x] **R-01** `gen_webpage.py --out` + `--inline` 不再覆盖 `index.html`（路径修复待开发）；`index.inline.html` **出库决策已定**（PRD **D-01**，`git rm --cached` 已随文档提交执行）
- [ ] **R-02** `analyze.py` 统一到 `total_loss_ratio`（+ `--xcol` 对照）
- [ ] **R-03** 新增 `src/validate_data.py` 并接入两个分析脚本
- [ ] **R-04** 新增 `src/run_all.py` 编排 + 样本量三角断言
- [ ] **R-05** 新增 `tests/`（pytest）与 `requirements.txt`
- [ ] **R-06** B 样条阈值真 bootstrap CI；三次拐点外推/`a<0` 语义守卫三处一致
- [ ] **R-07** 天花板：Tobit + 有序 logit 对照
- [ ] **R-08** 行为层：`early_quit` logistic + `next_gap_min` 生存分析
- [ ] **R-09** 分层交互 + 森林图
- [ ] **R-10** `src/sensitivity.py` 敏感性面板
- [ ] **R-11** 真实数据 E2E + 网页面板「数据来源」标签
- [ ] **R-12** 填充 `docs/research_log.md`（当前 0 字节）+ `CHANGELOG.md`
- [ ] **R-13** `src/build_release.py` 发布 zip
- [ ] **R-14** 网页 URL 状态 / 导出 / 移动端
- [ ] **R-16** 提交暂存区三项删除、README 目录树补登 `PRD.md`/`agent.md`/`docs/`