# -*- coding: utf-8 -*-
"""新 5 条（S012-S016）v4.0 vs 人工标注吻合率统计"""
import csv, json, sys
sys.path.insert(0, r"C:\Users\HP\Desktop\ai-fragrance-review")
from rules import load_brief, run_rules

brief = load_brief()
DIMS = ["A1", "A2", "A3", "A4", "A5", "A6"]
ORDER = {"Pass": 2, "Reminder": 1, "Needs Revision": 0}
ABBR = {"Pass": "P", "Reminder": "Rem", "Needs Revision": "NR"}

rows = list(csv.DictReader(open(r"C:\Users\HP\Desktop\ai-fragrance-review\data\scripts.csv", encoding="utf-8-sig", newline="")))
targets = [r for r in rows if r["sample_id"] in {"S012", "S013", "S014", "S015", "S016"}]

total = match = 0
dim_match = {d: [0, 0] for d in DIMS}
overall_match = [0, 0]
final_match = [0, 0]
lines = []
for s in targets:
    sid = s["sample_id"]
    pj = json.load(open(rf"C:\Users\HP\Desktop\ai-fragrance-review\results\v4.0_raw\{sid}.json", encoding="utf-8"))["parsed_json"]
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
    r2s = rr["R2_keyword_coverage"]["status"]
    r3s = "Flag" if rr["R3_risk_words"]["status"] == "Risk Flag" else "Clear"

    cells = []
    n_ok = 0
    for k in DIMS:
        h, a = s[f"human_{k}"], dims[k]
        ok = h == a
        total += 1; match += ok
        dim_match[k][0] += ok; dim_match[k][1] += 1
        n_ok += ok
        if ok:
            tag = "OK"
        elif ORDER.get(a, -1) > ORDER.get(h, -1):
            tag = f"{ABBR[a]}!={ABBR[h]} 松"
        else:
            tag = f"{ABBR[a]}!={ABBR[h]} 严"
        cells.append(f"{k}:{tag}")
    h, a = s["reviewer_label"], ai_overall
    ok = h == a
    total += 1; match += ok
    overall_match[0] += ok; overall_match[1] += 1
    n_ok += ok
    fok = final == s["reviewer_label"]
    final_match[0] += fok; final_match[1] += 1
    lines.append(f"{sid}: R2={r2s} R3={r3s} | {' '.join(cells)} | overall:{'OK' if ok else f'{ABBR.get(a,a)}!={ABBR.get(h,h)}'} | 最终整体:{final}{' OK' if fok else f' !=人工{ABBR.get(s[chr(114)+chr(101)+chr(118)+chr(105)+chr(101)+chr(119)+chr(101)+chr(114)+chr(95)+chr(108)+chr(97)+chr(98)+chr(101)+chr(108)],s['reviewer_label'])}'} | {n_ok}/7")

print("\n".join(lines))
print()
for k in DIMS:
    m, t = dim_match[k]
    print(f"{k}: {m}/{t}")
print(f"AI overall: {overall_match[0]}/{overall_match[1]}")
print(f"最终整体(规则+AI): {final_match[0]}/{final_match[1]}")
print(f"\nTOTAL 逐项(A1-A6+overall): {match}/{total} = {match/total*100:.1f}%")
