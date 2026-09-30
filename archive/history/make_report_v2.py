# -*- coding: utf-8 -*-
"""
make_report_v2.py — 第 5 轮报告生成（Prompt v2 全量 11 条）

结构对齐 PromptV1-Result.md：
- 头部元信息 + 总览大表
- 11 条 × 三表（Rule-based Check / AI Semantic Diagnosis / 判定总结）
- 总体成绩（三档）
- 逐维度 AI vs 人工对照（速查 + 统计 + 详细对照：人工判定依据 vs AI 理由原文）
- 本轮观察
"""
from __future__ import annotations
import csv
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(r"C:\Users\HP\Desktop\ai-fragrance-review")
sys.path.insert(0, str(PROJECT_ROOT))

from rules import load_brief, run_rules, find_keyword_evidence  # noqa: E402

BRIEF = load_brief()
SCRIPTS_CSV = PROJECT_ROOT / "data" / "scripts.csv"
V2_RAW = PROJECT_ROOT / "results" / "v2_raw"
OUT_MD = Path(r"C:\Users\HP\Desktop\工作文件记录\PromptV2-Result.md")
DOCX_TABLES_JSON = Path(r"C:\Users\HP\Desktop\工作文件记录\_human_docx_tables.json")

DIMS = ["A1", "A2", "A3", "A4", "A5", "A6"]

CREATOR_NAMES = {
    "S001": "滕Sir", "S002": "七万的日记本", "S003": "丸子在这里",
    "S004": "王微斯的生活号", "S005": "池一", "S006": "福师傅2.0",
    "S007": "王小小吖", "S008": "等等去上学", "S009": "肥宅助理",
    "S010": "然然吖", "S011": "精神一二",
}

AI_DIM_NAMES = {
    "A1": "A1 开头钩子（Hook）", "A2": "A2 痛点共鸣（Pain Point）",
    "A3": "A3 解决方案与卖点（Solution & Selling Point）",
    "A4": "A4 证明与可信度（Proof & Credibility）",
    "A5": "A5 CTA 质量（CTA Quality）",
    "A6": "A6 转化逻辑（Conversion Logic）",
}
DOCX_ROW_NAMES = {
    "A1": "A1 强钩子开场", "A2": "A2 痛点引入", "A3": "A3 解决方案与核心卖点",
    "A4": "A4 事实证明与合规边界", "A5": "A5 CTA 质量", "A6": "A6 转化逻辑",
}

ABBR = {"Pass": "P", "Reminder": "Rem", "Needs Revision": "NR"}
ORDER = {"Pass": 2, "Reminder": 1, "Needs Revision": 0}


def md_cell(t):
    s = (t or "").strip()
    s = s.replace("|", "\\|").replace("\r", " ").replace("\n", " ")
    return s if s else "—"


# ---------- 人工 docx 判定总结（表3）提取 ----------
import docx  # noqa: E402

if not DOCX_TABLES_JSON.exists():
    d = docx.Document(r"C:\Users\HP\Desktop\终版人工Review_新增Script11版.docx")
    tables = [[[c.text.strip() for c in row.cells] for row in t.rows] for t in d.tables]
    DOCX_TABLES_JSON.write_text(json.dumps(tables, ensure_ascii=False, indent=1), encoding="utf-8")
else:
    tables = json.loads(DOCX_TABLES_JSON.read_text(encoding="utf-8"))

human_notes = {}  # sid -> {dim: note}
for i in range(11):
    sid = f"S{i+1:03d}"
    t = tables[3 * i + 2]
    human_notes[sid] = {}
    for row in t[1:]:
        proj, note = row[0], row[2]
        for k in DIMS:
            if proj.startswith(DOCX_ROW_NAMES[k]):
                human_notes[sid][k] = note

# ---------- 读取样本 ----------
with open(SCRIPTS_CSV, encoding="utf-8-sig", newline="") as f:
    samples = list(csv.DictReader(f))


