"""
make_report_v1.py — 第 4 轮报告生成（对齐人工 Review 文档的三表呈现格式）

每条样本按人工 docx《终版人工Review_新增Script11版》的结构呈现三张表：
- 表 1｜Rule-based Check（R1-R4）：| Rule | 判定 | 检查结果 / 证据 |
- 表 2｜AI Semantic Diagnosis（A1-A6）：| AI 诊断维度 | Status | Evidence | Reason | Suggestion |
- 表 3｜判定总结：| 项目 | 判定 | 机器核查及建议 |

规则层判定只有 Pass / Needs Revision（R4 空配为 Skipped）——规则层只识别
规定词汇的『有/无』，不存在模糊情况（Reminder）。
整体判定（三档）= 规则层 + AI 层组合：
- Needs Revision：R2 品牌/产品词缺失，或 R3 命中风险词，或 A1-A6 任一 Needs Revision
- Reminder：无 NR，但 A1-A6 出现 Reminder
- Pass：A1-A6 全部 Pass 且规则层无缺失/命中
"""
from __future__ import annotations
import csv
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from rules import load_brief, run_rules, find_keyword_evidence  # noqa: E402

BRIEF = load_brief()
SCRIPTS_CSV = PROJECT_ROOT / "data" / "scripts.csv"
V1_RAW = PROJECT_ROOT / "results" / "v1_raw"
OUT_MD = Path(r"C:\Users\HP\Desktop\工作文件记录\PromptV1-Result.md")

DIMS = ["A1", "A2", "A3", "A4", "A5", "A6"]

# 达人名（与《终版人工Review_新增Script11版.docx》顺序一致）
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

# ---------- 读取 11 条样本 ----------
with open(SCRIPTS_CSV, encoding="utf-8-sig", newline="") as f:
    samples = list(csv.DictReader(f))

ABBR = {"Pass": "P", "Reminder": "Rem", "Needs Revision": "NR"}


def compute_final_overall(rr: dict, dim_status: dict) -> str:
    """三档最终判定：规则层（R2 门槛/R3）+ AI 层（A1-A6）组合"""
    missing = rr["R2_keyword_coverage"].get("missing_categories", [])
    if missing:  # v2.3 起 R2 仅剩品牌/产品两类，均为门槛
        return "Needs Revision"
    if rr["R3_risk_words"]["status"] == "Risk Flag":
        return "Needs Revision"
    if any(v == "Needs Revision" for v in dim_status.values()):
        return "Needs Revision"
    if any(v == "Reminder" for v in dim_status.values()):
        return "Reminder"
    return "Pass"


def ai_overall_logic_ok(dim_status: dict, ai_overall: str) -> bool:
    if any(v == "Needs Revision" for v in dim_status.values()):
        return ai_overall == "Needs Revision"
    if any(v == "Reminder" for v in dim_status.values()):
        return ai_overall == "Reminder"
    return ai_overall == "Pass"


# ---------- 规则层 R2/R3 证据文本（模仿人工 Review 的证据格式）----------

R2_BRAND_WORDS = ["网易严选"]
R2_PRODUCT_WORDS = ["香氛", "香薰", "除味香氛", "倒置香氛"]

R3_WORDS_TEXT = (
    "极限类（世界级、国家级、第一、唯一、首个）、"
    "违禁权威性（国家xx机关推荐、质量无需检测、官方认证、央视推荐）、"
    "疑似医疗用语（可治疗精神疾病、疗愈、根治、医疗级、治疗、处方）"
)


def r2_evidence_text(script: str) -> str:
    parts = []
    brand_hit = next((w for w in R2_BRAND_WORDS if w in script), None)
    if brand_hit:
        parts.append(f"核心品牌词命中“{brand_hit}”：{find_keyword_evidence(script, brand_hit, 15)}。")
    else:
        # 取脚本开头一句作相关原句
        head = script[:40].replace("\n", " ")
        parts.append(f"核心品牌词“网易严选”未命中。脚本相关原句：{head}。")
    product_hit = next((w for w in R2_PRODUCT_WORDS if w in script), None)
    if product_hit:
        parts.append(f"核心产品词命中“{product_hit}”：{find_keyword_evidence(script, product_hit, 15)}。")
    else:
        head = script[:40].replace("\n", " ")
        parts.append(f"核心产品词未命中。脚本相关原句：{head}。")
    return "".join(parts)


def r3_evidence_text(r3: dict) -> str:
    if r3["status"] == "Clear":
        return f"全文逐字扫描未出现规定禁用词：{R3_WORDS_TEXT}。"
    hits = "；".join(
        f"命中“{h['word']}”（{h['description']}）：{h['evidence']}" for h in r3.get("hits", [])
    )
    return hits


