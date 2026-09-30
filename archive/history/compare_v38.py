# -*- coding: utf-8 -*-
"""Compare v3.8 full-run results against human labels (11 scripts x 7 items)."""
import json

HUMAN = r"C:\Users\HP\Desktop\ai-fragrance-review\data\human_labels.json"
RES_DIR = r"C:\Users\HP\Desktop\ai-fragrance-review\results\v3.8_raw"

# script order: 1滕Sir=S001 ... 11精神一二=S011
order = ["滕Sir", "七万的日记本", "丸子在这里", "王微斯的生活号", "池一",
         "福师傅2.0", "王小小吖", "等等去上学", "肥宅助理", "然然吖", "精神一二"]
human = json.load(open(HUMAN, encoding="utf-8"))
DIMS = ["A1", "A2", "A3", "A4", "A5", "A6"]

total = match = 0
dim_match = {d: [0, 0] for d in DIMS}
overall_match = [0, 0]
rows = []
for i, name in enumerate(order, 1):
    sid = f"S{i:03d}"
    h = human[name]
    ai = json.load(open(f"{RES_DIR}\\{sid}.json", encoding="utf-8"))["parsed_json"]
    cells = []
    for d in DIMS:
        hv, av = h["dims"][d], ai[d]["status"]
        ok = hv == av
        total += 1
        match += ok
        dim_match[d][0] += ok
        dim_match[d][1] += 1
        cells.append(f"{d}:{'✓' if ok else f'{av}≠{hv}'}")
    hv, av = h["overall"], ai["overall"]
    ok = hv == av
    total += 1
    match += ok
    overall_match[0] += ok
    overall_match[1] += 1
    n_ok = sum(1 for c in cells if "✓" in c) + ok
    rows.append(f"{sid} {name}: {' '.join(cells)} | overall:{'✓' if ok else f'{av}≠{hv}'} | {n_ok}/7")

print("\n".join(rows))
print()
for d in DIMS:
    m, t = dim_match[d]
    print(f"{d}: {m}/{t}")
print(f"overall: {overall_match[0]}/{overall_match[1]}")
print(f"\nTOTAL: {match}/{total} = {match/total*100:.1f}%")