def compute_final_overall(rr, dim_status):
    if rr["R2_keyword_coverage"].get("missing_categories", []):
        return "Needs Revision"
    if rr["R3_risk_words"]["status"] == "Risk Flag":
        return "Needs Revision"
    if any(v == "Needs Revision" for v in dim_status.values()):
        return "Needs Revision"
    if any(v == "Reminder" for v in dim_status.values()):
        return "Reminder"
    return "Pass"


def ai_overall_logic_ok(dim_status, ai_overall):
    if any(v == "Needs Revision" for v in dim_status.values()):
        return ai_overall == "Needs Revision"
    if any(v == "Reminder" for v in dim_status.values()):
        return ai_overall == "Reminder"
    return ai_overall == "Pass"


R2_BRAND_WORDS = ["网易严选"]
R2_PRODUCT_WORDS = ["香氛", "香薰", "除味香氛", "倒置香氛"]
R3_WORDS_TEXT = (
    "极限类（世界级、国家级、第一、唯一、首个）、"
    "违禁权威性（国家xx机关推荐、质量无需检测、官方认证、央视推荐）、"
    "疑似医疗用语（可治疗精神疾病、疗愈、根治、医疗级、治疗、处方）"
)


def r2_evidence_text(script):
    parts = []
    brand_hit = next((w for w in R2_BRAND_WORDS if w in script), None)
    if brand_hit:
        parts.append(f"核心品牌词命中“{brand_hit}”：{find_keyword_evidence(script, brand_hit, 15)}。")
    else:
        parts.append(f"核心品牌词“网易严选”未命中。脚本相关原句：{script[:40]}。")
    product_hit = next((w for w in R2_PRODUCT_WORDS if w in script), None)
    if product_hit:
        parts.append(f"核心产品词命中“{product_hit}”：{find_keyword_evidence(script, product_hit, 15)}。")
    else:
        parts.append(f"核心产品词未命中。脚本相关原句：{script[:40]}。")
    return "".join(parts)


def r3_evidence_text(r3):
    if r3["status"] == "Clear":
        return f"全文逐字扫描未出现规定禁用词：{R3_WORDS_TEXT}。"
    return "；".join(
        f"命中“{h['word']}”（{h['description']}）：{h['evidence']}" for h in r3.get("hits", [])
    )


# ---------- 汇总 ----------
rows = []
for s in samples:
    sid = s["sample_id"]
    script = s["script"]
    human = s["reviewer_label"]
    human_dims = {k: s.get(f"human_{k}", "") for k in DIMS}

    rr = run_rules(BRIEF, script)
    rec = json.loads((V2_RAW / f"{sid}.json").read_text(encoding="utf-8"))
    pj = rec.get("parsed_json") or {}
    ai_overall = pj.get("overall", "?")
    hri = pj.get("human_review_items", [])
    dims = {k: pj.get(k) or {} for k in DIMS}
    dim_status = {k: dims[k].get("status", "?") for k in DIMS}

    final = compute_final_overall(rr, dim_status)
    rows.append({
        "sid": sid, "creator": CREATOR_NAMES.get(sid, ""), "chars": len(script),
        "human": human, "human_dims": human_dims, "script": script,
        "rr": rr, "dims": dim_status, "dims_full": dims,
        "ai_overall": ai_overall, "final": final,
        "align": "✅" if final == human else "❌",
        "hri": hri, "elapsed": rec.get("elapsed_sec"),
        "logic_ok": ai_overall_logic_ok(dim_status, ai_overall),
    })

N = len(rows)
lines = []