# ---------- 汇总数据 ----------
rows = []
for s in samples:
    sid = s["sample_id"]
    script = s["script"]
    human = s["reviewer_label"]
    human_dims = {k: s.get(f"human_{k}", "") for k in DIMS}

    rr = run_rules(BRIEF, script)
    rec = json.loads((V1_RAW / f"{sid}.json").read_text(encoding="utf-8"))
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

# ============================================================
# 头部元信息
# ============================================================
lines.append("# PromptV1-Result —— qwen-plus × Prompt v1.3 × brief v2.3 全量结果（第 4 轮）")
lines.append("")
lines.append("网易严选倒置香氛｜11 条短视频脚本机器 Review")
lines.append("")
lines.append("D2 小样本机器诊断｜Rule R1-R4 + AI A1-A6 + 判定总结")
lines.append("")
lines.append("说明：规则层（R1-R4）只按预设词表做字面匹配，识别规定词汇的『有/无』，"
             "判定只有 Pass / Needs Revision（R4 词表已清空，本轮 Skipped），不存在模糊情况（Reminder）；"
             "AI 层（A1-A6）做语义诊断，判定 Pass / Reminder / Needs Revision 三档。"
             "Rule 检查结果与 AI Evidence 均引用可定位到原脚本的具体句子；A4 负责产品事实、检测数据与 Claim 是否符合 Product Brief。")
lines.append("")
lines.append("| 项目 | 内容 |")
lines.append("|---|---|")
lines.append("| 测试日期 | 2026-09-26（第 4 轮全量，11 条） |")
lines.append("| 模型 | qwen-plus（阿里云 DashScope，OpenAI 兼容模式，temperature=0） |")
lines.append("| Prompt | **v1.3**：两层分工声明（规则层由系统执行，AI 不复述 R2/R3/R4）；A1–A6 维度定义修订版；三档整体判定规则写入正文 |")
lines.append("| Brief | **v2.3**：注入 AI 的只有 content_reference（rule_config 不再对 AI 可见）；R2 强制门槛收窄为品牌词+产品词两类（与人工 Review 口径一致）；R4 cta_words 空；R3 风险词调优版 |")
lines.append("| 样本 | 11 条（`data/scripts.csv`，S011 新增）；人工对照：《终版人工Review_新增Script11版.docx》 |")
lines.append("| 整体判定 | 三档组合：R2 门槛缺失/R3 命中/A1–A6 任一 NR → Needs Revision；无 NR 有 Reminder → Reminder；全 Pass → Pass |")
lines.append("| 原始输出 | `results/v1_raw/S001.json`~`S011.json`（历史轮次备份：`v1_raw_prev/`第1轮、`v1_raw_r2/`第2轮、`v1_raw_r3/`第3轮） |")
lines.append("")
lines.append("**版本变化（第 3 轮 → 第 4 轮）**：① Prompt 增加两层分工声明，AI 不再复述规则层检查；② 注入 AI 的 brief 剔除 rule_config（第 3 轮发现 AI 在 A5 判定中引用 R4 配置越位参与语义判断）；③ R2 收窄为品牌词+产品词（brief v2.3）。")
lines.append("")
lines.append("---")
lines.append("")

# ============================================================
# 总览大表
# ============================================================
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

# ============================================================
# 每条样本：三表结构（对齐人工 docx）
# ============================================================
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

    # ---- 表 1 Rule-based Check ----
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

    # ---- 表 2 AI Semantic Diagnosis ----
    lines.append("表 2｜AI Semantic Diagnosis（A1-A6）")
    lines.append("")
    lines.append("| AI 诊断维度 | Status | Evidence | Reason | Suggestion |")
    lines.append("|---|---|---|---|---|")
    for k in DIMS:
        dd = d[k]
        ev = (dd.get("evidence") or "—").replace("|", "\\|").replace("\n", " ")
        rs_ = (dd.get("reason") or "—").replace("|", "\\|").replace("\n", " ")
        sg = (dd.get("suggestion") or "—").replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {AI_DIM_NAMES[k]} | {dd.get('status', '?')} | {ev} | {rs_} | {sg} |")
    lines.append("")

    # ---- 表 3 判定总结 ----
    lines.append("表 3｜判定总结")
    lines.append("")
    lines.append("| 项目 | 判定 | 机器核查及建议 |")
    lines.append("|---|---|---|")

    # 整体行：组合判定 + 主要问题汇总（NR 项列出建议；Reminder 项列出建议；全 Pass 才写通过）
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

# ============================================================
# 总体成绩
# ============================================================
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

