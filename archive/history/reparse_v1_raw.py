"""
reparse_v1_raw.py — 一次性后处理
对 results/v1_raw/S*.json 用容错解析器重新解析 content，
回写 parsed_json 字段（不重调 API）。
"""
import json
from pathlib import Path

RAW_DIR = Path(r"C:\Users\HP\Desktop\ai-fragrance-review\results\v1_raw")

STRUCT_AFTER_CLOSE = {",", "}", "]", ":"}


def repair_json_text(s: str) -> str:
    out = []
    i = 0
    n = len(s)
    in_str = False
    esc = False
    while i < n:
        ch = s[i]
        if not in_str:
            if ch == '"':
                in_str = True
            out.append(ch)
            i += 1
            continue
        if esc:
            out.append(ch)
            esc = False
            i += 1
            continue
        if ch == "\\":
            out.append(ch)
            esc = True
            i += 1
            continue
        if ch == '"':
            j = i + 1
            while j < n and s[j] in " \t\r\n":
                j += 1
            if j >= n or s[j] in STRUCT_AFTER_CLOSE:
                out.append(ch)
                in_str = False
            else:
                out.append('\\"')
            i += 1
            continue
        if ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def tolerant_parse(text: str):
    s = text.strip()
    if s.startswith("```"):
        nl = s.find("\n")
        if nl > 0:
            s = s[nl + 1:]
        end = s.rfind("```")
        if end > 0:
            s = s[:end]
    s = s.strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    try:
        return json.loads(repair_json_text(s))
    except json.JSONDecodeError as e:
        print(f"  [repair failed] {e.msg} pos {e.pos}: {s[max(0, e.pos - 40):e.pos + 40]!r}")
        return None


for i in range(1, 11):
    sid = f"S{i:03d}"
    p = RAW_DIR / f"{sid}.json"
    rec = json.loads(p.read_text(encoding="utf-8"))
    if rec.get("status") != "ok":
        print(f"{sid}: status={rec.get('status')}，跳过")
        continue
    old = rec.get("parsed_json")
    new = tolerant_parse(rec.get("content") or "")
    if new != old:
        rec["parsed_json"] = new
        p.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
        mark = "已修复" if new else "解析失败"
        print(f"{sid}: {mark}")
    else:
        print(f"{sid}: 原解析已正确（或同样失败），未改动")