# ============ 头部 ============
lines.append("# PromptV2-Result —— qwen-plus × Prompt v2 × brief v2.3 全量结果（第 5 轮）")
lines.append("")
lines.append("网易严选倒置香氛｜11 条短视频脚本机器 Review")
lines.append("")
lines.append("D2 小样本机器诊断｜Rule R1-R4 + AI A1-A6 + 判定总结")
lines.append("")
lines.append("说明：规则层（R1-R4）只按预设词表做字面匹配，判定只有 Pass / Needs Revision（R4 词表已清空，本轮 Skipped）；"
             "AI 层（A1-A6）做语义诊断，三档判定。v2 Prompt 按《promptv1-badcase分析-人工核查修改版》落地："
             "判定总原则 6 条（显式文字/禁辩护/维度隔离/促销要素排除/同类同判/先依据后档位）+ A1 双要素 + A2 显式痛点句与位置 + "
             "A3 两层判断（方案对应/卖点覆盖）+ A4 两层判断（证据有无/逐 claim 合规比对+转译边界）+ A5 词级锚定 + A6 环节链先行。")
lines.append("")
lines.append("| 项目 | 内容 |")
lines.append("|---|---|")
lines.append("| 测试日期 | 2026-09-26（第 5 轮全量，11 条） |")
lines.append("| 模型 | qwen-plus（阿里云 DashScope，OpenAI 兼容模式，temperature=0） |")
lines.append("| Prompt | **v2**：判定总原则 6 条 + A1-A6 逐维度三档操作定义 + A3/A4 两层判断结构 + reason 结构化格式要求 |")
lines.append("| Brief | **v2.3**：注入 AI 的只有 content_reference；R2 强制门槛为品牌词+产品词；R4 空；R3 风险词调优版 |")
lines.append("| 样本 | 11 条（`data/scripts.csv`）；人工对照：《终版人工Review_新增Script11版.docx》 |")
lines.append("| 整体判定 | 三档组合：R2 门槛缺失/R3 命中/A1–A6 任一 NR → Needs Revision；无 NR 有 Reminder → Reminder；全 Pass → Pass |")
lines.append("| 原始输出 | `results/v2_raw/S001.json`~`S011.json` |")
lines.append("")
lines.append("**版本变化（第 4 轮 v1.3 → 第 5 轮 v2）**：A1-A6 每维写入 Pass/Reminder/NR 三档操作定义；A3/A4 改为两层判断（判断1+判断2+组合规则）；新增判定总原则（只依据显式文字、禁止辩护、维度间不传导、促销要素排除出判定、同类同判）；A3/A4/A6 reason 结构化（判断1/判断2/组合 或 环节链先行）。")
lines.append("")
lines.append("---")
lines.append("")

# ============ 总览 ============
lines.append("## 总览（Rule R1-R4 + AI A1-A6 + 三档整体判定）")
lines.append("")
lines.append("**缩写**：NR = Needs Revision，Rem = Reminder，P = Pass")
lines.append("")
lines.append("| ID | 达人 | 字数 | 人工整体 | R1 | R2 | R3 | R4 | A1 | A2 | A3 | A4 | A5 | A6 | AI整体 | 最终整体 | 对齐 |")
lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for r in rows:
    d = r["dims"]
    rr = r["rr"]
    r3s = "⚠ Flag" if rr["R3_risk_words"]["status"] == "Risk Flag" else "Clear"
    r4s = rr["R4_cta_present"]["status"]
    r2s = rr["R2_keyword_coverage"]["status"]
    lines.append(
        f"| {r['sid']} | {r['creator']} | {r['chars']} | {r['human']} | {rr['R1_brief_complete']['status']} | {r2s} | {r3s} | {r4s} | "
        f"{ABBR.get(d['A1'], d['A1'])} | {ABBR.get(d['A2'], d['A2'])} | {ABBR.get(d['A3'], d['A3'])} | "
        f"{ABBR.get(d['A4'], d['A4'])} | {ABBR.get(d['A5'], d['A5'])} | {ABBR.get(d['A6'], d['A6'])} | "
        f"{ABBR.get(r['ai_overall'], r['ai_overall'])} | {ABBR.get(r['final'], r['final'])} | {r['align']} |"
    )
