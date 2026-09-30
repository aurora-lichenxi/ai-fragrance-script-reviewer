"""
rules.py — 确定性规则检查 (R1-R4)
================================
本文件只做"找得到 / 找不到"的事，不下对错判断。
不调用 AI 模型，纯字符串匹配。
所有结果以 dict 形式返回，可直接 json.dumps。

适配 brief v2.0 两层架构：
- content_reference（内容参考层）→ 本文件不读，仅供 AI 层使用
- rule_config（规则配置层）     → 本文件只读这一层

空数组语义：R2 某类填 [] 则跳过该类；R3 全空则直接 Clear；R4 空 [] 则跳过检查。

依赖：仅 Python 标准库（json / re / sys / pathlib）
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 常量与工具函数
# ---------------------------------------------------------------------------

# 项目根目录 = rules.py 所在目录
PROJECT_ROOT = Path(__file__).resolve().parent
BRIEF_PATH = PROJECT_ROOT / "data" / "briefs" / "brief.json"


def load_brief(brief_path: Path | None = None) -> dict:
    """加载 data/brief.json，返回字典"""
    p = Path(brief_path) if brief_path else BRIEF_PATH
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def find_keyword_evidence(script: str, keyword: str, window: int = 8) -> str | None:
    """
    返回 keyword 在 script 中首次出现的原文片段。
    取 keyword 前后各 window 字，便于回溯检查。
    找不到返回 None。
    """
    idx = script.find(keyword)
    if idx < 0:
        return None
    s = max(0, idx - window)
    e = min(len(script), idx + len(keyword) + window)
    return script[s:e]


# ---------------------------------------------------------------------------
# 分句与完整句子证据（R3 使用）
# 与既定文本预处理方案一致：先替换省略号与破折号，再按标点切分。
# 省略号视为句末（……/… → 断句）；破折号保留在句内（不产生断点）。
# 句末标点：。！？!? 与换行；逗号/顿号/分号等句内标点不切分，保证句子完整。
# ---------------------------------------------------------------------------

_SENT_SPLIT_RE = re.compile(r"[。！？!?]+|\n+")
_EVIDENCE_MAX_LEN = 120   # 单句超过此长度时截取关键词附近片段
_EVIDENCE_MAX_SENTS = 3   # 同一个词最多列出 3 个命中句子


def split_sentences(script: str) -> list[str]:
    """把脚本切分为句子列表（句末标点切分，句内标点保留）"""
    text = script.replace("……", "。").replace("…", "。")
    parts = [p.strip() for p in _SENT_SPLIT_RE.split(text)]
    return [p for p in parts if p]


def find_sentence_evidence(script: str, keyword: str) -> list[str]:
    """
    返回 script 中包含 keyword 的完整句子（按出现顺序去重，最多 3 句）。
    单句超过 _EVIDENCE_MAX_LEN 字时，截取 keyword 前后各 60 字并加省略号。
    找不到返回 []。
    """
    sents: list[str] = []
    for s in split_sentences(script):
        if keyword not in s:
            continue
        shown = s
        if len(shown) > _EVIDENCE_MAX_LEN:
            i = shown.find(keyword)
            start = max(0, i - 60)
            end = min(len(shown), i + len(keyword) + 60)
            shown = ("…" if start > 0 else "") + shown[start:end] + ("…" if end < len(shown) else "")
        if shown not in sents:
            sents.append(shown)
        if len(sents) >= _EVIDENCE_MAX_SENTS:
            break
    return sents


def _as_word_list(value) -> list[str]:
    """容错：把配置值规整为字符串列表（非列表/非字符串元素一律丢弃）"""
    if isinstance(value, list):
        return [w for w in value if isinstance(w, str) and w.strip()]
    return []


# ---------------------------------------------------------------------------
# R1 — 规则配置格式校验（自动检查，无需使用者填写）
# ---------------------------------------------------------------------------

def check_brief_completeness(brief: dict) -> dict:
    """
    校验 rule_config 三栏（R2 / R3 / R4）格式是否正确。
    注意：v2.0 起空数组是合法的（表示跳过），这里只查"格式错误"。

    输出：
    {
      "status": "Complete" | "Invalid",
      "errors": ["R2.must_appear.brand 应为词列表，实际是 str", ...]
    }
    """
    errors: list[str] = []

    rc = brief.get("rule_config", {}) or {}

    # --- R2.must_appear：应为 dict，值为词列表 ---
    r2 = rc.get("R2", {}) or {}
    must = r2.get("must_appear", {}) or {}
    if not isinstance(must, dict):
        errors.append("R2.must_appear 应为 {类名: 词列表} 的对象")
    else:
        for cat, words in must.items():
            if not isinstance(words, list):
                errors.append(f"R2.must_appear.{cat} 应为词列表，实际是 {type(words).__name__}")
            else:
                bad = [w for w in words if not isinstance(w, str)]
                if bad:
                    errors.append(f"R2.must_appear.{cat} 含非字符串元素：{bad!r}")

    # --- R3.forbidden：应为 dict，每类含 words 词列表 ---
    r3 = rc.get("R3", {}) or {}
    forbidden = r3.get("forbidden", {}) or {}
    if not isinstance(forbidden, dict):
        errors.append("R3.forbidden 应为 {子类名: {description, words}} 的对象")
    else:
        for sub, cfg in forbidden.items():
            if not isinstance(cfg, dict):
                errors.append(f"R3.forbidden.{sub} 应为对象，实际是 {type(cfg).__name__}")
                continue
            words = cfg.get("words", [])
            if not isinstance(words, list):
                errors.append(f"R3.forbidden.{sub}.words 应为词列表，实际是 {type(words).__name__}")
            else:
                bad = [w for w in words if not isinstance(w, str)]
                if bad:
                    errors.append(f"R3.forbidden.{sub}.words 含非字符串元素：{bad!r}")

    # --- R4.cta_words：应为词列表 ---
    r4 = rc.get("R4", {}) or {}
    cta = r4.get("cta_words", [])
    if not isinstance(cta, list):
        errors.append(f"R4.cta_words 应为词列表，实际是 {type(cta).__name__}")
    else:
        bad = [w for w in cta if not isinstance(w, str)]
        if bad:
            errors.append(f"R4.cta_words 含非字符串元素：{bad!r}")

    return {
        "status": "Invalid" if errors else "Complete",
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# R2 — 必现关键词检查（rule_config.R2.must_appear，空类跳过）
# ---------------------------------------------------------------------------

def check_keyword_coverage(brief: dict, script: str) -> dict:
    """
    把 must_appear 各类词分别与 script 做子串匹配。
    每类至少命中一词才算通过；填 [] 的类跳过（不算缺失）。

    输出：
    {
      "status": "Present" | "Missing",
      "present": {"brand": ["网易严选"], ...},
      "missing_categories": ["pain_point", ...],
      "skipped_categories": ["scene", ...]
    }
    """
    must = (brief.get("rule_config", {}) or {}).get("R2", {}).get("must_appear", {}) or {}

    present: dict[str, list[str]] = {}
    missing: list[str] = []
    skipped: list[str] = []

    for cat, words in must.items():
        word_list = _as_word_list(words)
        if not word_list:
            skipped.append(cat)
            continue
        hits = [w for w in word_list if w in script]
        if hits:
            present[cat] = hits
        else:
            missing.append(cat)

    return {
        "status": "Missing" if missing else "Present",
        "present": present,
        "missing_categories": missing,
        "skipped_categories": skipped,
    }


# ---------------------------------------------------------------------------
# R3 — 禁现风险词扫描（rule_config.R3.forbidden，空子类跳过）
# ---------------------------------------------------------------------------

def _flatten_risk_words(brief: dict) -> list[tuple[str, str, str]]:
    """
    把 R3.forbidden 各子类展开为 [(word, sub_category, description), ...] 列表。
    words 为空的子类自动跳过。
    """
    forbidden = (brief.get("rule_config", {}) or {}).get("R3", {}).get("forbidden", {}) or {}
    flat: list[tuple[str, str, str]] = []
    for sub, cfg in forbidden.items():
        if not isinstance(cfg, dict):
            continue
        desc = cfg.get("description", sub)
        for w in _as_word_list(cfg.get("words")):
            flat.append((w, sub, desc))
    return flat


def check_risk_words(brief: dict, script: str) -> dict:
    """
    检查 script 中是否出现禁现风险词中的任一。
    命中即 Flag，不下违规结论。
    证据为包含该词的完整句子（evidence = 首处句子，evidence_sentences = 全部命中句子），
    便于人工结合语境判断是否构成违规（如『第一印象』属固定搭配而非极限用法）。

    输出：
    {
      "status": "Clear" | "Risk Flag",
      "hits": [
        {"word": "第一", "category": "absolute_terms",
         "description": "极限类词语",
         "evidence": "客人进门的第一印象，就是玄关的味道",
         "evidence_sentences": ["客人进门的第一印象，就是玄关的味道", ...]}
      ]
    }
    """
    hits = []
    for word, sub, desc in _flatten_risk_words(brief):
        if word in script:
            sents = find_sentence_evidence(script, word)
            hits.append({
                "word": word,
                "category": sub,
                "description": desc,
                "evidence": sents[0] if sents else None,
                "evidence_sentences": sents,
            })
    return {
        "status": "Clear" if not hits else "Risk Flag",
        "hits": hits,
    }


# ---------------------------------------------------------------------------
# R4 — CTA 存在性检查（rule_config.R4.cta_words，空列表跳过）
# ---------------------------------------------------------------------------

def check_cta_presence(brief: dict, script: str) -> dict:
    """
    检查 script 中是否出现配置的 CTA 词。
    仅检查"有没有"，不判断"够不够强"（强 CTA 由 AI 评估）。
    cta_words 为空列表时跳过检查（status = Skipped）。

    输出：
    {
      "status": "Present" | "Missing" | "Skipped",
      "matched_cta": ["推荐", "入手"]
    }
    """
    cta_words = _as_word_list(
        (brief.get("rule_config", {}) or {}).get("R4", {}).get("cta_words")
    )
    if not cta_words:
        return {"status": "Skipped", "matched_cta": []}
    matched = [w for w in cta_words if w in script]
    return {
        "status": "Present" if matched else "Missing",
        "matched_cta": matched,
    }


# ---------------------------------------------------------------------------
# 总入口 — 给 app.py / evaluator.py 调用
# ---------------------------------------------------------------------------

def run_rules(brief: dict, script: str) -> dict:
    """汇总 R1-R4 检查结果（dict 形式，可直接 json.dumps）"""
    return {
        "R1_brief_complete": check_brief_completeness(brief),
        "R2_keyword_coverage": check_keyword_coverage(brief, script),
        "R3_risk_words": check_risk_words(brief, script),
        "R4_cta_present": check_cta_presence(brief, script),
    }


# ---------------------------------------------------------------------------
# 自测入口 — python rules.py --self-test
# ---------------------------------------------------------------------------

def _self_test() -> None:
    """跑 8 个自测用例，覆盖 R1/R2/R3/R4 全部路径（含 v2.0 空数组跳过语义）"""
    print("=" * 72)
    print("rules.py 自测 — 8 个用例覆盖 R1 / R2 / R3 / R4（brief v2.0 结构）")
    print("=" * 72)

    real_brief = load_brief()

    # CASE 1：R1 格式错误（must_appear.brand 填成了字符串）
    case1_brief = {"rule_config": {
        "R2": {"must_appear": {"brand": "网易严选", "product": ["香氛"]}},
        "R3": {"forbidden": {}},
        "R4": {"cta_words": []},
    }}

    # CASE 2：R2 全命中（brand / product / scene / pain_point / feature 都有词出现）
    case2_script = (
        "网易严选 0感香氛，是玄关必备，"
        "情绪价值满满，植物萃取不刺鼻，缓慢持续挥发。"
    )

    # CASE 3：R2 部分缺失（v2.0 口径：R2 仅按品牌词+产品词判门槛）
    case3_script = "网易严选香氛推荐给你。"

    # CASE 4：R3 命中风险词（极限类 + 权威类）
    case4_script = "这款是世界级香氛，国家级认证。"

    # CASE 5/6 专用 brief：R4 带 CTA 词（真实 PB01 v2.4 的 cta_words 已清空，
    # 用这份 brief 才能覆盖 R4 的 Present / Missing 两条路径）
    case56_brief = {"rule_config": {
        "R2": {"must_appear": {"brand": ["网易严选"], "product": ["香氛"]}},
        "R3": {"forbidden": {}},
        "R4": {"cta_words": ["推荐", "入手", "赶紧"]},
    }}

    # CASE 5：R4 CTA 命中
    case5_script = "推荐给你，赶紧入手看看。"

    # CASE 6：R4 CTA 缺失
    case6_script = "这款香氛很好闻但是没有行动指令。"

    # CASE 7：R2/R4 空数组跳过（跳过的类不算缺失，R4 直接 Skipped）
    case7_brief = {"rule_config": {
        "R2": {"must_appear": {"brand": ["网易严选"], "scene": [], "feature": []}},
        "R3": {"forbidden": {
            "absolute_terms": {"description": "极限类词语", "words": []},
        }},
        "R4": {"cta_words": []},
    }}

    # CASE 8：R3 证据为完整句子（『第一印象』固定搭配——仍命中，但证据给完整句子供人工判断）
    case8_script = (
        "客人进门的第一印象，就是玄关的味道。"
        "这款网易严选香氛放在玄关，朋友进门第一眼就能闻到。"
        "它卖得很好，是我们店销量第一的香氛。"
    )

    cases = [
        ("CASE 1: R1 格式错误（brand 填成字符串）",
         case1_brief, "任意脚本",
         "预期：R1.status=Invalid, errors 含 must_appear.brand"),
        ("CASE 2: R2 全命中（brand/product 均命中，v2.0 仅按品牌词+产品词判门槛）",
         real_brief, case2_script,
         "预期：R2.status=Present, missing_categories=[], skipped=[]"),
        ("CASE 3: R2 命中（脚本含品牌词+产品词；场景/痛点/特征 v2.0 不再作门槛）",
         real_brief, case3_script,
         "预期：R2.status=Present, missing_categories=[]"),
        ("CASE 4: R3 命中风险词（极限类+权威类）",
         real_brief, case4_script,
         "预期：R3.status=Risk Flag, hits 含 世界级/国家级"),
        ("CASE 5: R4 CTA 命中（专用 brief，cta_words 非空）",
         case56_brief, case5_script,
         "预期：R4.status=Present, matched_cta 含 推荐/入手/赶紧"),
        ("CASE 6: R4 CTA 缺失（专用 brief，cta_words 非空但脚本无指令词）",
         case56_brief, case6_script,
         "预期：R4.status=Missing, matched_cta=[]"),
        ("CASE 7: 空数组跳过（scene/feature 跳过，R4 Skipped）",
         case7_brief, "网易严选很好闻。",
         "预期：R2.status=Present（scene/feature 在 skipped 里）, R4.status=Skipped"),
        ("CASE 8: R3 证据为完整句子（第一印象/第一眼/销量第一）",
         real_brief, case8_script,
         "预期：R3.status=Risk Flag, 命中『第一』，evidence 为包含它的完整句子（3 句都含第一，最多列 3 句）"),
    ]

    for i, (name, brief, script, expect) in enumerate(cases, 1):
        print(f"\n{'-' * 72}")
        print(f"CASE {i}: {name}")
        print(f"  {expect}")
        print(f"  script: {script}")
        print(f"{'-' * 72}")
        result = run_rules(brief, script)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    print(f"\n{'=' * 72}")
    print("自测完成 — 逐条比对预期与输出")
    print("如全部符合预期，说明 R1-R4 在 v2.0 brief 结构下逻辑正确")
    print("=" * 72)


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        _self_test()
    else:
        print("用法：")
        print("  python rules.py --self-test   跑 8 个自测用例")
        print("  python rules.py               打印本说明")
        sys.exit(0)
