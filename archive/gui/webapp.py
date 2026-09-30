# -*- coding: utf-8 -*-
"""
webapp.py — AI 香氛短视频内容诊断 · 本机网页界面
==================================================
由 app.py web 启动：python app.py web [--port 8501]

- 纯 Python 标准库实现（http.server），无第三方依赖
- 界面为本机临时页面：Key 保存在本机 .env，API 调用从本机直连 DashScope
- 程序不收集、不上传任何使用者数据
"""
from __future__ import annotations
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import app  # 复用 app.py 的诊断流程

ENV_PATH = app.ENV_PATH  # .env 始终在 exe/脚本旁边（用户 Key 持久化位置）

PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI香氛视频脚本诊断工具 1.0</title>
<style>
  :root { --line:#e5e7eb; --muted:#6b7280; --bg:#f9fafb; --accent:#1f2937; }
  * { box-sizing:border-box; }
  body { font-family:"Microsoft YaHei","PingFang SC",system-ui,sans-serif; margin:0;
         background:var(--bg); color:var(--accent); font-size:15px; }
  .wrap { max-width:860px; margin:0 auto; padding:32px 20px 60px; }
  h1 { font-size:22px; margin:0 0 6px; }
  .sub { color:var(--muted); font-size:13px; margin-bottom:22px; }
  .notice { background:#f0fdf4; border:1px solid #bbf7d0; color:#166534;
            border-radius:8px; padding:10px 14px; font-size:13px; margin-bottom:22px; }
  .card { background:#fff; border:1px solid var(--line); border-radius:10px;
          padding:18px 20px; margin-bottom:18px; }
  .card h2 { font-size:15px; margin:0 0 12px; }
  textarea { width:100%; height:180px; border:1px solid var(--line); border-radius:8px;
             padding:10px 12px; font-size:14px; resize:vertical; font-family:inherit; }
  textarea:focus { outline:2px solid #93c5fd; border-color:#93c5fd; }
  .row { display:flex; gap:10px; align-items:center; flex-wrap:wrap; }
  input[type=text], input[type=password] { border:1px solid var(--line); border-radius:8px;
             padding:8px 12px; font-size:14px; flex:1; min-width:220px; font-family:inherit; }
  button { background:var(--accent); color:#fff; border:none; border-radius:8px;
           padding:10px 22px; font-size:15px; cursor:pointer; font-family:inherit; }
  button:disabled { background:#9ca3af; cursor:not-allowed; }
  button.ghost { background:#fff; color:var(--accent); border:1px solid var(--line); }
  .hint { color:var(--muted); font-size:12.5px; }
  .status-ok { color:#166534; } .status-no { color:#b91c1c; } .status-warn { color:#b45309; }
  table { width:100%; border-collapse:collapse; font-size:14px; }
  th, td { border:1px solid var(--line); padding:8px 10px; text-align:left; vertical-align:top; }
  th { background:#f3f4f6; font-weight:600; white-space:nowrap; }
  .verdict { font-size:17px; font-weight:600; padding:12px 16px; border-radius:8px;
             display:inline-block; margin-top:4px; }
  .v-pass { background:#f0fdf4; color:#166534; }
  .v-rem  { background:#fffbeb; color:#b45309; }
  .v-nr   { background:#fef2f2; color:#b91c1c; }
  .detail { font-size:13px; color:#374151; }
  .muted { color:var(--muted); }
  #loading { display:none; color:var(--muted); font-size:14px; }
  #err { display:none; background:#fef2f2; color:#b91c1c; border:1px solid #fecaca;
         border-radius:8px; padding:10px 14px; font-size:14px; margin-bottom:18px; }
  .footer { color:var(--muted); font-size:12px; text-align:center; margin-top:30px; }
  select { border:1px solid var(--line); border-radius:6px; padding:4px 6px; font-size:13px;
           font-family:inherit; background:#fff; max-width:100%; }
  input.fbreason { width:100%; min-width:120px; border:1px solid var(--line); border-radius:6px;
           padding:4px 8px; font-size:13px; font-family:inherit; box-sizing:border-box; }
  .concl { background:#fef08a; padding:1px 5px; border-radius:4px; font-weight:600;
           color:#713f12; display:inline-block; }
  .hl-human { background:#fef08a; padding:2px 6px; border-radius:4px; }
</style>
</head>
<body>
<div class="wrap">
  <h1>AI香氛视频脚本诊断工具 1.0</h1>

  <div class="card" style="background:#f8fafc">
    <h2>工具介绍</h2>
    <div style="font-size:13.5px;line-height:1.8">
      <p style="margin:0 0 10px"><b>功能：</b>营销型短视频脚本大多结构高度重复（开场钩子、痛点、卖点、证据、行动号召、转化逻辑）。本工具代替人工初审这类脚本：按统一标准逐项检查重复的结构性内容，给出三档整体判定与具体修改建议，避免人工审核口径漂移、漏看错看。</p>
      <p style="margin:0 0 10px"><b>基本原理：</b>规则层与 AI 层分工。规则层（R1-R4）对必现词、禁用词等做字面硬匹配，判断确定、零误判；AI 语义层（A1-A6）基于产品 brief 由大模型理解脚本内容，逐维判断是否达标。两层结果合并，推导整体档位（通过 / 提醒修改 / 需修改）。</p>
      <p style="margin:0"><b>如何使用：</b>① 在下方卡片填写并保存 DashScope API Key（仅存本机）→ ② 粘贴产品 Brief，点「解析 Brief」自动生成结构化信息（缺少必需信息会提示补充）→ ③ 粘贴待审脚本，点「开始诊断」（约 30-60 秒）→ ④ 查看判定结果，可提交人工判定作为迭代依据。</p>
    </div>
  </div>

  <div class="notice">🔒 本程序完全在你自己的电脑上运行：API Key 保存在本机 .env 文件，诊断请求由本机直连阿里云 DashScope。程序不收集、不上传任何数据。</div>

  <div id="err"></div>

  <div class="card" id="keyCard">
    <h2>API Key（本机保存）</h2>
    <div class="row">
      <input type="password" id="apiKey" placeholder="DashScope API Key（sk-开头）">
      <button class="ghost" onclick="saveKey()">保存到本机</button>
    </div>
    <div class="hint" id="keyStatus" style="margin-top:8px">检查中…</div>
  </div>

  <div class="card" id="briefCard">
    <h2>输入 Brief 自动解析</h2>
    <div class="hint" style="margin-bottom:10px">粘贴产品 brief 原文（自由文本），AI 自动解析为结构化信息（品牌词、产品词、核心卖点、官方宣称、禁用边界等），缺少必需信息会提示补充；解析结果可逐项编辑确认，保存后即为人工确认 Brief——后续诊断将自动使用最新一份。</div>
    <textarea id="briefText" style="height:160px" placeholder="把产品 brief 原文粘贴到这里（运营文档、商详要点、卖点清单均可）…"></textarea>
    <div class="row" style="margin-top:12px">
      <button id="briefBtn" onclick="parseBrief()">解析 Brief</button>
      <span id="briefLoading" class="hint" style="display:none">解析中，约需 10-30 秒…</span>
    </div>
    <div id="briefResult" style="display:none;margin-top:14px">
      <div id="briefValid"></div>
      <div id="briefFields"></div>
      <div class="row" style="margin-top:12px">
        <button onclick="saveBriefDraft()">保存人工确认 Brief</button>
        <span id="briefMsg" class="hint"></span>
      </div>
    </div>
  </div>

  <div class="card">
    <h2>待审脚本</h2>
    <textarea id="script" placeholder="把抖音短视频口播脚本粘贴到这里…"></textarea>
    <div class="row" style="margin-top:12px">
      <button id="goBtn" onclick="diagnose()">开始诊断</button>
      <span id="loading">诊断中，约需 30-60 秒…</span>
    </div>
  </div>

  <div id="result" style="display:none">
    <div class="card"><h2>整体判定</h2><div id="verdict"></div>
      <div class="hint" id="verdictNote" style="margin-top:10px"></div></div>
    <div class="card"><h2>规则层检查（R1-R4，字面匹配）</h2><div id="rules"></div></div>
    <div class="card"><h2>AI 语义诊断（A1-A6）</h2><div id="dims"></div></div>
    <div class="card"><h2>提请人工复核（规则层 + AI 层事项汇总）</h2><div id="hri"></div></div>
    <div class="card"><h2>人工判定</h2>
      <div class="hint" style="margin-bottom:10px">在各规则（R1-R4）与维度（A1-A6）行内选择人工判定（与 AI 一致可不填理由；不一致建议填写理由，不强制——规则层命中固定搭配如『第一印象』时，可在此改判并说明）。提交后生成『人工审核表』（规则层 + AI 层机器判定与人工修改结果汇总），保存在本机 results/视频审核人工判定表格/，作为后续 prompt 迭代依据。</div>
      <div id="fbOverall"></div>
      <div class="row" style="margin-top:14px">
        <button onclick="submitFeedback()">提交人工判定</button>
        <span id="fbMsg" class="hint"></span>
      </div>
    </div>

    <div class="card" id="fbTableCard" style="display:none">
      <h2>人工审核表（本次提交）</h2>
      <div id="fbTable"></div>
      <div class="hint" id="fbTableNote" style="margin-top:8px"></div>
    </div>
  </div>

  <div class="card" style="background:#f8fafc">
    <h2>2.0 迭代方向：通用视频脚本 AI 诊断工具</h2>
    <div class="hint" style="margin-bottom:8px">迭代逻辑：把本工具从「香氛单品类」扩展为「任意产品可用的通用诊断工具」，四步闭环：</div>
    <table style="font-size:13.5px">
      <tr><td style="width:44px;text-align:center"><b>①</b></td><td><b>输入任何产品 brief</b>——自由文本粘贴，自动解析为结构化信息（1.0 已上线本能力），缺少必需信息自动提示补充；</td></tr>
      <tr><td style="text-align:center"><b>②</b></td><td><b>自动生成诊断 prompt</b>——按 brief 信息 + 已沉淀的结构化分析经验（六维判定核心规则）生成，支持人工核查与修改；</td></tr>
      <tr><td style="text-align:center"><b>③</b></td><td><b>两层分析</b>——规则层字面检查 + AI 六维语义判断，与 1.0 相同的双层架构；</td></tr>
      <tr><td style="text-align:center"><b>④</b></td><td><b>输出判断及建议 + 人工判定回流</b>——判定结果持续积累，用于校准新品类的判定口径，工具越用越准。</td></tr>
    </table>
  </div>

  <div class="footer">AI香氛视频脚本诊断工具 1.0（build 2026-09-28 00:35）· prompt v4.1 × qwen-plus（temperature=0）· 结果仅供审核参考，不构成最终裁定</div>
</div>

<script>
const V = {"Pass":["通过","v-pass"],"Reminder":["提醒修改","v-rem"],"Needs Revision":["需修改","v-nr"],
           "Complete":"通过","Present":"通过","Clear":"通过","Skipped":"跳过","Missing":"未通过","Risk Flag":"命中风险词","Invalid":"配置错误"};
// 规则层状态 → 三档映射（用于人工判定一致性比对；Skipped 不参与比对）
const RULE_STATUS_MAP = {"Complete":"Pass","Present":"Pass","Clear":"Pass",
                         "Missing":"Needs Revision","Risk Flag":"Needs Revision","Invalid":"Needs Revision"};
const RULE_KEYS = ["R1","R2","R3","R4"];
const DIM_NAMES = {
  "A1":"Hook · 开场钩子",
  "A2":"Pain Point · 痛点",
  "A3":"Solution & Selling Point · 方案与卖点",
  "A4":"Proof & Credibility · 证据与可信度",
  "A5":"CTA Quality · 行动号召质量",
  "A6":"Conversion Logic · 转化逻辑"
};
function ruleStatusOf(rl, k){
  if (!rl) return "";
  if (k==="R1") return (rl.R1_brief_complete||{}).status||"";
  if (k==="R2") return (rl.R2_keyword_coverage||{}).status||"";
  if (k==="R3") return (rl.R3_risk_words||{}).status||"";
  if (k==="R4") return (rl.R4_cta_present||{}).status||"";
  return "";
}
function escHtml(s){ return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }
function renderReason(txt){
  if (!txt || !String(txt).trim()) return "—";
  let lines = String(txt).split(/\\n+/).map(function(x){return x.trim();}).filter(function(x){return x;});
  if (lines.length===1){
    // 无换行（旧格式兼容）：在 ①②③/判断N：/位置核对/判定/组合 标记前断行
    let s = lines[0].replace(/(?=(?:[①②③④⑤]|判断[12]：|位置核对：|判定：|组合：))/g, "\\n");
    lines = s.split(/\\n+/).map(function(x){return x.trim();}).filter(function(x){return x;});
  }
  return lines.map(function(line){
    const m = line.match(/^([^：:]{1,24})[：:](.*)$/);
    if (m){
      return "<div style='margin:0 0 6px'><span class='concl'>"+escHtml(m[1])+"：</span>"+
             "<span class='detail'>"+escHtml(m[2])+"</span></div>";
    }
    return "<div class='detail' style='margin:0 0 6px'>"+escHtml(line)+"</div>";
  }).join("");
}
let lastResult = null, lastScript = "";

function statusOpts(){
  return "<option value=''>未判定</option>"+
    "<option value='Pass'>Pass</option>"+
    "<option value='Reminder'>Reminder</option>"+
    "<option value='Needs Revision'>Needs Revision</option>";
}
function fbCell(id){
  return "<select id='h-"+id+"'>"+statusOpts()+"</select>"+
         "<input type='text' class='fbreason' id='hr-"+id+"' placeholder='理由（不一致时建议填写）' style='margin-top:6px'>";
}

// ---- Brief 解析（阶段一）----
const BF_FIELDS = [
  ["category","商品分类","hard","text"],
  ["brand_words","品牌词（规范写法/简称）","hard","list"],
  ["product_words","产品词（必须出现的规范写法）","hard","list"],
  ["core_selling_points","核心卖点","hard","list"],
  ["official_claims","官方宣称（数据/技术口径）","soft","list"],
  ["banned_claims","禁用表述/宣称边界","soft","list"],
  ["target_audience","目标人群","soft","list"],
  ["scenes","使用场景","soft","list"],
  ["specs_price","规格与价格","soft","text"],
  ["cta_words","规定 CTA 词（可选）","soft","list"]
];
async function parseBrief(){
  const text = document.getElementById("briefText").value.trim();
  if (!text){ alert("请先粘贴 brief 原文"); return; }
  const btn = document.getElementById("briefBtn"); btn.disabled=true;
  document.getElementById("briefLoading").style.display="inline";
  document.getElementById("briefMsg").textContent="";
  try{
    const resp = await fetch("/api/parse_brief",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({text})});
    const r = await resp.json();
    if (!r.ok){ throw new Error(r.error||"解析失败"); }
    renderBrief(r);
  }catch(e){
    alert("Brief 解析失败："+e.message+"（若为 Key 问题，请先在上方配置 API Key）");
  }finally{
    btn.disabled=false; document.getElementById("briefLoading").style.display="none";
  }
}
function renderBrief(r){
  document.getElementById("briefResult").style.display="block";
  let vh = "";
  if (r.missing_hard.length){
    vh += "<div style='background:#fef2f2;border:1px solid #fecaca;color:#b91c1c;border-radius:8px;padding:10px 14px;font-size:13.5px;margin-bottom:8px'>"+
          "❗ 缺少必需信息（无法用于诊断，请在下方对应字段补充）："+r.missing_hard.join("、")+"</div>";
  } else {
    vh += "<div style='background:#f0fdf4;border:1px solid #bbf7d0;color:#166534;border-radius:8px;padding:10px 14px;font-size:13.5px;margin-bottom:8px'>"+
          "✅ 必需信息齐全</div>";
  }
  if (r.missing_soft.length){
    vh += "<div style='background:#fffbeb;border:1px solid #fde68a;color:#b45309;border-radius:8px;padding:10px 14px;font-size:13.5px'>"+
          "⚠️ 建议补充（缺失将降级运行）："+r.missing_soft.join("、")+
          (r.missing_soft.some(x=>x.indexOf("官方宣称")>=0||x.indexOf("禁用表述")>=0)
            ? "——缺少官方宣称/禁用表述时，A4 证据合规检查将只覆盖广告法通用风险，无法比对产品专属口径"
            : "")+"</div>";
  }
  document.getElementById("briefValid").innerHTML = vh;

  let fh = "<table><tr><th style='width:190px'>字段</th><th>抽取结果（可直接编辑；列表类每行一条）</th></tr>";
  for (const [key,name,lvl,type] of BF_FIELDS){
    const v = (r.parsed[key]!==undefined&&r.parsed[key]!==null)?r.parsed[key]:"";
    const shown = ((type==="list") ? (Array.isArray(v)?v.join("\\n"):"") : String(v))
                  .replace(/&/g,"&amp;").replace(/</g,"&lt;");
    const tag = lvl==="hard" ? "<span style='color:#b91c1c'> *</span>" : "";
    fh += "<tr><td>"+name+tag+"</td><td>"+
          (type==="list"
            ? "<textarea id='bf-"+key+"' rows='"+Math.max(2,Math.min(6,shown.split("\\n").length))+"' style='width:100%'>"+shown+"</textarea>"
            : '<input type="text" id="bf-'+key+'" value="'+shown.replace(/"/g,'&quot;')+'" style="width:100%" class="fbreason">')+
          "</td></tr>";
  }
  fh += "</table>";
  document.getElementById("briefFields").innerHTML = fh;
  document.getElementById("briefCard").scrollIntoView({behavior:"smooth"});
}
async function saveBriefDraft(){
  const draft = {};
  for (const [key,name,lvl,type] of BF_FIELDS){
    const el = document.getElementById("bf-"+key);
    if (!el) continue;
    if (type==="list"){
      draft[key] = el.value.split("\\n").map(x=>x.trim()).filter(x=>x);
    } else {
      draft[key] = el.value.trim();
    }
  }
  const msg = document.getElementById("briefMsg");
  msg.textContent = "保存中…";
  try{
    const resp = await fetch("/api/save_brief_draft",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({draft})});
    const r = await resp.json();
    if (!r.ok){ throw new Error(r.error||"保存失败"); }
    msg.textContent = "已保存人工确认 brief（"+r.file+"）。后续诊断将自动使用最新一份人工确认 brief。";
  }catch(e){
    msg.textContent = "保存失败："+e.message;
  }
}

async function loadStatus(){
  const el = document.getElementById("keyStatus");
  const controller = new AbortController();
  const timer = setTimeout(function(){ controller.abort(); }, 8000);
  try{
    const resp = await fetch("/api/status",{signal:controller.signal});
    clearTimeout(timer);
    const r = await resp.json();
    if (r.key_configured){
      el.innerHTML = "✅ 已配置（.env）· 模型：" + r.model + " · prompt：" + r.prompt + " · Brief：" + (r.brief_source||"—");
      el.className = "hint status-ok";
    } else {
      el.innerHTML = "❌ 未配置。请填写 DashScope API Key（<a href='https://bailian.console.aliyun.com/' target='_blank'>阿里云百炼</a> 可免费申请）";
      el.className = "hint status-no";
    }
  }catch(e){
    clearTimeout(timer);
    el.innerHTML = "⚠️ 无法连接本机服务（" + (e.name==="AbortError" ? "请求超时" : e.message) +
      "）。当前页面地址：" + location.host +
      "。请确认地址栏为 127.0.0.1:8501 且工具 exe 正在运行；旧标签页请关闭，点此 <a href='javascript:loadStatus()'>重试</a>，或按 Ctrl+F5 强制刷新。";
    el.className = "hint status-warn";
    setTimeout(loadStatus, 5000);
  }
}
async function saveKey(){
  const k = document.getElementById("apiKey").value.trim();
  if (!k){ alert("请先填写 Key"); return; }
  const r = await (await fetch("/api/save_key",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({key:k})})).json();
  if (r.ok){ alert("已保存到本机 .env"); loadStatus(); } else { alert("保存失败：" + r.error); }
}
function badge(s){
  const m = V[s];
  if (Array.isArray(m)) return "<span class='verdict "+m[1]+"' style='font-size:14px;padding:4px 12px'>"+s+"（"+m[0]+"）</span>";
  return s;
}
async function diagnose(){
  const script = document.getElementById("script").value.trim();
  const err = document.getElementById("err"); err.style.display="none";
  if (!script){ err.textContent="请先粘贴脚本文本"; err.style.display="block"; return; }
  const btn = document.getElementById("goBtn"); btn.disabled=true;
  document.getElementById("loading").style.display="inline";
  try{
    const resp = await fetch("/api/diagnose",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({script})});
    const r = await resp.json();
    if (!r.ok){ throw new Error(r.error||"诊断失败"); }
    render(r);
  }catch(e){
    err.textContent = "诊断失败：" + e.message + "（若为 Key 问题，请先在上方配置 API Key）";
    err.style.display="block";
  }finally{
    btn.disabled=false; document.getElementById("loading").style.display="none";
  }
}
function render(r){
  lastResult = r;
  lastScript = document.getElementById("script").value.trim();
  document.getElementById("result").style.display="block";
  const v = document.getElementById("verdict");
  const m = V[r.final_overall]||[r.final_overall,""];
  v.className = "verdict "+m[1]; v.textContent = r.final_overall+"（"+m[0]+"）";
  document.getElementById("verdictNote").textContent =
    "三档推导：R2 门槛缺失 / R3 命中 / 任一维度需修改 → 需修改；无『需修改』有『提醒』→ 提醒；全部通过 → 通过。耗时 "+r.elapsed_sec+" 秒。Brief："+(r.brief_source||"—");

  const rl = r.rule_layer;
  let r3detail = "未命中风险词";
  if (rl.R3_risk_words.hits.length){
    r3detail = rl.R3_risk_words.hits.map(function(h){
      const sents = (h.evidence_sentences && h.evidence_sentences.length)
        ? h.evidence_sentences : [h.evidence || h.word];
      return "『"+h.word+"』（"+h.description+"）——"+
             sents.map(function(x){ return "「"+x+"」"; }).join("　");
    }).join("<br>");
  }
  const rows = [
    ["R1","R1 Brief 确定性", rl.R1_brief_complete.status, rl.R1_brief_complete.errors ? rl.R1_brief_complete.errors.join("；") : "—"],
    ["R2","R2 关键词植入", rl.R2_keyword_coverage.status, rl.R2_keyword_coverage.missing_categories.length ? "缺失："+rl.R2_keyword_coverage.missing_categories.join("、") : "品牌词/产品词均命中"],
    ["R3","R3 禁用词扫描", rl.R3_risk_words.status, r3detail],
    ["R4","R4 CTA 词检查", rl.R4_cta_present.status, "cta_words 已清空，CTA 质量由 AI 层 A5 评估"],
  ];
  document.getElementById("rules").innerHTML = "<table><tr><th>规则</th><th>判定</th><th>说明</th><th style='width:160px'>人工判定</th></tr>"+
    rows.map(function(x){
      return "<tr><td>"+x[1]+"</td><td>"+badge(x[2])+"</td><td class='detail'>"+x[3]+"</td><td>"+fbCell(x[0])+"</td></tr>";
    }).join("")+"</table>";

  const dims = r.ai_layer;
  let html = "<table><tr><th style='width:110px'>维度</th><th style='width:120px'>判定</th>"+
             "<th>证据（脚本原文）</th><th>原因（分要点：高亮为结论）</th><th>建议（修改方向）</th><th style='width:160px'>人工判定</th></tr>";
  for (const k of ["A1","A2","A3","A4","A5","A6"]){
    const d = dims[k]||{};
    const ev   = ((d.evidence  ||"—").toString()).replace(/\\n/g," ").trim() || "—";
    const rsn  = renderReason(d.reason);
    const sugg = ((d.suggestion||"—").toString()).replace(/\\n/g," ").trim() || "—";
    html += "<tr><td><b>"+k+"</b><br><span class='muted' style='font-size:12px'>"+(DIM_NAMES[k]||"")+"</span></td>"+
            "<td>"+badge(d.status||"?")+"</td>"+
            "<td class='detail'>"+ev+"</td>"+
            "<td class='detail'>"+rsn+"</td>"+
            "<td class='detail'>"+sugg+"</td>"+
            "<td>"+fbCell(k)+"</td></tr>";
  }
  html += "</table><div class='hint' style='margin-top:8px'>AI 自报整体："+r.ai_overall+"（与三档规则推导"+
          (r.ai_overall===r.derived?"一致":"不一致")+"）</div>";
  document.getElementById("dims").innerHTML = html;

  document.getElementById("fbOverall").innerHTML =
    "<table><tr><th style='width:110px'>项目</th><th style='width:120px'>AI 判定</th><th style='width:160px'>人工判定</th><th>理由（可选）</th></tr>"+
    "<tr><td><b>整体判定</b><br><span class='muted' style='font-size:12px'>最终整体（规则层+AI 层）</span></td>"+
    "<td>"+badge(r.final_overall)+"</td>"+
    "<td><select id='h-OA'>"+statusOpts()+"</select></td>"+
    "<td><input type='text' class='fbreason' id='hr-OA' placeholder='不一致时建议填写理由'></td></tr></table>";

  const items = [];
  ((rl.R3_risk_words||{}).hits||[]).forEach(function(h){
    items.push("【规则层·R3】命中风险词『"+h.word+"』——"+(h.description||"")+"。请结合完整原句确认语境是否构成违规（固定搭配如『第一印象』不属极限用法，可在人工判定改判为通过；命中即整体判为需修改）。");
  });
  ((rl.R2_keyword_coverage||{}).missing_categories||[]).forEach(function(c){
    items.push("【规则层·R2】『"+c+"』未命中——请确认脚本是否确实未使用规范写法（口语简称不计入；缺失即整体判为需修改）。");
  });
  (r.human_review_items||[]).forEach(function(x){
    items.push("【AI 层登记】"+x);
  });
  document.getElementById("hri").innerHTML = items.length
    ? "<ol>"+items.map(function(x){return "<li class='detail'>"+x+"</li>";}).join("")+"</ol>"+
      "<div class='hint' style='margin-top:6px'>以上为规则层与 AI 语义层提交人工确认的事项汇总，请在下方完成人工判定。</div>"
    : "<div class='hint'>本轮无待人工确认事项</div>";

  document.getElementById("result").scrollIntoView({behavior:"smooth"});
}
async function submitFeedback(){
  if (!lastResult){ alert("请先完成一次诊断"); return; }
  const human = {};
  let warn = 0, n = 0;
  for (const k of ["A1","A2","A3","A4","A5","A6"]){
    const s = document.getElementById("h-"+k).value;
    if (!s) continue;
    const rsn = document.getElementById("hr-"+k).value.trim();
    const aiS = (lastResult.ai_layer[k]||{}).status;
    if (s!==aiS && !rsn) warn++;
    human[k] = {status:s, reason:rsn, ai_status:aiS};
    n++;
  }
  for (const k of RULE_KEYS){
    const el = document.getElementById("h-"+k);
    if (!el) continue;
    const s = el.value;
    if (!s) continue;
    const rsn = document.getElementById("hr-"+k).value.trim();
    const raw = ruleStatusOf(lastResult.rule_layer, k);
    const aiS = RULE_STATUS_MAP[raw] || null;  // Skipped / 未知 → null，不参与一致性比对
    if (aiS && s!==aiS && !rsn) warn++;
    human[k] = {status:s, reason:rsn, ai_status:aiS, rule_status:raw};
    n++;
  }
  const os = document.getElementById("h-OA").value;
  if (os){
    const orsn = document.getElementById("hr-OA").value.trim();
    if (os!==lastResult.final_overall && !orsn) warn++;
    human["overall"] = {status:os, reason:orsn, ai_status:lastResult.final_overall};
    n++;
  }
  if (!n){ alert("请先至少选择一处人工判定"); return; }
  let cmsg = "提交后将生成『人工审核表』（规则层 R1-R4 + AI 层 A1-A6 机器判定与人工修改结果汇总），并保存到本机 results/视频审核人工判定表格/（JSON + Markdown 各一份）。";
  if (warn){ cmsg = "有 "+warn+" 处与机器判定不一致但未填理由。\\n"+cmsg+"\\n仍要提交吗？"; }
  else { cmsg += "\\n确定提交吗？"; }
  if (!confirm(cmsg)) return;
  const msg = document.getElementById("fbMsg");
  msg.textContent = "提交中…";
  try{
    const resp = await fetch("/api/feedback",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({script:lastScript, ai:lastResult, human:human})});
    const rr = await resp.json();
    if (!rr.ok){ throw new Error(rr.error||"保存失败"); }
    msg.textContent = "已保存至本机 "+rr.file+"（与机器不一致 "+rr.mismatches+" 处）";
    renderReviewTable(human, rr);
  }catch(e){
    msg.textContent = "提交失败："+e.message;
  }
}

function renderReviewTable(human, rr){
  const rl = lastResult.rule_layer;
  const items = [];
  // 规则层 R1-R4：机器判定 = 原始状态（附三档等价）；人工判定/一致性/理由来自 human
  const ruleNames = {"R1":"R1 Brief 确定性","R2":"R2 关键词植入","R3":"R3 禁用词扫描","R4":"R4 CTA 词检查"};
  for (const k of RULE_KEYS){
    const raw = ruleStatusOf(rl, k);
    const eq = RULE_STATUS_MAP[raw] || null;
    const h = human[k] || {};
    items.push({name: k+" "+ruleNames[k], layer:"规则层", machine: raw+(eq?"（视同 "+eq+"）":""),
                hstat: h.status||"", reason: h.reason||""});
  }
  // AI 层 A1-A6
  for (const k of ["A1","A2","A3","A4","A5","A6"]){
    const h = human[k] || {};
    items.push({name: k+" "+(DIM_NAMES[k]||""), layer:"AI 层", machine: (lastResult.ai_layer[k]||{}).status||"",
                hstat: h.status||"", reason: h.reason||""});
  }
  // 整体判定
  const ho = human["overall"] || {};
  items.push({name: "整体判定（规则层+AI 层推导）", layer:"汇总", machine: lastResult.final_overall,
              hstat: ho.status||"", reason: ho.reason||""});

  let html = "<table><tr><th style='width:200px'>项目</th><th style='width:170px'>机器判定</th>"+
             "<th style='width:150px'>人工判定</th><th style='width:90px'>一致性</th><th>人工理由</th></tr>";
  for (const it of items){
    let hcell = it.hstat ? badge(it.hstat) : "<span class='muted'>未判定</span>";
    let agcell = "<span class='muted'>—</span>";
    if (it.hstat){
      // 与机器三档等价值比对
      const m = it.machine.match(/（视同 ([^）]+)）/);
      const mEq = m ? m[1] : it.machine;
      if (it.machine.indexOf("Skipped")>=0){ agcell = "<span class='muted'>跳过不比对</span>"; }
      else if (it.hstat===mEq){ agcell = "<span class='status-ok'>✓ 一致</span>"; hcell = "<span class='hl-human'>"+hcell+"</span>"; }
      else { agcell = "<span class='status-no'>✗ 不一致</span>"; hcell = "<span class='hl-human'>"+hcell+"</span>"; }
    }
    html += "<tr><td><b>"+escHtml(it.name)+"</b><br><span class='muted' style='font-size:12px'>"+it.layer+"</span></td>"+
            "<td>"+badge(it.machine)+"</td><td>"+hcell+"</td><td>"+agcell+"</td>"+
            "<td class='detail'>"+(it.reason?escHtml(it.reason):"<span class='muted'>—</span>")+"</td></tr>";
  }
  html += "</table>";
  document.getElementById("fbTable").innerHTML = html;
  document.getElementById("fbTableNote").textContent =
    "已保存："+rr.file+"（JSON，含完整诊断原文）与同名 .md（本表格 Markdown 版）——作为后续 prompt 迭代依据。";
  document.getElementById("fbTableCard").style.display = "block";
  document.getElementById("fbTableCard").scrollIntoView({behavior:"smooth"});
}
loadStatus();
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # 静默访问日志
        pass

    # ---- helpers ----
    def _send(self, code: int, body: bytes, ctype: str):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")  # 禁止浏览器缓存，避免旧页面残留
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code: int = 200):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    # ---- GET ----
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
        elif self.path == "/api/status":
            self._json({
                "ok": True,
                "key_configured": bool(app.ENV.get("QWEN_API_KEY")),
                "model": app.ENV.get("QWEN_MODEL", "qwen-plus"),
                "prompt": app.DEFAULT_PROMPT,
                "brief_source": app.load_active_brief()[1],
            })
        else:
            self._json({"ok": False, "error": "not found"}, 404)

    # ---- POST ----
    def do_POST(self):
        if self.path == "/api/save_key":
            data = self._body()
            key = (data.get("key") or "").strip()
            if not key.startswith("sk-"):
                self._json({"ok": False, "error": "Key 应以 sk- 开头"}, 400)
                return
            lines = []
            if ENV_PATH.exists():
                for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
                    if not line.strip().startswith("QWEN_API_KEY"):
                        lines.append(line)
            else:
                lines = ["QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1",
                         "QWEN_MODEL=qwen-plus", "QWEN_TIMEOUT=120"]
            lines = ["QWEN_API_KEY=" + key] + [l for l in lines]
            ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
            app.ENV = app.load_env()  # 热更新
            self._json({"ok": True})
        elif self.path == "/api/diagnose":
            data = self._body()
            script = (data.get("script") or "").strip()
            if not script:
                self._json({"ok": False, "error": "脚本文本为空"}, 400)
                return
            import traceback
            try:
                rec = app.diagnose_script(script)
            except Exception:  # noqa: BLE001
                err = traceback.format_exc()
                try:
                    (app.APP_DIR / "webapp_error.log").write_text(err, encoding="utf-8")
                except OSError:
                    pass
                self._json({"ok": False, "error": "诊断异常，详见 webapp_error.log"}, 500)
                return
            if rec.get("status") != "ok":
                err = f"{rec.get('error_kind')}: {rec.get('error', '')}"
                if rec.get("error_kind") == "missing_key":
                    err = "尚未配置 API Key：请在上方『API Key（本机保存）』卡片填写 DashScope Key 并保存，再重新诊断。"
                try:
                    (app.APP_DIR / "webapp_error.log").write_text(err, encoding="utf-8")
                except OSError:
                    pass
                self._json({"ok": False, "error": err[:200]}, 500)
                return
            self._json({
                "ok": True,
                "final_overall": rec["final_overall"],
                "ai_overall": rec["ai_overall"],
                "brief_source": rec.get("brief_source", ""),
                "derived": app.derive_final_overall(rec["rule_layer"], rec["ai_dims"]),
                "rule_layer": rec["rule_layer"],
                "ai_layer": rec["ai_layer"],
                "human_review_items": rec["ai_layer"].get("human_review_items") or [],
                "elapsed_sec": rec["elapsed_sec"],
            })
        elif self.path == "/api/feedback":
            data = self._body()
            script = (data.get("script") or "").strip()
            human = data.get("human") or {}
            ai = data.get("ai") or {}
            if not script:
                self._json({"ok": False, "error": "脚本文本为空"}, 400)
                return
            if not human:
                self._json({"ok": False, "error": "未包含任何人工判定"}, 400)
                return
            mismatches = []
            ai_layer = ai.get("ai_layer") or {}
            # 规则层状态 → 三档等价映射（与前端 RULE_STATUS_MAP 一致；Skipped 不比对）
            RULE_EQUIV = {"Complete": "Pass", "Present": "Pass", "Clear": "Pass",
                          "Missing": "Needs Revision", "Risk Flag": "Needs Revision",
                          "Invalid": "Needs Revision"}
            rl = ai.get("rule_layer") or {}
            rule_status = {
                "R1": (rl.get("R1_brief_complete") or {}).get("status"),
                "R2": (rl.get("R2_keyword_coverage") or {}).get("status"),
                "R3": (rl.get("R3_risk_words") or {}).get("status"),
                "R4": (rl.get("R4_cta_present") or {}).get("status"),
            }
            for k in ("A1", "A2", "A3", "A4", "A5", "A6"):
                h = human.get(k) or {}
                a_s = (ai_layer.get(k) or {}).get("status")
                if h.get("status") and a_s and h["status"] != a_s:
                    mismatches.append({"item": k, "ai": a_s, "human": h["status"],
                                       "reason": h.get("reason", "")})
            for k in ("R1", "R2", "R3", "R4"):
                h = human.get(k) or {}
                a_s = RULE_EQUIV.get(rule_status.get(k) or "")
                if h.get("status") and a_s and h["status"] != a_s:
                    mismatches.append({"item": k, "ai": a_s, "human": h["status"],
                                       "reason": h.get("reason", "")})
            ho = human.get("overall") or {}
            if ho.get("status") and ai.get("final_overall") and ho["status"] != ai["final_overall"]:
                mismatches.append({"item": "overall", "ai": ai["final_overall"],
                                   "human": ho["status"], "reason": ho.get("reason", "")})
            from datetime import datetime
            fb_dir = app.APP_DIR / "results" / "视频审核人工判定表格"
            fb_dir.mkdir(parents=True, exist_ok=True)
            fname = "FB-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".json"
            record = {
                "saved_at": datetime.now().isoformat(timespec="seconds"),
                "script": script,
                "ai_result": ai,
                "human": human,
                "mismatches": mismatches,
            }
            (fb_dir / fname).write_text(json.dumps(record, ensure_ascii=False, indent=2),
                                        encoding="utf-8")

            # ---- 同步生成人工审核表（Markdown 版，与 JSON 同名） ----
            RULE_EQUIV_MD = {"Complete": "Pass", "Present": "Pass", "Clear": "Pass",
                             "Missing": "Needs Revision", "Risk Flag": "Needs Revision",
                             "Invalid": "Needs Revision"}
            rl_md = ai.get("rule_layer") or {}
            ai_md = ai.get("ai_layer") or {}
            md_rows = []
            rule_names = {"R1": "R1 Brief 确定性", "R2": "R2 关键词植入",
                          "R3": "R3 禁用词扫描", "R4": "R4 CTA 词检查"}
            rule_raw = {
                "R1": (rl_md.get("R1_brief_complete") or {}).get("status") or "",
                "R2": (rl_md.get("R2_keyword_coverage") or {}).get("status") or "",
                "R3": (rl_md.get("R3_risk_words") or {}).get("status") or "",
                "R4": (rl_md.get("R4_cta_present") or {}).get("status") or "",
            }
            dim_names = {"A1": "Hook · 开场钩子", "A2": "Pain Point · 痛点",
                         "A3": "Solution & Selling Point · 方案与卖点",
                         "A4": "Proof & Credibility · 证据与可信度",
                         "A5": "CTA Quality · 行动号召质量",
                         "A6": "Conversion Logic · 转化逻辑"}
            for k in ("R1", "R2", "R3", "R4"):
                raw = rule_raw.get(k) or ""
                h = human.get(k) or {}
                md_rows.append((f"{k} {rule_names[k]}", "规则层", raw, h, RULE_EQUIV_MD.get(raw)))
            for k in ("A1", "A2", "A3", "A4", "A5", "A6"):
                h = human.get(k) or {}
                md_rows.append((f"{k} {dim_names[k]}", "AI 层",
                                (ai_md.get(k) or {}).get("status") or "", h, None))
            ho = human.get("overall") or {}
            md_rows.append(("整体判定（规则层+AI 层推导）", "汇总",
                            ai.get("final_overall") or "", ho, None))

            def _md_cell(s: str) -> str:
                return str(s).replace("|", "\\|").replace("\n", " ") if s else "—"

            md_lines = [f"# 人工审核表 · {record['saved_at']}", "",
                        "| 项目 | 层级 | 机器判定 | 人工判定 | 一致性 | 人工理由 |",
                        "|---|---|---|---|---|---|"]
            for name, layer, machine, h, equiv in md_rows:
                hs = h.get("status") or ""
                if not hs:
                    agree = "—（未判定）"
                elif equiv:  # 规则层有三档等价值 → 按等价值比对
                    agree = "✓ 一致" if hs == equiv else "✗ 不一致"
                elif layer == "规则层":  # Skipped 等无比对值 → 不比对
                    agree = "—（跳过不比对）"
                else:  # AI 层 / 汇总 → 直接与机器档位比对
                    agree = "✓ 一致" if hs == machine else "✗ 不一致"
                md_lines.append("| " + " | ".join([
                    _md_cell(name), layer, _md_cell(machine), _md_cell(hs),
                    agree, _md_cell(h.get("reason", ""))]) + " |")
            md_lines += ["", f"与机器判定不一致：{len(mismatches)} 处",
                         "", "## 脚本原文", "", "> " + script.replace("\n", "\n> "), ""]
            md_name = fname.replace(".json", ".md")
            (fb_dir / md_name).write_text("\n".join(md_lines), encoding="utf-8")

            self._json({"ok": True, "file": "results/视频审核人工判定表格/" + fname,
                        "md_file": "results/视频审核人工判定表格/" + md_name,
                        "mismatches": len(mismatches)})
        elif self.path == "/api/parse_brief":
            data = self._body()
            text = (data.get("text") or "").strip()
            if not text:
                self._json({"ok": False, "error": "brief 原文为空"}, 400)
                return
            import traceback
            try:
                res = app.parse_brief_text(text)
            except Exception:  # noqa: BLE001
                err = traceback.format_exc()
                try:
                    (app.APP_DIR / "webapp_error.log").write_text(err, encoding="utf-8")
                except OSError:
                    pass
                self._json({"ok": False, "error": "解析异常，详见 webapp_error.log"}, 500)
                return
            if not res.get("ok"):
                err = res.get("error", "")
                if res.get("kind") == "missing_key":
                    err = "尚未配置 API Key：请先在上方『API Key（本机保存）』卡片填写并保存。"
                self._json({"ok": False, "error": str(err)[:200]}, 500)
                return
            self._json({
                "ok": True,
                "parsed": res["parsed"],
                "missing_hard": res["missing_hard"],
                "missing_soft": res["missing_soft"],
            })
        elif self.path == "/api/save_brief_draft":
            data = self._body()
            draft = data.get("draft") or {}
            if not draft:
                self._json({"ok": False, "error": "Brief 内容为空"}, 400)
                return
            from datetime import datetime
            bd_dir = app.APP_DIR / "results" / "产品brief人工审核版"
            bd_dir.mkdir(parents=True, exist_ok=True)
            fname = "BRIEF-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".json"
            record = {
                "saved_at": datetime.now().isoformat(timespec="seconds"),
                "draft": draft,
            }
            (bd_dir / fname).write_text(json.dumps(record, ensure_ascii=False, indent=2),
                                        encoding="utf-8")
            self._json({"ok": True, "file": "results/产品brief人工审核版/" + fname})
        else:
            self._json({"ok": False, "error": "not found"}, 404)


def make_handler():
    return Handler


if __name__ == "__main__":
    import webbrowser
    port = 8501
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"网页版已启动：http://127.0.0.1:{port}（Ctrl+C 退出）")
    webbrowser.open(f"http://127.0.0.1:{port}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已退出")