lines.append("")
lines.append("---")
lines.append("")

# ============ 逐条三表 ============
lines.append("## 逐条诊断（表1 Rule-based Check ＋ 表2 AI Semantic Diagnosis ＋ 表3 判定总结）")
lines.append("")
lines.append("> 三张表结构与《终版人工Review_新增Script11版.docx》一致，方便逐条对照、思考 Prompt 修改方向。")
lines.append("")

for i, r in enumerate(rows, 1):
    rr = r["rr"]
    r1, r2, r3, r4 = rr["R1_brief_complete"], rr["R2_keyword_coverage"], rr["R3_risk_words"], rr["R4_cta_present"]
    d = r["dims_full"]

    lines.append(f"### {i}. {r['creator']}（{r['sid']}，{r['chars']} 字｜人工整体：{r['human']}｜最终整体：{r['final']} {r['align']}）")
    lines.append("")

    lines.append("表 1｜Rule-based Check（R1-R4）")
    lines.append("")
    lines.append("| Rule | 判定 | 检查结果 / 证据 |")
    lines.append("|---|---|---|")
    lines.append("| R1 Brief 确定性检查 | Pass | 固定 Product Brief（v2.3）已完成 R1 检查；R1 评估 Brief，不重复评价单条 Script。 |")
    r2_verdict = "Pass" if r2["status"] == "Present" else "Needs Revision"
    lines.append(f"| R2 关键词植入检查 | {r2_verdict} | {r2_evidence_text(r['script'])} |")
    r3_verdict = "Pass" if r3["status"] == "Clear" else "Needs Revision"
    lines.append(f"| R3 禁用词扫描 | {r3_verdict} | {r3_evidence_text(r3)} |")
    lines.append("| R4 CTA 词检查 | Skipped | cta_words 已清空（v2.1，本次香薰诊断不做 CTA 词检查）；CTA 的质量判断由 AI 层 A5 承担。 |")
    lines.append("")

    lines.append("表 2｜AI Semantic Diagnosis（A1-A6）")
    lines.append("")
    lines.append("| AI 诊断维度 | Status | Evidence | Reason | Suggestion |")
    lines.append("|---|---|---|---|---|")
    for k in DIMS:
        dd = d[k]
        lines.append(f"| {AI_DIM_NAMES[k]} | {dd.get('status', '?')} | {md_cell(dd.get('evidence'))} | {md_cell(dd.get('reason'))} | {md_cell(dd.get('suggestion'))} |")
    lines.append("")

    lines.append("表 3｜判定总结")
    lines.append("")
    lines.append("| 项目 | 判定 | 机器核查及建议 |")
    lines.append("|---|---|---|")
    issues = []
    if r2["status"] == "Missing":
        issues.append("R2 关键词植入检查：脚本没有完整命中 R2 固定词要求（缺品牌词/产品词）；请在不改变内容含义的前提下补入缺失的固定关键词。")
    if r3["status"] == "Risk Flag":
        for h in r3.get("hits", []):
            issues.append(f"R3 禁用词扫描：命中“{h['word']}”（{h['description']}）；请替换或删除该表述。")
    for k in DIMS:
        if r["dims"][k] == "Needs Revision":
            sg = (d[k].get("suggestion") or "").replace("|", "\\|").replace("\n", " ")
            issues.append(f"{AI_DIM_NAMES[k]}：{sg or '见 AI 诊断建议。'}")
    if not issues:
        rem_items = []
        for k in DIMS:
            if r["dims"][k] == "Reminder":
                sg = (d[k].get("suggestion") or "").replace("|", "\\|").replace("\n", " ")
                rem_items.append(f"{AI_DIM_NAMES[k]}：{sg or '见 AI 诊断建议。'}")
        issues = rem_items if rem_items else ["各项检查均通过。"]
    overall_note = "；".join(issues)
    lines.append(f"| 整体 | {r['final']} | {overall_note} |")

    lines.append("| Rule 1 Brief 确定性检查 | Pass | 固定 Brief 已完成检查，不需对单条脚本重复核查。 |")
    r2_note = ("脚本原句同时命中“网易严选”和至少一个规定产品词，R2 通过。"
               if r2["status"] == "Present" else
               "脚本没有完整命中 R2 固定词要求；请补入缺失的固定关键词。")
    lines.append(f"| Rule 2 关键词植入检查 | {r2_verdict} | {r2_note} |")
    lines.append(f"| Rule 3 禁用词扫描 | {r3_verdict} | {'未命中规定禁用词，R3 无需修改。' if r3['status'] == 'Clear' else '命中规定禁用词，需替换或删除。'} |")
    lines.append("| Rule 4 CTA 词检查 | Skipped | cta_words 已清空，本轮跳过；CTA 质量由 A5 评估。 |")
    for k in DIMS:
        sg = (d[k].get("suggestion") or "—").replace("|", "\\|").replace("\n", " ")
        note = sg if sg != "—" else "无明显修改必要。"
        lines.append(f"| {AI_DIM_NAMES[k]} | {r['dims'][k]} | {note} |")
    hri_txt = "；".join(r["hri"]) if r["hri"] else "—"
    lines.append("")
    lines.append(f"**AI 自报 overall**：{r['ai_overall']}（与三档规则推导{'一致' if r['logic_ok'] else '不一致'}）　|　**human_review_items**：{hri_txt}　|　**耗时** {r['elapsed']}s")
    lines.append("")
    lines.append("---")
    lines.append("")

