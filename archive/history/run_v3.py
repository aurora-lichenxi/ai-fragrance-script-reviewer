"""
run_v3.py — 用 v3 Prompt 跑 Qwen DashScope API（试跑：S003 + S005 校准样本）

与 run_v2.py 相同的流程，仅切换：
- PROMPT_PATH → prompts/v3.txt
- RESULTS_DIR → results/v3_raw
- 试跑样本：S003、S005（v2 轮偏严最典型样本，用于校验 v3 严格度回调方向）

试跑通过后再改为全量 S001-S011。

运行：
    python run_v3.py
"""
from __future__ import annotations
import csv
import json
import sys
import time
from pathlib import Path
from urllib import request as urlrequest
from urllib.error import URLError, HTTPError

# ---------- 路径 ----------
# 用法：python run_v3.py [prompt名，默认v3] [样本ID ...]（默认试跑 S003 S005）
PROJECT_ROOT = Path(__file__).resolve().parent
_ARGS = sys.argv[1:]
PROMPT_NAME = _ARGS[0] if _ARGS else "v3"
PROMPT_PATH = PROJECT_ROOT / "prompts" / f"{PROMPT_NAME}.txt"
BRIEF_PATH = PROJECT_ROOT / "data" / "brief.json"
SCRIPTS_CSV = PROJECT_ROOT / "data" / "scripts.csv"
RESULTS_DIR = PROJECT_ROOT / "results" / f"{PROMPT_NAME}_raw"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# 试跑：默认 S003、S005（v2 轮偏严最典型样本，用于校验严格度回调方向）
TEST_SAMPLE_IDS = _ARGS[1:] if len(_ARGS) > 1 else ["S003", "S005"]


# ---------- .env 读取（不依赖 python-dotenv）----------
def load_env(path: Path) -> dict[str, str]:
    cfg: dict[str, str] = {}
    if not path.exists():
        return cfg
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        cfg[k.strip()] = v.strip().strip('"').strip("'")
    return cfg


env = load_env(PROJECT_ROOT / ".env")
API_KEY = env.get("QWEN_API_KEY", "")
BASE_URL = env.get("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1").rstrip("/")
MODEL = env.get("QWEN_MODEL", "qwen-plus")
TIMEOUT = int(env.get("QWEN_TIMEOUT", "20"))


# ---------- 渲染 prompt ----------
def render_prompt(tpl: str, brief: dict, sample_id: str, script: str) -> str:
    # v1.3 起 AI 层只见 content_reference（rule_config 由规则层执行，不注入 AI）
    brief_for_ai = {
        "brief_id": brief.get("brief_id"),
        "version": brief.get("version"),
        "content_reference": brief.get("content_reference", {}),
    }
    return (tpl
            .replace("{{brief_json}}", json.dumps(brief_for_ai, ensure_ascii=False, indent=2))
            .replace("{{sample_id}}", sample_id)
            .replace("{{script}}", script))


# ---------- 调 API ----------
def call_qwen(prompt: str) -> dict:
    """返回 {'ok': True, 'raw': {...}} 或 {'ok': False, 'kind': ..., 'error': ...}"""
    if not API_KEY:
        return {"ok": False, "kind": "missing_key",
                "error": ".env 中没有 QWEN_API_KEY。请在项目根目录创建 .env 并填入 Key。"}

    url = f"{BASE_URL}/chat/completions"
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }
    req = urlrequest.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        },
        method="POST",
    )
    try:
        with urlrequest.urlopen(req, timeout=TIMEOUT) as resp:
            body = resp.read().decode("utf-8")
        return {"ok": True, "raw": json.loads(body)}
    except HTTPError as e:
        return {"ok": False, "kind": "http_error",
                "error": f"HTTP {e.code}: {e.reason}"}
    except URLError as e:
        return {"ok": False, "kind": "timeout_or_network",
                "error": str(e.reason)}
    except json.JSONDecodeError as e:
        return {"ok": False, "kind": "invalid_response",
                "error": f"响应不是合法 JSON: {e}"}
    except Exception as e:
        return {"ok": False, "kind": "unknown", "error": repr(e)}


