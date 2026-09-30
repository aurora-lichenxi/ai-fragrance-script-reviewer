# -*- coding: utf-8 -*-
"""Parse human review docx text -> per-script A1-A6 + overall human labels."""
import re
import json

TXT = r"C:\Users\HP\Desktop\ai-fragrance-review\data\human_review_text.txt"
OUT = r"C:\Users\HP\Desktop\ai-fragrance-review\data\human_labels.json"

lines = [l.rstrip() for l in open(TXT, encoding="utf-8")]

# Script blocks: lines like '1. 滕Sir' (title must start with a CJK char, number 1-11)
heads = [
    (i, l)
    for i, l in enumerate(lines)
    if re.match(r"^\d{1,2}\.\s*[一-龥]", l) and 1 <= int(re.match(r"^(\d{1,2})\.", l).group(1)) <= 11
]
print("script headers:", [h[1] for h in heads])

DIMS = ["A1", "A2", "A3", "A4", "A5", "A6"]
results = {}
for bi, (i, h) in enumerate(heads):
    end = heads[bi + 1][0] if bi + 1 < len(heads) else len(lines)
    block = lines[i:end]
    try:
        t2 = next(j for j, l in enumerate(block) if l.startswith("表 2"))
    except StopIteration:
        t2 = 0
    dims = {}
    for d in DIMS:
        for j in range(t2, len(block)):
            if block[j].startswith(d + " "):
                dims[d] = block[j + 1].strip()
                break
    overall = ""
    for j, l in enumerate(block):
        if l.strip() == "整体":
            overall = block[j + 1].strip()
            break
    name = h.split(".", 1)[1].strip()
    results[name] = {"dims": dims, "overall": overall}

for k, v in results.items():
    dims_str = " ".join(d + "=" + v["dims"].get(d, "?") for d in DIMS)
    print(k, "|", dims_str, "| overall =", v["overall"])

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("saved ->", OUT)