# ============ 总体成绩 ============
lines.append("## 总体成绩（三档）")
lines.append("")
ok = sum(1 for r in rows if r["align"] == "✅")
ai_ok = sum(1 for r in rows if r["ai_overall"] == r["human"])
nr_human = [r for r in rows if r["human"] == "Needs Revision"]
rem_human = [r for r in rows if r["human"] == "Reminder"]
nr_ok = [r for r in nr_human if r["final"] == "Needs Revision"]
rem_ok = [r for r in rem_human if r["final"] == "Reminder"]
nr_down = [r for r in nr_human if r["final"] == "Reminder"]
rem_up = [r for r in rem_human if r["final"] == "Needs Revision"]
logic_ok_n = sum(1 for r in rows if r["logic_ok"])
lines.append("| 指标 | 数值 |")
lines.append("|---|---|")
lines.append(f"| **最终整体（规则层+AI 层组合）与人工一致率** | **{ok} / {N}（{round(ok*100/N)}%）** |")
lines.append(f"| AI 层 overall 单独与人工一致率 | {ai_ok} / {N}（{round(ai_ok*100/N)}%） |")
lines.append(f"| AI 自报 overall 与三档规则推导一致性 | **{logic_ok_n} / {N}** |")
lines.append(f"| 人工 NR {len(nr_human)} 条，最终判 NR（召回） | **{len(nr_ok)} / {len(nr_human)}（{round(len(nr_ok)*100/len(nr_human))}%）** |")
lines.append(f"| 人工 NR 被降档为 Reminder（漏判） | {len(nr_down)} 条（{'、'.join(r['sid'] for r in nr_down) or '—'}） |")
lines.append(f"| 人工 Reminder {len(rem_human)} 条，最终判 Reminder（精确） | **{len(rem_ok)} / {len(rem_human)}（{round(len(rem_ok)*100/len(rem_human))}%）** |")
lines.append(f"| 人工 Reminder 被升档为 NR（过严） | {len(rem_up)} 条（{'、'.join(r['sid'] for r in rem_up) or '—'}） |")
lines.append("")
lines.append("---")
lines.append("")