# ============================================================
# 逐维度对照
# ============================================================
lines.append("## 逐维度 AI vs 人工对照（A1-A6）")
lines.append("")
lines.append("**一致 = 档位完全相同；松 = AI 高于人工（P＞Rem＞NR）；严 = AI 低于人工**")
lines.append("")
ORDER = {"Pass": 2, "Reminder": 1, "Needs Revision": 0}
lines.append("| ID | A1 人/AI | A2 人/AI | A3 人/AI | A4 人/AI | A5 人/AI | A6 人/AI |")
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
lines.append("| 维度 | 一致 | 偏松 | 偏严 | 一致率 |")
lines.append("|---|---|---|---|---|")
for k in DIMS:
    same = sum(1 for r in rows if r["human_dims"][k] == r["dims"][k])
    loose = sum(1 for r in rows if ORDER.get(r["dims"][k], -1) > ORDER.get(r["human_dims"][k], -1))
    strict = sum(1 for r in rows if ORDER.get(r["dims"][k], -1) < ORDER.get(r["human_dims"][k], -1))
    lines.append(f"| {k} | {same} | {loose} | {strict} | **{round(same*100/N)}%** |")
lines.append("")
lines.append("---")
lines.append("")

# ============================================================
# 问题分析
# ============================================================
lines.append("## 本轮观察（第 4 轮，Prompt v1.3 + brief v2.3）")
lines.append("")
lines.append("### ✅ 进步")
lines.append("")
lines.append("1. **两层分工声明生效**：全轮 AI 输出中未再出现引用 rule_config/R4 配置的内容（第 3 轮 S001/S010 的 A5 reason 均引用了 R4 cta_words 清空），human_review_items 也未再塞入 R2/R3/R4 自查结果。")
lines.append("2. **AI 自报 overall 与三档推导 100% 一致**（连续第二轮），整体判定规则稳定执行。")
lines.append("3. **S009 首次出现整体 Pass**（AI 层），说明剔除 rule_config 后模型不再被『清空的 R4』提示牵引从严；同时该条被规则层 R2（缺品牌词）正确拉回 Needs Revision——两层互补按设计工作。")
lines.append("4. **R2 收窄后规则层与人工口径对齐**：11 条中规则层仅 S009（缺品牌词）判 NR，与人工 R2 判定完全一致（11/11）。")
lines.append("")
lines.append("### ❌ 仍存在的问题")
lines.append("")
lines.append("1. **A5 判定口径再次摆动**：第 3 轮 A5 从不判 NR（漏 S002/S006/S008），本轮 A5 出现 4 次 NR（S003/S004/S007/S008），其中 S004/S007 人工只判 Reminder（脚本有『点开链接有活动』『一定要试试』，人工认为泛行动导向=Reminder，AI 判无明确动作=NR）。A5 三档标准缺失导致的摆动依旧。")
lines.append("2. **A4 仍未判出 S011 的 NR**：『清除抑郁的情绪』『摆三天老板加薪』超 Brief 因果宣称，AI 连续两轮只给 Reminder。『超出 Brief 的功效/因果宣称 = NR』这条边界仍未建立。")
lines.append("3. **S003 仍被判 NR（人工 Reminder）**：短脚本要素缺失从严的倾向未根治。")
lines.append("4. **逐维度一致率仍低**（A5 5/11、A6 6/11、A4 6/11）：无维度内三档标准，模型每轮松严漂移——这是 v2 Prompt 需要解决的核心问题。")
lines.append("")
lines.append("### 结论")
lines.append("")
lines.append("结构层（两层分工、三档整体判定、R2 口径）已全部就位且稳定；**当前误差几乎全部来自维度内三档标准缺失**（A4 因果宣称边界、A5 行动指令档位、短脚本从宽原则）。v2 Prompt 的重点是把 A1–A6 每维的 Pass/Reminder/NR 判定标准逐条写进正文。")
lines.append("")
lines.append("---")
lines.append("")
lines.append("*生成方式：`rules.py`（本地规则层）+ `results/v1_raw/*.json`（qwen-plus，Prompt v1.3）合并生成；生成脚本 `make_report_v1.py`。人工对照：《终版人工Review_新增Script11版.docx》（2026-09-26）。*")

OUT_MD.write_text("\n".join(lines), encoding="utf-8")
print(f"已生成：{OUT_MD}")
print(f"共 {N} 条样本")
print(f"最终整体一致率：{ok}/{N}（{round(ok*100/N)}%）")
print(f"AI overall 一致率：{ai_ok}/{N}")
print(f"AI overall 逻辑一致：{logic_ok_n}/{N}")
for k in DIMS:
    same = sum(1 for r in rows if r["human_dims"][k] == r["dims"][k])
    print(f"  {k} 一致 {same}/{N}")
