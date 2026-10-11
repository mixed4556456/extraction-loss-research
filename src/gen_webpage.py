"""生成 index.html（内嵌 JSON；Plotly 本地优先 + 多 CDN 兜底）

用法:
  python src/gen_webpage.py            # index.html：assets/plotly.min.js 优先，缺失则依次试多 CDN
  python src/gen_webpage.py --inline   # 把 Plotly 直接内嵌进 index.html，完全离线自包含（~4.5MB 单文件）
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent   # 项目根（脚本在 src/ 下，data/ assets/ index.html 都位于根目录）
with open(ROOT / "data" / "curve_data.json", encoding="utf-8") as f:
    cd = json.load(f)
m = cd["meta"]
ex = cd.get("extended", {})

PLOTLY_VERSION = "2.35.2"
PLOTLY_CDNS = [
    f"https://jsd.onmicrosoft.cn/npm/plotly.js-dist-min@{PLOTLY_VERSION}/plotly.min.js",  # 国内可直连的 jsDelivr 镜像
    f"https://cdn.jsdelivr.net/npm/plotly.js-dist-min@{PLOTLY_VERSION}/plotly.min.js",
    f"https://unpkg.com/plotly.js-dist-min@{PLOTLY_VERSION}/plotly.min.js",
]
LOCAL_PLOTLY = ROOT / "assets" / "plotly.min.js"


def build_plotly_tags(inline=False):
    """本地 assets/plotly.min.js 优先 → 多 CDN 依次兜底；inline=True 时直接内嵌为单文件。"""
    if inline:
        if LOCAL_PLOTLY.exists():
            js = LOCAL_PLOTLY.read_text(encoding="utf-8").replace("</script", "<\\/script")
            return "<script>" + js + "</script>"
        print("[warn] 未找到 assets/plotly.min.js，退回 CDN 模式")
    tags = []
    if LOCAL_PLOTLY.exists():
        tags.append('<script src="assets/plotly.min.js"></script>')
    for url in PLOTLY_CDNS:
        # 逐个兜底：前一个没加载成功（Plotly 仍是 undefined）时才 document.write 下一个
        tags.append(
            "<script>if(typeof Plotly==='undefined')document.write("
            "'<script src=\"" + url + "\"><\\/script>');</script>"
        )
    return "".join(tags)


PLOTLY = build_plotly_tags(inline="--inline" in sys.argv)

S = """*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"Microsoft YaHei","PingFang SC",sans-serif;background:#f5f6fa;color:#2c3e50;padding:20px}
h1{font-size:22px}.sub{color:#7f8c8d;font-size:14px;margin:4px 0 20px}.l{display:flex;gap:20px;flex-wrap:wrap}
.ca{flex:1 1 660px;min-width:320px}.pa{flex:0 0 300px;background:#fff;border-radius:10px;padding:18px;box-shadow:0 0 8px rgba(0,0,0,.08)}
.pa h3{font-size:15px;margin-bottom:14px;border-left:4px solid #c0392b;padding-left:10px}
.f{margin:12px 0}.f label{display:block;font-size:13px;margin-bottom:4px;color:#555}
.f input{width:100%;padding:7px 10px;border:1px solid #ddd;border-radius:6px;font-size:14px}
.f input:focus{border-color:#2980b9}.rg{display:flex;gap:8px;flex-wrap:wrap}
.rg label{display:flex;gap:4px;font-size:13px;cursor:pointer;border:1px solid #ddd;border-radius:6px;padding:5px 10px}
.rg label:has(input:checked){border-color:#c0392b;background:#fff5f5}
.rb{background:#f0f3f7;border-radius:8px;padding:14px;margin-top:14px}
.rr{display:flex;justify-content:space-between;padding:5px 0;font-size:14px}
.rr .l{color:#555}.rr .v{font-weight:bold}.hl{color:#c0392b;font-size:18px}
.bd{display:inline-block;padding:3px 10px;border-radius:10px;font-size:12px;font-weight:bold}
.bd.s{background:#e8f8f5;color:#27ae60}.bd.d{background:#fdedec;color:#c0392b}
.tn{font-size:12px;color:#7f8c8d;margin-top:10px;line-height:1.5}
.tn strong{color:#2c3e50}.tn .primary{color:#27ae60;font-weight:bold}.tn .ref{color:#e67e22}
#c{width:100%;height:500px}
.sw{display:flex;gap:8px;margin:12px 0}
.sw label{flex:1;text-align:center;padding:6px 4px;font-size:12px;border:1px solid #ddd;border-radius:6px;cursor:pointer;background:#f9f9f9}
.sw label:has(input:checked){border-color:#c0392b;background:#fff5f5;font-weight:bold}
.note-box{background:#fff9e6;border-left:4px solid #e67e22;padding:8px 12px;margin-top:10px;font-size:12px;line-height:1.6;border-radius:4px}"""

J = json.dumps(cd, ensure_ascii=False)

H = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>搜打撤 负反馈曲线</title>{PLOTLY}<style>{S}</style></head><body>
<h1>🎮 搜打撤 — 单局损失→负反馈 曲线</h1>
<div class="sub">基于 {m["n_matches"]} 局 / {m["n_players"]} 名玩家的 B 样条 + 三次函数拟合（v1.4 版 — 两种口径均以三次函数「最大加速点」为主口径，总损失率口径为默认推荐视图）</div>
<div class="l"><div class="ca"><div id="c"></div></div><div class="pa">
<h3>📋 输入本局数据</h3>
<div class="f"><label>💰 携带总价值</label><input type="number" id="cr" value="50000" min="1" step="100"></div>
<div class="f"><label>💎 局内找到战利品价值</label><input type="number" id="fl" value="30000" min="0" step="100"></div>
<div class="f"><label>💸 丢失总价值 (装备+战利品)</label><input type="number" id="ls" value="35000" min="0" step="100"></div>
<div class="f"><label>📊 X 轴指标</label>
<div class="sw"><label><input type="radio" name="xa" value="tlr" checked onchange="up()"><span>总损失率 (含战利品,可>100%) ★(推荐)</span></label><label><input type="radio" name="xa" value="lr" onchange="up()"><span>损失率 (仅装备,0~100%)</span></label></div></div>
<div class="f"><label>🔥 挫败感来源</label>
<div class="rg"><label><input type="radio" name="fs" value="death" checked><span>💀 死亡</span></label><label><input type="radio" name="fs" value="mixed"><span>⚖️ 相当</span></label><label><input type="radio" name="fs" value="loss"><span>📉 物品损失</span></label></div></div>
<div class="rb">
<div class="rr"><span class="l">📊 总损失率(含战利品) ★</span><span class="v" id="tlr">--</span></div>
<div class="rr"><span class="l">📊 损失率(仅装备)</span><span class="v" id="lr">--</span></div>
<div class="rr"><span class="l">🔮 预挫败感</span><span class="v hl" id="pf">--</span></div>
<div class="rr"><span class="l">📍 位置</span><span id="po" class="bd s">计算中</span></div>
<div class="rr"><span class="l">📈 超越玩家</span><span class="v" id="pc">--</span></div>
</div>
<div class="tn" id="tn">⚡ <strong>检测结果（口径与判定点）</strong><br>
  总损失率口径 ★推荐：<span class="primary">三次函数最大加速点 = {m["cubic_threshold_pct"]}%</span>（95%CI {m["cubic_threshold_ci_low_pct"]}%~{m["cubic_threshold_ci_high_pct"]}%）<br>● 三次函数的「拐点」= 曲线斜率最大处 = 整条曲线的「最大加速点」（图中绿色点线 + ◆ 标记）
  ● 参考线：B样条最大加速点 {m["threshold_pct"]}%（95%CI {m["threshold_ci_low_pct"]}%~{m["threshold_ci_high_pct"]}%，观测范围内的经验值）<br>
  ● 该最大加速点在观测上限 {round(m["cubic_truncated_x_max"]*100,1)}% 之外，属外推（CI 偏宽，建议与橙色参考线并读）<br>
  损失率(仅装备)口径：<span class="ref">三次函数最大加速点 = {ex["meta"]["cubic_threshold_pct"]}%</span>（95%CI {ex["meta"]["cubic_threshold_ci_low_pct"]}%~{ex["meta"]["cubic_threshold_ci_high_pct"]}%）<br>● 挫败感量表 1~10 分存在天花板效应，两种口径标出的都是「加速起点」而非终点<br>● X 轴按你填写的数值自动缩放（默认 0~300%），更长的尾部不在视图内，「超越玩家」仍统计全部数据</div>
</div></div>
<script>
const D={J};const EX=D.extended;
function pF(x,xa){{const sp=(xa==='lr'&&EX.spline_fit)?EX.spline_fit:D.spline_fit;const y=sp.filter(p=>p.x<=x);return y.length>0?y[y.length-1].y:1}}
function dr(){{const ca=+document.getElementById('cr').value||1;const fl=+document.getElementById('fl').value||0;const lo=+document.getElementById('ls').value||0;const tr=lo/ca;const r=Math.min(tr,1);const xa=document.querySelector('input[name="xa"]:checked').value;
const sp=(xa==='lr'&&EX.spline_fit)?EX.spline_fit:D.spline_fit;const bi=(xa==='lr'&&EX.binned)?EX.binned:D.binned;const cf=(xa==='lr'&&EX.cubic_fit)?EX.cubic_fit:D.cubic_fit;
const meta=(xa==='tlr')?D.meta:EX.meta;const bs_th=meta.threshold_pct/100;const cb_th=meta.cubic_threshold_pct/100;
const bs_th_pct=meta.threshold_pct.toFixed(1);const cb_th_pct=meta.cubic_threshold_pct.toFixed(1);const cb_in_range=meta.cubic_inflection_in_range;const pf_val=pF(xa==='tlr'?tr:r,xa);const x_val=xa==='tlr'?tr:r;
const primary_th=isNaN(cb_th)?bs_th:cb_th;
let traces=[];
if(xa!=='tlr'){{const dm=0.9942;const ext=sp.filter(p=>p.x>dm);const obs=sp.filter(p=>p.x<=dm);traces.push({{x:obs.map(p=>p.x),y:obs.map(p=>p.y),mode:'lines',name:'B样条',line:{{color:'#c0392b',width:3}}}});if(ext.length>0)traces.push({{x:ext.map(p=>p.x),y:ext.map(p=>p.y),mode:'lines',name:'外推',line:{{color:'#c0392b',width:3,dash:'dash',opacity:0.5}}}})}}else{{traces.push({{x:sp.map(p=>p.x),y:sp.map(p=>p.y),mode:'lines',name:'B样条',line:{{color:'#c0392b',width:3}}}})}}
if(cf&&cf.length>0)traces.push({{x:cf.map(p=>p.x),y:cf.map(p=>p.y),mode:'lines',name:'三次拟合',line:{{color:'#27ae60',width:2,dash:'dot'}}}});
traces.push({{x:bi.map(p=>p.x||p.loss_rate_mid),y:bi.map(p=>p.frustration_mean),error_y:{{type:'data',array:bi.map(p=>p.ci),visible:true}},mode:'markers',name:'箱±95%CI',marker:{{color:'#7f8c8d',size:8}}}});
const bslbl=(xa==='tlr')?('B样条·最大加速点(参考) '+bs_th_pct+'%'):('B样条阈值(参考) '+bs_th_pct+'%');
traces.push({{x:[bs_th,bs_th],y:[0,10],mode:'lines',name:bslbl,line:{{color:'#e67e22',width:2,dash:'dash'}}}});
if(cb_th&&!isNaN(cb_th)){{const cblbl=(xa==='lr'||cb_in_range)?('最大加速点(三次拐点) '+cb_th_pct+'%'):('最大加速点(三次拐点·外推) '+cb_th_pct+'%');traces.push({{x:[cb_th,cb_th],y:[0,10],mode:'lines',name:cblbl,line:{{color:'#27ae60',width:3,dash:'dot'}}}})}}let cb_fx=null,cb_fy=null;if(cb_th&&!isNaN(cb_th)&&cf&&cf.length>0){{let bp=cf[0];for(const p of cf){{if(Math.abs(p.x-cb_th)<Math.abs(bp.x-cb_th))bp=p}}cb_fx=bp.x;cb_fy=bp.y}}if(cb_fx!=null)traces.push({{x:[cb_fx],y:[cb_fy],mode:'markers+text',name:'最大加速点坐标',text:['最大加速点 '+cb_th_pct+'%'],textposition:'bottom right',textfont:{{size:11,color:'#27ae60'}},marker:{{color:'#27ae60',size:12,symbol:'diamond',line:{{width:1,color:'#fff'}}}},showlegend:false}});
traces.push({{x:[x_val],y:[pf_val],mode:'markers+text',name:'你',text:['←你'],textposition:'top center',textfont:{{size:13,color:'#e67e22'}},marker:{{color:'#e67e22',size:18,symbol:'star',line:{{width:2,color:'#fff'}}}}}});
const xTitle=xa==='tlr'?'总损失率 (损失总价值/携带价值, 可>100%)':'本局损失率 (0~100%)';
const xRange=xa==='tlr'?[0,Math.max(2.5,Math.ceil(Math.max(x_val,cb_th)*1.15))]:[-0.02,Math.max(1.02,x_val*1.1)];
const shapes=[{{type:'rect',x0:meta.threshold_ci_low_pct/100,x1:meta.threshold_ci_high_pct/100,y0:0,y1:10,fillcolor:'rgba(230,126,34,0.08)',line:{{width:0}}}}];
if(cb_th&&!isNaN(cb_th)&&meta.cubic_threshold_ci_low_pct!=null)shapes.push({{type:'rect',x0:meta.cubic_threshold_ci_low_pct/100,x1:meta.cubic_threshold_ci_high_pct/100,y0:0,y1:10,fillcolor:'rgba(39,174,96,0.08)',line:{{width:0}}}});
Plotly.newPlot('c',traces,{{title:xTitle,xaxis:{{title:xTitle,range:xRange,tickformat:'.0%',dtick:xa==='tlr'?0.5:0.1}},yaxis:{{title:'挫败感',range:[0.5,10.5],dtick:1}},hovermode:'closest',legend:{{orientation:'h',y:-0.2}},margin:{{l:50,r:20,t:40,b:80}},shapes:shapes}},{{responsive:true,displayModeBar:false}})}}
function up(){{const ca=+document.getElementById('cr').value||1;const fl=+document.getElementById('fl').value||0;const lo=+document.getElementById('ls').value||0;const tr=lo/ca;const r=Math.min(tr,1);const xa=document.querySelector('input[name="xa"]:checked').value;const s=document.querySelector('input[name="fs"]:checked').value;const adj=D.frustration_source_adjust||{{death_dominated:0.8,loss_dominated:-0.5,mixed:0}};const a=s==='death'?adj.death_dominated:s==='loss'?adj.loss_dominated:adj.mixed;const b=pF(xa==='tlr'?tr:r,xa);const f=Math.min(10,Math.max(1,b+a));document.getElementById('lr').textContent=(r*100).toFixed(1)+'%';document.getElementById('tlr').textContent=(tr*100).toFixed(1)+'%';document.getElementById('pf').textContent=f.toFixed(1)+'/10';const meta=(xa==='tlr')?D.meta:EX.meta;const bs_th=meta.threshold_pct/100;const cb_th=meta.cubic_threshold_pct/100;const primary_th=isNaN(cb_th)?bs_th:cb_th;const po=document.getElementById('po');const cv=xa==='tlr'?tr:r;if(cv<primary_th*0.7){{po.className='bd s';po.textContent='安全'}}else if(cv<primary_th){{po.className='bd s';po.style.background='#fef9e7';po.style.color='#f39c12';po.textContent='接近最大加速点'}}else if(cv<primary_th*1.3){{po.className='bd d';po.style.background='#fdedec';po.style.color='#e67e22';po.textContent='最大加速区间'}}else{{po.className='bd d';po.textContent='超越最大加速点'}}const bi=(xa==='lr'&&EX.binned)?EX.binned:D.binned;let below=0,tot=0;for(const p of(bi||[])){{tot+=p.n;const bx=p.x||p.loss_rate_mid;if(bx<=cv)below+=p.n}}document.getElementById('pc').textContent=tot>0?Math.round(below/tot*100)+'%':'--';dr()}}
up();document.querySelectorAll('#cr,#fl,#ls,input[name="xa"],input[name="fs"]').forEach(el=>el.addEventListener('input',up))
</script></body></html>"""

(ROOT / "index.html").write_text(H, encoding="utf-8")
print(f'index.html generated ({len(H)} bytes)')