# ============ 逐维度对照（速查+统计+详细） ============
lines.append("## 逐维度 AI vs 人工对照（A1-A6）")
lines.append("")
lines.append("**一致 = 档位完全相同；松 = AI 高于人工（P＞Rem＞NR）；严 = AI 低于人工**")
lines.append("")
lines.append("### 速查总表")
lines.append("")
lines.append("| ID | A1 | A2 | A3 | A4 | A5 | A6 |")
lines.append("|---|---|---|---|---|---|---|")
for r in rows:
    cells = []
    for k in DIMS:
        h, a = r["human_dims"][k], r["dims"][k]
        if h == a:
            tag = "✅"
        elif ORDER.get(a, -1) > ORDER.get(h, -1):
            tag = "↑松"
        else:
            tag = "↓严"
        cells.append(f"{ABBR.get(h, h)}/{ABBR.get(a, a)}{tag}")
    lines.append(f"| {r['sid']} {r['creator']} | " + " | ".join(cells) + " |")
lines.append("")
lines.append("### 维度一致率统计")
lines.append("")
lines.append("| 维度 | 一致 | 偏松 | 偏严 | 一致率 |")
lines.append("|---|---|---|---|---|")
for k in DIMS:
    same = sum(1 for r in rows if r["human_dims"][k] == r["dims"][k])
    loose = sum(1 for r in rows if ORDER.get(r["dims"][k], -1) > ORDER.get(r["human_dims"][k], -1))
    strict = sum(1 for r in rows if ORDER.get(r["dims"][k], -1) < ORDER.get(r["human_dims"][k], -1))
    lines.append(f"| {AI_DIM_NAMES[k]} | {same} | {loose} | {strict} | **{round(same*100/N)}%** |")
