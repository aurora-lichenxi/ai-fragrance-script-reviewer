# -*- coding: utf-8 -*-
"""导出 v4.0 新5条完整诊断结果（AI 层 A1-A6 + overall + human_review_items）"""
import json

out = open(r"C:\Users\HP\Desktop\ai-fragrance-review\v4_new5_full.txt", "w", encoding="utf-8")
NAMES = {
    "S012": "布伽糖（原子吐息）", "S013": "王小小吖", "S014": "长颈姑姑",
    "S015": "沙老怪的碎碎念", "S016": "鱼头的百宝袋",
}
DIMS = ["A1", "A2", "A3", "A4", "A5", "A6"]

for sid in ["S012", "S013", "S014", "S015", "S016"]:
    rec = json.load(open(rf"C:\Users\HP\Desktop\ai-fragrance-review\results\v4.0_raw\{sid}.json", encoding="utf-8"))
    pj = rec["parsed_json"]
    out.write(f"{'='*80}\n{sid} {NAMES[sid]}｜耗时 {rec['elapsed_sec']}s｜AI overall = {pj['overall']}\n{'='*80}\n")
    for k in DIMS:
        d = pj[k]
        out.write(f"\n【{k}】Status: {d.get('status')}\n")
        out.write(f"  Evidence: {d.get('evidence','')}\n")
        out.write(f"  Reason: {d.get('reason','')}\n")
        out.write(f"  Suggestion: {d.get('suggestion','')}\n")
    hri = pj.get("human_review_items", [])
    out.write(f"\n  human_review_items（{len(hri)} 项）:\n")
    for i, h in enumerate(hri, 1):
        out.write(f"    {i}. {h}\n")
    out.write("\n")
out.close()
print("done")
