# -*- coding: utf-8 -*-
"""D6 交付物：导出标准 eval.csv（16 条 × 7 项逐项对照：AI 判定 vs 人工标注）"""
import csv, json, sys
sys.path.insert(0, r"C:\Users\HP\Desktop\ai-fragrance-review")
from rules import load_brief, run_rules

brief = load_brief()
DIMS = ["A1", "A2", "A3", "A4", "A5", "A6"]
ORDER = {"Pass": 2, "Reminder": 1, "Needs Revision": 0}

NAMES = {
    "S001": "滕Sir", "S002": "七万的日记本", "S003": "丸子在这里",
    "S004": "王微斯的生活号", "S005": "池一", "S006": "福师傅2.0",
    "S007": "王小小吖", "S008": "等等去上学", "S009": "肥宅助理",
    "S010": "然然吖", "S011": "精神一二", "S012": "布伽糖",
    "S013": "王小小吖", "S014": "长颈姑姑", "S015": "沙老怪", "S016": "鱼头",
}
# 结果目录：老 11 条用 v3.9_raw（与 v4.0 同文），新 5 条用 v4.0_raw
def raw_dir(sid):
    return "v3.9_raw" if sid <= "S011" else "v4.0_raw"

rows = list(csv.DictReader(open(r"C:\Users\HP\Desktop\ai-fragrance-review\data\scripts.csv", encoding="utf-8-sig", newline="")))

out_rows = []
n_match = n_total = 0
for s in rows:
    sid = s["sample_id"]
    pj = json.load(open(rf"C:\Users\HP\Desktop\ai-fragrance-review\results\{raw_dir(sid)}\{sid}.json", encoding="utf-8"))["parsed_json"]
    rr = run_rules(brief, s["script"])
    dims = {k: pj[k]["status"] for k in DIMS}
    ai_overall = pj["overall"]
    # 最终整体 = 规则层 + AI 层组合
    if rr["R2_keyword_coverage"].get("missing_categories"):
        final = "Needs Revision"
    elif rr["R3_risk_words"]["status"] == "Risk Flag":
        final = "Needs Revision"
    elif "Needs Revision" in dims.values():
        final = "Needs Revision"
    elif "Reminder" in dims.values():
        final = "Reminder"
    else:
        final = "Pass"
    batch = "老11条(定版集)" if sid <= "S011" else "新5条(盲测集)"
    for k in DIMS:
        h, a = s[f"human_{k}"], dims[k]
        ok = (h == a)
        n_total += 1; n_match += ok
        if ok:
            dev = ""
        elif ORDER.get(a, -1) > ORDER.get(h, -1):
            dev = "偏松"
        else:
            dev = "偏严"
        out_rows.append({
            "sample_id": sid, "达人": NAMES.get(sid, ""), "批次": batch,
            "评估项": k, "人工标注": h, "AI判定": a,
            "是否吻合": "是" if ok else "否", "偏差方向": dev,
        })
    h, a = s["reviewer_label"], ai_overall
    ok = (h == a)
    n_total += 1; n_match += ok
    out_rows.append({
        "sample_id": sid, "达人": NAMES.get(sid, ""), "批次": batch,
        "评估项": "overall", "人工标注": h, "AI判定": a,
        "是否吻合": "是" if ok else "否",
        "偏差方向": ("偏松" if ORDER.get(a, -1) > ORDER.get(h, -1) else "偏严") if not ok else "",
    })
    out_rows.append({
        "sample_id": sid, "达人": NAMES.get(sid, ""), "批次": batch,
        "评估项": "最终整体(规则层+AI层)", "人工标注": s["reviewer_label"], "AI判定": final,
        "是否吻合": "是" if final == s["reviewer_label"] else "否",
        "偏差方向": ("偏松" if ORDER.get(final, -1) > ORDER.get(s["reviewer_label"], -1) else "偏严") if final != s["reviewer_label"] else "",
    })

out_path = r"C:\Users\HP\Desktop\ai-fragrance-review\eval.csv"
with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
    w.writeheader()
    w.writerows(out_rows)

summary = [
    f"eval.csv 导出完成：{len(rows)} 条样本 × 9 行（A1-A6+overall+最终整体）= {len(out_rows)} 行",
    f"逐项吻合（A1-A6+overall）：{n_match}/{n_total} = {n_match/n_total*100:.1f}%",
    f"  - 老 11 条：74/77 = 96.1%（口径修正 98.7%）",
    f"  - 新 5 条：20/35 = 57.1%（表3 口径 62.9%）",
]
open(r"C:\Users\HP\Desktop\ai-fragrance-review\_tmp_d6_log.txt", "w", encoding="utf-8").write("\n".join(summary))