lines.append("")
lines.append("### 详细对照（人工判定与依据 vs AI判定与理由）")
lines.append("")
lines.append("> 人工判断取自《终版人工Review_新增Script11版.docx》各脚本表3「判定总结」中对应维度行；")
lines.append("> AI 判断取自本轮 qwen-plus 输出（Prompt v2 × brief v2.3）对应维度的 Status 与 Reason 原文。")
lines.append("")
for k in DIMS:
    lines.append(f"#### {AI_DIM_NAMES[k]}")
    lines.append("")
    lines.append("| 样本 | 人工判定 | AI判定 | 对照 | 人工判断（docx 判定总结·原文） | AI判断理由（本轮输出·原文） |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for r in rows:
        h = r["human_dims"][k]
        a = r["dims"][k]
        if h == a:
            mark = "✅ 一致"
        elif ORDER.get(a, -1) > ORDER.get(h, -1):
            mark = "↑ AI偏松"
        else:
            mark = "↓ AI偏严"
        note = human_notes.get(r["sid"], {}).get(k, "")
        reason = r["dims_full"][k].get("reason", "")
        lines.append(
            f"| {r['sid']} {r['creator']} | **{h}** | **{a}** | {mark} | {md_cell(note)} | {md_cell(reason)} |"
        )
    lines.append("")

lines.append("---")
lines.append("")

# ============ 本轮观察 ============
lines.append("## 本轮观察（第 5 轮，Prompt v2 + brief v2.3）")
lines.append("")
lines.append("### ✅ 进步")
lines.append("")
lines.append("1. **偏松问题全部消除**：第 4 轮 16 处偏松分歧（AI 给高了档位）本轮全部归零——A4 判断 2 逐 claim 合规比对生效，S011『清除抑郁/加薪』首次判出 Needs Revision（人工 NR，连续两轮漏判后修复）；A5 词级锚定生效，S004『链接有活动，你们点开』与 S011 同型表述本轮同判（S004=Pass）。")
lines.append("2. **两层判断结构被执行**：A3/A4 的 reason 均按『判断1→判断2→组合』输出，卖点覆盖、证据逐条比对过程可见、可核查。")
lines.append("3. **AI 自报 overall 与三档推导 11/11 一致**（连续第三轮）。")
lines.append("4. **维度间传导被抑制**：A6 未再因 A5=Reminder 而判 NR 的『Reminder 当断点』错误；A2 缺失未再把 A3 拖到 Needs Revision（A3 无 NR，全部为 Reminder/Pass）。")
lines.append("5. **促销要素退出判定**：全轮 reason 中价格锚点/规格引导不再作为扣档理由（只出现在 suggestion）。")
lines.append("")
lines.append("### ❌ 新问题：全面过严")
lines.append("")
lines.append("1. **方向反转过头**：66 项维度判定中偏松 0 项、偏严 27 项——上一轮的『辩护倾向』被『禁止辩护』纠正后，模型转向吹毛求疵。整体一致率持平 5/11，但错误结构从『漏判+过严并存』变为『单边过严』。")
lines.append("2. **A4 判断 2 的 NR 面扩大化（8 处偏严）**：细微字面差异被升级为 NR 级『篡改/越界』——S003 把『99.9%』vs brief『>99.9%』记为『数值篡改』、『去味』vs『祛味』记为『擅自简写』、『回家一喷』记为『虚假使用场景』；S010『调香大师』身份背书被记 NR 级（人工口径=一般越界 Rem）。『涉及身心健康因果才 NR』的边界被模型泛化成『凡与 brief 不完全一致即 NR』。")
lines.append("3. **A3 判断 1 被 A2 拖累（9 处偏严，一致率 18%）**：『A2 缺失时判断 1 最多 Reminder』本意是防 A2 传导 NR，模型却执行成『A2 有问题→判断 1=Reminder』——A2 全偏严（5 处）后，A3 判断 1 连带全部 Reminder。人工口径：方案本身对应卖点即可 Pass，链完整与否的宽容度比模型执行的高。")
lines.append("4. **A2 位置检查执行过严（5 处偏严）**：『痛点出现较晚』的判定标准被收紧（S001 人工只对痛点中置记 Rem，模型对更多前置场景也扣档）。")
lines.append("5. **A5 锚例『链接有活动，你们点开=Pass』生效**（S004 对了），但『一定要试试』『姐妹们可以来试试看』本应 Rem，S007/S009 判了 NR——Rem 档的泛动词边界仍没收住。")
lines.append("")
lines.append("### 结论")
lines.append("")
lines.append("v2 的结构层改动全部生效（两层判断、转译边界、促销排除、维度隔离、锚例同判），**偏松清零、S011 修复、判定过程可核查**——证明 badcase 分析的方向正确。但三档边界文案的『严格度』整体校准过猛：A4 判断 2 的 NR 触发条件需要收窄回『仅身心健康因果/医疗暗示』，字面微差与口语化表述归 Reminder；A3 判断 1 的『最多 Reminder』需改为『方案在 brief 内且覆盖≥1 卖点即 Pass，链缺失仅在方案无法对应卖点时才降档』；A2 位置与 A5 泛动词档位需再校准。下一轮（v2.1）的重点是**回调严格度**，而非继续加规则。")
lines.append("")
lines.append("---")
lines.append("")
lines.append("*生成方式：`rules.py`（本地规则层）+ `results/v2_raw/*.json`（qwen-plus，Prompt v2）合并生成；生成脚本 `make_report_v2.py`。人工对照：《终版人工Review_新增Script11版.docx》（2026-09-26）。*")

OUT_MD.write_text("\n".join(lines), encoding="utf-8")
print(f"已生成：{OUT_MD}")
print(f"共 {N} 条样本")
print(f"最终整体一致率：{ok}/{N}（{round(ok*100/N)}%）")
print(f"AI overall 一致率：{ai_ok}/{N}")
print(f"AI overall 逻辑一致：{logic_ok_n}/{N}")
for k in DIMS:
    same = sum(1 for r in rows if r["human_dims"][k] == r["dims"][k])
    print(f"  {k} 一致 {same}/{N}")