def extract_content(api_resp: dict) -> str:
    try:
        return api_resp["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        return ""


STRUCT_AFTER_CLOSE = {",", "}", "]", ":"}


def repair_json_text(s: str) -> str:
    """
    修复 LLM 输出的非严格 JSON：
    1. 字符串值内的原始换行/制表符 → 转义
    2. 字符串值内未转义的内嵌英文双引号 → 转义
       判定规则：字符串态遇到 " 时，向后跳过空白看第一个字符——
       若是 , } ] : 则视为字符串结束符；否则视为内嵌引号，转义保留。
    """
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


def extract_json_from_text(text: str) -> dict | None:
    """容忍 LLM 把 JSON 裹在 ```json ... ``` 里；再容忍字符串内原始换行与内嵌引号"""
    s = text.strip()
    if s.startswith("```"):
        first_nl = s.find("\n")
        if first_nl > 0:
            s = s[first_nl + 1:]
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
    except json.JSONDecodeError:
        return None


# ---------- 主流程 ----------
def main() -> int:
    print("=" * 70)
    print(f"run_v3.py — 用 {PROMPT_NAME} Prompt 跑 Qwen API（{len(TEST_SAMPLE_IDS)} 条样本）")
    print(f"模型：{MODEL}  Base：{BASE_URL}  超时：{TIMEOUT}s")
    print("=" * 70)

    if not PROMPT_PATH.exists():
        print(f"[ERROR] 找不到 {PROMPT_PATH}")
        return 1

    prompt_tpl = PROMPT_PATH.read_text(encoding="utf-8")
    brief = json.loads(BRIEF_PATH.read_text(encoding="utf-8"))

    with open(SCRIPTS_CSV, encoding="utf-8-sig", newline="") as f:
        samples = {r["sample_id"]: r for r in csv.DictReader(f)}

    summary: list[dict] = []

    for sid in TEST_SAMPLE_IDS:
        print(f"\n--- {sid} ---")
        if sid not in samples:
            print(f"  [SKIP] 样本不存在")
            continue

        sample = samples[sid]
        rendered = render_prompt(prompt_tpl, brief, sid, sample["script"])
        print(f"  脚本 {len(sample['script'])} 字 → 渲染后 prompt {len(rendered)} 字")
        print(f"  reviewer_label：{sample['reviewer_label']}")

        t0 = time.time()
        result = call_qwen(rendered)
        elapsed = time.time() - t0

        record: dict = {
            "sample_id": sid,
            "elapsed_sec": round(elapsed, 2),
            "reviewer_label": sample["reviewer_label"],
        }

        if not result["ok"]:
            print(f"  [FAIL] {result['kind']}: {result['error'][:120]}")
            record["status"] = "fail"
            record["error_kind"] = result["kind"]
            record["error"] = result["error"]
        else:
            content = extract_content(result["raw"])
            record["status"] = "ok"
            record["content"] = content
            record["parsed_json"] = extract_json_from_text(content)
            print(f"  [OK]  {elapsed:.1f}s  content {len(content)} 字")
            if record["parsed_json"] is None:
                print(f"  [WARN] content 不是合法 JSON")
                print(f"  预览：{content[:160]}...")
            else:
                pj = record["parsed_json"]
                statuses = []
                for k in ["A1", "A2", "A3", "A4", "A5", "A6"]:
                    d = pj.get(k) or {}
                    statuses.append(f"{k}={d.get('status', '?')}")
                overall = pj.get("overall", "?")
                hri = pj.get("human_review_items", [])
                print(f"  状态：{', '.join(statuses)} | overall={overall} | 人工复核 {len(hri)} 项")

        out_path = RESULTS_DIR / f"{sid}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        summary.append(record)

    summary_path = RESULTS_DIR / "_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 70}")
    ok = sum(1 for r in summary if r.get("status") == "ok")
    print(f"完成：{ok}/{len(summary)} 成功。结果在 {RESULTS_DIR}")

    # 与人工判定对齐情况
    print("\n=== 与 reviewer_label 对照（仅成功样本） ===")
    print(f"{'ID':<6}{'人工':<18}{'AI overall':<18}{'A1':<8}{'A2':<8}{'A3':<8}{'A4':<8}{'A5':<8}{'A6':<8}")
    for r in summary:
        if r.get("status") != "ok":
            continue
        pj = r.get("parsed_json") or {}
        row = [r["sample_id"], r["reviewer_label"], pj.get("overall", "?")]
        for k in ["A1", "A2", "A3", "A4", "A5", "A6"]:
            row.append(((pj.get(k) or {}).get("status", "?")))
        print(f"{row[0]:<6}{row[1]:<18}{row[2]:<18}" + "".join(f"{x:<8}" for x in row[3:]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
