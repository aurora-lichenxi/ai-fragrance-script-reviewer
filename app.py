# -*- coding: utf-8 -*-
# ============================================================
# 区块 ① ｜ 文件说明（docstring 头部，见下方三引号包裹部分）
# ------------------------------------------------------------
# 【模块整体在干嘛】
#   app.py 顶部的项目说明文档。向开发者/读者展示：这个文件是干什么的、
#   支持哪些使用方式、需要哪些配置信息、整体设计思路是什么。
#   是任何人第一次打开这个文件时第一眼必看的"使用说明书"。
# ------------------------------------------------------------
# 【具体解释】
#   · 标题：app.py 是这个项目的统一主入口（所有使用都从这里开始）
#   · 一句话定位：为网易严选 0感香氛产品做的"短视频脚本机器 Review"
#   · 用法清单（4 个子命令）：
#       diagnose  → 单条诊断（手动贴一条脚本让 AI 审）
#       batch     → 批量诊断（一次跑完数据表里所有脚本）
#       eval      → 评估（对比 AI 判定与人工标注的吻合率）
#       web       → 启动网页界面（给非技术同事用）
#   · 配置说明（.env 文件里要放的 4 把钥匙）：
#       API Key 必填（不填就跑不起来），其余三项有默认值
#   · 设计说明（最重要）：双层架构 + 三档整体判定
#       规则层 rules.py 字面匹配 + AI 层 qwen 模型语义判断
#       整体档位逻辑：任一 NR → Needs Revision；
#                     有 Reminder 无 NR → Reminder；
#                     全 Pass → Pass
# ============================================================
"""
app.py — AI 香氛短视频内容诊断 · 统一主入口
================================================
网易严选 0感香氛｜短视频口播脚本机器 Review

用法：
    python app.py diagnose "脚本文本"          单条诊断（规则层 R1-R4 + AI 层 A1-A6 + 三档整体判定）
    python app.py diagnose --file 路径.txt     从文本文件读脚本诊断
    python app.py batch [S001 S002 ...]        批量诊断（默认 data/scripts.csv 全量；结果落盘 results/app_raw/）
    python app.py eval [--batch old|new|all]   评估：AI 判定 vs 人工标注逐项吻合率（默认用已有结果）
    python app.py web [--port 8501]            启动本机网页界面（自动打开浏览器）

配置：项目根目录 .env
    QWEN_API_KEY=sk-xxx        （必填，阿里云 DashScope Key）
    QWEN_BASE_URL=...          （默认 https://dashscope.aliyuncs.com/compatible-mode/v1）
    QWEN_MODEL=qwen-plus
    QWEN_TIMEOUT=120

设计：规则层（rules.py 纯字面匹配）+ AI 层（qwen × prompt v4.0 语义诊断）；
最终整体判定 = R2 门槛缺失 / R3 命中 / A1-A6 任一 NR → Needs Revision；
无 NR 有 Reminder → Reminder；全 Pass → Pass。
"""
# ============================================================
# 区块 ② ｜ 工具箱与路径常量
# ------------------------------------------------------------
# 【模块整体在干嘛】
#   加载 app.py 后续代码要用到的标准库、第三方库与项目内部模块，
#   并预先定义好各个关键路径常量（项目根目录、数据文件、结果文件夹等），
#   让后面所有函数不用反复拼路径，直接引用常量即可。
# ------------------------------------------------------------
# 【具体解释】
#   · 工具箱：导入 argparse（命令行参数解析）、json（JSON 读写）、
#     csv（表格读取）、urllib.request（调外部接口）等基础库
#   · 项目内模块：import rules —— 同目录的 rules.py 文件，
#     提供 R1-R4 硬规则的判定函数
#   · 路径兼容逻辑：兼容"开发模式（直接跑 .py 脚本）"与
#     "打包模式（PyInstaller 打成 .exe）"两种运行方式，
#     自动判断资源文件在哪、结果写到哪
#   · 关键路径常量：
#       BRIEF_PATH       → 业务规则配置（brief.json）
#       SCRIPTS_CSV      → 脚本样本表
#       PROMPTS_DIR      → Prompt 文件夹
#       RESULTS_DIR      → 结果输出总目录
#       ENV_PATH         → .env 密钥文件位置
#   · 默认 Prompt 版本号（v4.1）
#   · 维度与档位枚举：
#       DIMS = A1..A6 六个评估维度
#       ORDER = 三档优先级排序（Pass=2 > Reminder=1 > NR=0）
#   · 规则档位 → 整体档位的映射表（Complete/Present/Clear → Pass；
#     Missing/Risk Flag/Invalid → NR；Skipped 跳过）
# ============================================================


from __future__ import annotations
import argparse
import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib import request as urlrequest
from urllib.error import URLError, HTTPError

import rules  # 同目录 rules.py：R1-R4 确定性规则

PROJECT_ROOT = Path(__file__).resolve().parent
# PyInstaller 打包后：资源（brief/prompt）在临时解压目录 _MEIPASS；.env/结果写在 exe 旁边
if getattr(sys, "frozen", False):
    BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    APP_DIR = Path(sys.executable).parent
else:
    BUNDLE_ROOT = PROJECT_ROOT
    APP_DIR = PROJECT_ROOT
BRIEF_PATH = BUNDLE_ROOT / "data" / "briefs" / "brief.json"
SCRIPTS_CSV = BUNDLE_ROOT / "data" / "scripts.csv"
PROMPTS_DIR = BUNDLE_ROOT / "prompts"
RESULTS_DIR = APP_DIR / "results"
DIAGNOSE_DIR = RESULTS_DIR / "diagnose"
BRIEF_REVIEW_DIR = RESULTS_DIR / "产品brief人工审核版"
ENV_PATH = APP_DIR / ".env"
DEFAULT_PROMPT = "v4.1"
DIMS = ["A1", "A2", "A3", "A4", "A5", "A6"]
ORDER = {"Pass": 2, "Reminder": 1, "Needs Revision": 0}
RULE_STATUS_LABEL = {
    "Complete": "Pass", "Present": "Pass", "Clear": "Pass",
    "Missing": "Needs Revision", "Risk Flag": "Needs Revision",
    "Invalid": "Needs Revision", "Skipped": "Skipped",
}


# ---------------------------------------------------------------------------
# 基础设施：.env / API / JSON 容错解析
# ---------------------------------------------------------------------------

# ============================================================
# 区块 ③ ｜ 读 .env 配置
# ------------------------------------------------------------
# 【模块整体在干嘛】
#   读 .env 文件里的"钥匙"（API Key、接口地址、模型名、超时秒数），
#   把里面的键值对解析出来，存到 ENV 字典里给后面 call_qwen 等函数用。
#   如果 .env 不存在，返回空字典（由后续调用检查是否缺 Key 并提示）。
# ------------------------------------------------------------
# 【具体解释】
#   · 函数 load_env：按行读 .env 文件，跳过空行与 # 注释行，
#     用 = 拆分成键值对，剥掉字符串外围的双引号/单引号，返回字典
#   · 模块加载即执行：app.py 一被导入就立刻把 ENV 读入，
#     后续任何函数都可以直接 ENV.get("QWEN_API_KEY") 这样取
# ============================================================


def load_env(path: Path | None = None) -> dict[str, str]:
    p = Path(path) if path else ENV_PATH
    cfg: dict[str, str] = {}
    if not p.exists():
        return cfg
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        cfg[k.strip()] = v.strip().strip('"').strip("'")
    return cfg


ENV = load_env()


# ============================================================
# 区块 ④ ｜ 模型调用 call_qwen + 第一/二道异常防线
# ------------------------------------------------------------
# 【模块整体在干嘛】
#   通过 HTTP POST 调用阿里云 DashScope 的 qwen-plus 模型，
#   把 prompt 内容发给 AI、等到 AI 返回文本结果。
#   同一段代码里包含两道防护：缺 Key 不发请求、网络/解析失败都返回失败标识，
#   不让程序因为一个失败就直接崩溃。
# ------------------------------------------------------------
# 【具体解释】
#   · 函数定义与默认值：
#       从 .env 读或使用调用方传入的 API Key、接口地址、模型名、超时秒数
#       （OpenAI 兼容模式，所以可以无缝切到任意兼容厂商）
#   · 第一道防线（缺 Key 预检）：
#       没填 API Key 直接返回 ok=False，不发请求，
#       避免线上 401 报错让用户困惑
#   · 构造请求体与 HTTP 请求头
#   · 第二道防线（请求/解析异常）：
#       HTTPError       → 网关返回 4xx/5xx，返回 kind=http + 状态码
#       URLError        → 网络不通或超时，返回 kind=network
#       JSONDecodeError → 返回的不是合法 JSON
#       Exception       → 其他兜底
#       所有失败都返回 {'ok': False, 'kind': ..., 'error': '...'}，
#       绝不抛异常给上游
# ============================================================


def call_qwen(prompt: str, api_key: str = "", base_url: str = "", model: str = "", timeout: int = 0) -> dict:
    """调 DashScope（OpenAI 兼容模式）。返回 {'ok': True, 'raw': ...} 或 {'ok': False, 'kind', 'error'}"""
    api_key = api_key or ENV.get("QWEN_API_KEY", "")
    base_url = (base_url or ENV.get("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")).rstrip("/")
    model = model or ENV.get("QWEN_MODEL", "qwen-plus")
    timeout = timeout or int(ENV.get("QWEN_TIMEOUT", "120"))

    if not api_key:
        return {"ok": False, "kind": "missing_key",
                "error": "未配置 QWEN_API_KEY。请在项目根目录 .env 填入 Key（参考 .env.example）。"}

    payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0}
    req = urlrequest.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            return {"ok": True, "raw": json.loads(resp.read().decode("utf-8"))}
    except HTTPError as e:
        return {"ok": False, "kind": "http_error", "error": f"HTTP {e.code}: {e.reason}"}
    except URLError as e:
        return {"ok": False, "kind": "timeout_or_network", "error": str(e.reason)}
    except json.JSONDecodeError as e:
        return {"ok": False, "kind": "invalid_response", "error": f"响应不是合法 JSON: {e}"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "kind": "unknown", "error": repr(e)}


# ============================================================
# 区块 ⑤ ｜ 取出模型内容
# ------------------------------------------------------------
# 【模块整体在干嘛】
#   从 DashScope 的标准响应里挑出"模型真正生成的那段文本"。
#   DashScope 用 OpenAI 兼容格式返回，模型内容嵌在
#   choices[0].message.content 位置 —— 这一段就是把它取出来，
#   给后面的 JSON 解析步骤用。
# ------------------------------------------------------------
# 【具体解释】
#   · 函数 extract_message_content：
#       防御性取值（任一层缺失返回空串），
#       避免下游 JSON 解析踩到 None 或 KeyError
# ============================================================


def extract_content(api_resp: dict) -> str:
    try:
        return api_resp["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        return ""


# ============================================================
# 区块 ⑥ ｜ 第三道异常防线 + JSON 解析
# ------------------------------------------------------------
# 【模块整体在干嘛】
#   把模型返回的"看起来像 JSON"的文本解析成 Python dict。
#   AI 经常不会老老实实输出纯 JSON，而是会包一层 ```json ... ``` 代码块、
#   或引号/逗号写错 —— 这一段就是处理这些"毛糙输出"的容错逻辑。
#   是整个项目容错最关键的兜底层。
# ------------------------------------------------------------
# 【具体解释】
#   · 剥 Markdown 包裹：
#       先按 ```json 切，再按 ``` 切，把代码块包围去掉
#   · 直接解析：
#       先尝试 json.loads，再兜底一次正则抓 {...} 切片
#   · 最后兜底（修复式解析）：
#       用 repair_json_text 强行修一次常见错误
#       （多余逗号、单引号、未闭合括号），
#       还不行才返回 None，让上游判定为"解析失败"
# ============================================================


STRUCT_AFTER_CLOSE = {",", "}", "]", ":"}


def repair_json_text(s: str) -> str:
    """修复 LLM 输出的非严格 JSON：字符串内原始换行/制表转义 + 内嵌双引号转义"""
    out, i, n, in_str, esc = [], 0, len(s), False, False
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


# ---------------------------------------------------------------------------
# 核心流程
# ---------------------------------------------------------------------------

# ============================================================
# 区块 ⑦ ｜ 业务核心：加载 brief、拼模板、整体判定
# ------------------------------------------------------------
# 【模块整体在干嘛】
#   项目的"业务内核"：把 brief.json 的内容（场景/痛点/品牌词等业务规则）和
#   prompt 模板（v4.1）拼起来，形成发给模型的完整指令，
#   并实现最终的三档整体判定 —— 所有判定逻辑的"灵魂"都在这一段。
# ------------------------------------------------------------
# 【具体解释】
#   · 加载 brief：读 brief.json，把里面的 content_reference
#     （AI 阅读层）与 rule_config（R1-R4 规则配置）拆开，
#     放进两个独立字典（双层架构的关键）
#   · 加载 prompt：读 prompts/v4.1.txt 模板，
#     把 {brand_scenes} {pain_points} {rule_summary} 等占位符
#     替换为真实业务内容，生成最终发给模型的字符串
#   · 整体判定 derive_final_overall：
#       输入：A1-A6 六个维度的判定 + R1-R4 四个规则的命中状态
#       输出：三档之一（Pass / Reminder / Needs Revision）
#       逻辑：①任一 NR → Needs Revision；②有 Reminder 无 NR → Reminder；
#            ③全 Pass → Pass
# ============================================================


def load_brief() -> dict:
    return json.loads(BRIEF_PATH.read_text(encoding="utf-8"))


def draft_to_brief(draft: dict) -> dict:
    """
    人工确认的 brief 草稿（10 个平铺字段）→ 双层诊断 brief。
    content_reference 供 AI 层阅读；rule_config 供规则层 R1-R4 执行。
    字段映射（与 BRIEF_FIELD_META 的 10 个解析维度一一对应）：
      brand_words/product_words → R2 门槛；banned_claims → R3 自定义禁用 + AI 阅读层；
      cta_words → R4；core_selling_points（"卖点 | 官方表达参考"）→ AI 阅读层卖点；
      official_claims/target_audience/scenes/specs_price/category → AI 阅读层。
    """
    def _words(key: str) -> list[str]:
        return [str(x).strip() for x in (draft.get(key) or []) if str(x).strip()]

    brand = _words("brand_words")
    product = _words("product_words")
    selling = []
    for item in draft.get("core_selling_points") or []:
        s = str(item).strip()
        if not s:
            continue
        if "|" in s:
            p, ref = s.split("|", 1)
            selling.append({"point": p.strip(), "expression_ref": ref.strip()})
        else:
            selling.append({"point": s, "expression_ref": ""})
    claims = _words("official_claims")
    banned = _words("banned_claims")
    cta = _words("cta_words")

    content_reference = {
        "naming": {
            "brand": brand[0] if brand else "",
            "series": "",
            "generic_name": str(draft.get("category") or "").strip(),
            "craft": "",
            "brief_note": "本 brief 由使用者粘贴原文、大模型结构化抽取、人工确认编辑后生成",
        },
        "specs": {"price": str(draft.get("specs_price") or "").strip()},
        "official_claims": {
            "source": "使用者人工确认的官方宣称口径",
            "usage_note": "以下为人工确认的官方口径；脚本引用时只需检查是否与该口径一致（数值不得夸大、技术名称不得窜改）。",
            "claims": claims,
        },
        "audience_scenes": {
            "target_audience": _words("target_audience"),
            "scenes": _words("scenes"),
        },
        "core_selling_points": selling,
        "banned_claims": banned,
    }
    rule_config = {
        "R1": {"description": "自动检查，无需填写：校验以下各栏格式是否正确"},
        "R2": {
            "description": "人工确认 brief：品牌词与产品词为强制门槛（与人工 Review 口径一致）",
            "must_appear": {"brand": brand, "product": product},
        },
        "R3": {
            "description": "人工确认 brief：自定义禁用表述；为空则跳过 R3 检查",
            "forbidden": {"custom_banned": {"description": "人工确认的禁用表述", "words": banned}},
        },
        "R4": {
            "description": "CTA 行动指令词：至少命中一个才算存在；没有可填 []",
            "cta_words": cta,
        },
        "overall": {
            "description": "整体判定逻辑（三档）：全 Pass→Pass；有 Reminder 无 NR→Reminder；任一 NR→Needs Revision（规则层 R2 缺失 / R3 命中同样导致 NR）",
            "logic": "all_pass_then_pass_only_reminder_then_reminder_any_nr_then_needs_revision",
        },
    }
    return {
        "brief_id": "USER-CONFIRMED",
        "version": "draft-1.0",
        "content_reference": content_reference,
        "rule_config": rule_config,
    }


def load_active_brief() -> tuple[dict, str]:
    """
    诊断用 brief：优先使用 results/产品brief人工审核版/ 里最新一份人工确认草稿
    （必需字段 brand_words/product_words 齐全才启用）；否则回退内置 PB01。
    返回 (brief, 来源描述)。
    """
    if BRIEF_REVIEW_DIR.exists():
        for path in sorted(BRIEF_REVIEW_DIR.glob("BRIEF-*.json"), reverse=True):
            try:
                rec = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            d = rec.get("draft") or {}
            if d.get("brand_words") and d.get("product_words"):
                src = rec.get("saved_at") or path.stem
                return draft_to_brief(d), f"人工确认版（保存于 {src}）"
    return load_brief(), "内置 PB01 v2.4（0感香氛）"


def render_prompt(tpl: str, brief: dict, sample_id: str, script: str) -> str:
    brief_for_ai = {
        "brief_id": brief.get("brief_id"),
        "version": brief.get("version"),
        "content_reference": brief.get("content_reference", {}),
    }
    return (tpl
            .replace("{{brief_json}}", json.dumps(brief_for_ai, ensure_ascii=False, indent=2))
            .replace("{{sample_id}}", sample_id)
            .replace("{{script}}", script))


def derive_final_overall(rule_result: dict, ai_dims: dict) -> str:
    """三档整体判定：R2 门槛缺失 / R3 命中 / 任一维度 NR → NR；无 NR 有 Rem → Rem；全 Pass → Pass"""
    if rule_result["R2_keyword_coverage"].get("missing_categories"):
        return "Needs Revision"
    if rule_result["R3_risk_words"]["status"] == "Risk Flag":
        return "Needs Revision"
    if "Needs Revision" in ai_dims.values():
        return "Needs Revision"
    if "Reminder" in ai_dims.values():
        return "Reminder"
    return "Pass"


# ---------------------------------------------------------------------------
# 产品 Brief 结构化解析（新品类实验 · 阶段一）
# ---------------------------------------------------------------------------

# ============================================================
# 区块 ⑧ ｜ 备用功能：brief 文本 → 结构化抽取
# ------------------------------------------------------------
# 【模块整体在干嘛】
#   把"业务方手写的 brief 自然语言描述"翻译成"机器可读的结构化 JSON"。
#   这是个备用功能：通常 brief 由我们自己整理好后写进 brief.json，
#   但偶尔需要快速把一份自然语言 brief 转成结构化版本，这一块就用得上。
# ------------------------------------------------------------
# 【具体解释】
#   · 函数结构 + 构造抽取指令：拼一段 prompt 让 AI
#     把自由文本切成 content_reference + rule_config 两层结构
#   · 把模型输出解析成 dict 并落盘到 brief.json，
#     校验必填字段，缺字段时写错误日志而不是崩溃
# ============================================================


BRIEF_EXTRACT_PROMPT = """你是产品 Brief 结构化助手。任务：从产品 brief 原文中抽取结构化信息，供短视频脚本诊断系统使用。输出严格 JSON，不要任何其他文字、不要 Markdown 代码块包裹。

# 抽取字段

- category：商品分类，一个短语（如"香氛/香薰""面部护肤""休闲零食"）
- brand_words：品牌名及官方可接受的写法/简称（数组）
- product_words：产品名、系列名、关键成分/香型/型号的规范写法——营销脚本中必须出现的产品相关词（数组）
- core_selling_points：核心卖点清单，每条一个短语；若原文含该卖点的官方表达参考，写作"卖点短语 | 官方表达参考"（数组）
- official_claims：官方宣称的检测数据与技术口径，保留具体数值、单位、来源性质，如"抑菌率99.9%（官方商详）"（数组）
- banned_claims：禁用或限制的表述/宣称边界（数组）
- target_audience：目标人群（数组）
- scenes：使用场景（数组）
- specs_price：规格与价格信息（一段文本；无则空字符串）
- cta_words：brief 明确规定脚本必须出现的 CTA 词（数组；brief 未要求则 []）

# 抽取规则

1. 只抽取 brief 原文中明确存在的信息，禁止编造、禁止用行业常识补全
2. 没有的字段：数组给 []，文本给 ""
3. 保留原文数值、单位、规范写法，不改写不概括
4. 简称、俗称只有在 brief 注明可接受时才进 brand_words/product_words，否则不收

## 产品 Brief 原文

{{brief_text}}

# 输出

仅输出一个 JSON 对象，包含上述全部字段，不要任何其他文字。"""

# 字段元数据：(key, 显示名, 必填级别, 值类型)——必填级别 hard=缺失无法诊断 / soft=缺失降级运行
BRIEF_FIELD_META = [
    ("category", "商品分类", "hard", "text"),
    ("brand_words", "品牌词（规范写法/简称）", "hard", "list"),
    ("product_words", "产品词（必须出现的规范写法）", "hard", "list"),
    ("core_selling_points", "核心卖点", "hard", "list"),
    ("official_claims", "官方宣称（数据/技术口径）", "soft", "list"),
    ("banned_claims", "禁用表述/宣称边界", "soft", "list"),
    ("target_audience", "目标人群", "soft", "list"),
    ("scenes", "使用场景", "soft", "list"),
    ("specs_price", "规格与价格", "soft", "text"),
    ("cta_words", "规定 CTA 词（可选）", "soft", "list"),
]


def _field_missing(pj: dict, key: str) -> bool:
    v = pj.get(key)
    if isinstance(v, str):
        return not v.strip()
    return not v  # None / [] / {}


def parse_brief_text(text: str, api_key: str = "") -> dict:
    """自由文本 brief → LLM 结构化抽取 + 必填校验。返回 {ok, parsed, missing_hard, missing_soft} 或 {ok:False,...}"""
    prompt = BRIEF_EXTRACT_PROMPT.replace("{{brief_text}}", text.strip())
    api = call_qwen(prompt, api_key=api_key)
    if not api["ok"]:
        return {"ok": False, "kind": api["kind"], "error": api["error"]}

    pj = extract_json_from_text(extract_content(api["raw"]))
    if pj is None:
        return {"ok": False, "kind": "parse_fail",
                "error": "LLM 输出无法解析为 JSON，请重试或精简 brief 原文"}

    missing_hard = [name for key, name, lvl, _t in BRIEF_FIELD_META
                    if lvl == "hard" and _field_missing(pj, key)]
    missing_soft = [name for key, name, lvl, _t in BRIEF_FIELD_META
                    if lvl == "soft" and _field_missing(pj, key)]
    return {"ok": True, "parsed": pj,
            "missing_hard": missing_hard, "missing_soft": missing_soft}


# ============================================================
# 区块 ⑨ ｜ 主流程 diagnose_script（最关键）
# ------------------------------------------------------------
# 【模块整体在干嘛】
#   这是整个 app.py 最重要的一段函数：拿到一条短视频脚本，
#   端到端地跑完整套诊断（R1-R4 + A1-A6 + 整体判定）并返回结果。
#   diagnose、batch、eval 三个子命令最终都调用它。
# ------------------------------------------------------------
# 【具体解释】
#   · 函数定义与签名：输入脚本文本 + 可选 brief/prompt 版本号，
#     输出一个 dict（含每条规则的命中、每个维度的判定、整体档位）
#   · 跑规则层：调用 rules.R1..R4，得到每条规则的判定字符串
#   · 跑 AI 层：拼 prompt → 调 call_qwen →
#     extract_json_from_text 解析 → 得到 A1-A6 六个维度的判定
#   · 算整体档位：调用 derive_final_overall 收口
#   任何一层失败（网络/解析/规则异常）都会被捕获，
#   返回一个带 ok=False 的失败 dict，而不是抛异常给上游
# ============================================================


def diagnose_script(script: str, prompt_name: str = DEFAULT_PROMPT, sample_id: str = "",
                    api_key: str = "") -> dict:
    """单条脚本全流程诊断：规则层 + AI 层 + 三档推导。返回完整结果 dict（不落盘）。"""
    brief, brief_source = load_active_brief()
    tpl_path = PROMPTS_DIR / f"{prompt_name}.txt"
    if not tpl_path.exists():
        raise FileNotFoundError(f"找不到 prompt 文件：{tpl_path}")
    tpl = tpl_path.read_text(encoding="utf-8")

    sid = sample_id or f"ADHOC-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    rule_result = rules.run_rules(brief, script)

    t0 = time.time()
    api = call_qwen(render_prompt(tpl, brief, sid, script), api_key=api_key)
    elapsed = round(time.time() - t0, 1)

    record = {
        "sample_id": sid,
        "prompt": prompt_name,
        "brief_source": brief_source,
        "script_length": len(script),
        "elapsed_sec": elapsed,
        "rule_layer": rule_result,
    }
    if not api["ok"]:
        record["status"] = "fail"
        record["error_kind"] = api["kind"]
        record["error"] = api["error"]
        return record

    content = extract_content(api["raw"])
    pj = extract_json_from_text(content)
    record["status"] = "ok" if pj else "parse_fail"
    if pj is None:
        record["content_raw"] = content[:2000]
        return record

    ai_dims = {k: (pj.get(k) or {}).get("status", "?") for k in DIMS}
    record["ai_layer"] = pj
    record["ai_dims"] = ai_dims
    record["ai_overall"] = pj.get("overall", "?")
    record["final_overall"] = derive_final_overall(rule_result, ai_dims)
    return record


# ============================================================
# 区块 ⑩ ｜ 输出格式化
# ------------------------------------------------------------
# 【模块整体在干嘛】
#   把 diagnose_script 返回的"原始结果 dict"转换成两种格式：
#   一种是打印到屏幕的格式化文本（人类阅读用），
#   另一种是落到 results/diagnose/ 目录的 JSON 文件（机器审阅/留档用）。
# ------------------------------------------------------------
# 【具体解释】
#   · load_samples：辅助函数，从 data/scripts.csv 读取样本库，供 cmd_batch 使用
#   · 格式化打印：把规则/维度判定按表格样式输出到终端，
#     关键档位用颜色或符号标记，方便人工快速浏览
#   · 落盘 JSON：写到 results/diagnose/...json，
#     含时间戳、脚本 ID、维度判定、原文，保留完整审计痕迹
# ============================================================


def load_samples() -> dict[str, dict]:
    with open(SCRIPTS_CSV, encoding="utf-8-sig", newline="") as f:
        return {r["sample_id"]: r for r in csv.DictReader(f)}


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------

def format_record(rec: dict, verbose: bool = False) -> str:
    lines = []
    rl = rec["rule_layer"]
    r2, r3, r4 = rl["R2_keyword_coverage"], rl["R3_risk_words"], rl["R4_cta_present"]
    lines.append(f"── 规则层 R1-R4 ─────────────────────────")
    lines.append(f"  R1 Brief 确定性：{rl['R1_brief_complete']['status']}")
    lines.append(f"  R2 关键词植入：{r2['status']}" + (f"（缺失：{'、'.join(r2['missing_categories'])}）" if r2["missing_categories"] else ""))
    r3_extra = f"（命中：{', '.join(h['word'] for h in r3['hits'])}）" if r3["hits"] else ""
    lines.append(f"  R3 禁用词扫描：{r3['status']}{r3_extra}")
    lines.append(f"  R4 CTA 词检查：{r4['status']}")

    if rec["status"] != "ok":
        lines.append(f"── AI 层：失败（{rec.get('error_kind', rec['status'])}）──")
        lines.append(f"  {rec.get('error', rec.get('content_raw', ''))[:200]}")
        return "\n".join(lines)

    lines.append("── AI 层 A1-A6（语义诊断）─────────────")
    for k in DIMS:
        d = rec["ai_layer"].get(k) or {}
        lines.append(f"  {k} {d.get('status', '?')}")
        if verbose:
            reason = (d.get("reason") or "").replace("\n", " ")
            lines.append(f"      依据：{reason[:120]}{'…' if len(reason) > 120 else ''}")
            sugg = (d.get("suggestion") or "").replace("\n", " ")
            if sugg:
                lines.append(f"      建议：{sugg[:100]}{'…' if len(sugg) > 100 else ''}")
    lines.append("── 整体判定 ────────────────────────────")
    lines.append(f"  AI 自报 overall：{rec['ai_overall']}")
    lines.append(f"  最终整体判定（规则层+AI 层三档推导）：{rec['final_overall']}")
    hri = rec["ai_layer"].get("human_review_items") or []
    if hri:
        lines.append("  提请人工复核：")
        for i, item in enumerate(hri, 1):
            lines.append(f"    {i}. {item}")
    lines.append(f"（耗时 {rec['elapsed_sec']}s｜prompt {rec['prompt']}｜Brief：{rec.get('brief_source', '—')}）")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 子命令：diagnose / batch / eval / web
# ---------------------------------------------------------------------------

# ============================================================
# 区块 ⑪ ｜ 四个子命令
# ------------------------------------------------------------
# 【模块整体在干嘛】
#   把 diagnose/batch/eval/web 四种使用方式分别实现成函数，
#   让用户能在命令行选一种来用。每个函数都对应文件头部说明的一个子命令。
# ------------------------------------------------------------
# 【具体解释】
#   · cmd_diagnose（单条诊断）：
#       解析 --file 或位置参数 → 调 diagnose_script → 打印 + 落盘
#   · cmd_batch（批量诊断）：
#       读 data/scripts.csv 全量（或指定的 S001 S002...）
#       → 逐条 diagnose_script → 结果写到 results/app_raw/
#   · cmd_eval（评估对比）：
#       把 results/app_raw/ 里的 AI 判定和人工标注 data/human_labels.json 对比，
#       逐维度算吻合率
#   · cmd_web（网页界面）：
#       启动一个本地网页服务，提供 GUI 给非技术用户单条诊断
# ============================================================


def cmd_diagnose(args) -> int:
    if args.file:
        script = Path(args.file).read_text(encoding="utf-8").strip()
    elif args.text:
        script = args.text.strip()
    else:
        print("请提供脚本文本或 --file 路径")
        return 1
    if not script:
        print("脚本文本为空")
        return 1

    print(f"诊断中（{len(script)} 字，prompt {args.prompt}）…")
    rec = diagnose_script(script, prompt_name=args.prompt)
    print(format_record(rec, verbose=True))

    DIAGNOSE_DIR.mkdir(parents=True, exist_ok=True)
    out = DIAGNOSE_DIR / f"{rec['sample_id']}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)
    print(f"\n完整结果已保存：{out}")
    return 0


def cmd_batch(args) -> int:
    samples = load_samples()
    ids = args.ids or sorted(samples.keys())
    out_dir = RESULTS_DIR / "app_raw"
    out_dir.mkdir(parents=True, exist_ok=True)

    ok = 0
    for sid in ids:
        if sid not in samples:
            print(f"[SKIP] {sid} 不在 data/scripts.csv")
            continue
        print(f"--- {sid}（{len(samples[sid]['script'])} 字）---")
        rec = diagnose_script(samples[sid]["script"], prompt_name=args.prompt, sample_id=sid)
        if rec["status"] == "ok":
            ok += 1
            print(f"  {format_record(rec).splitlines()[-1]}")
            print(f"  最终整体：{rec['final_overall']}｜AI overall：{rec['ai_overall']}")
        else:
            print(f"  [FAIL] {rec.get('error_kind')}: {rec.get('error', '')[:100]}")
        with open(out_dir / f"{sid}.json", "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=2)

    print(f"\n批量完成：{ok}/{len(ids)} 成功，结果在 {out_dir}")
    return 0


def cmd_eval(args) -> int:
    """评估 AI 判定 vs 人工标注逐项吻合率。默认复用既有 raw 结果（老 11 条=results/v3.9_raw，新 5 条=results/v4.0_raw）。"""
    samples = load_samples()
    if args.batch == "old":
        ids = [sid for sid in sorted(samples) if sid <= "S011"]
    elif args.batch == "new":
        ids = [sid for sid in sorted(samples) if sid > "S011"]
    else:
        ids = sorted(samples)

    brief = load_brief()
    total = match = 0
    per_sample = []
    print(f"{'ID':<6}{'A1':<10}{'A2':<10}{'A3':<10}{'A4':<10}{'A5':<10}{'A6':<10}{'overall':<18}{'吻合'}")
    for sid in ids:
        raw_dir = "v3.9_raw" if sid <= "S011" else "v4.0_raw"
        raw_path = RESULTS_DIR / raw_dir / f"{sid}.json"
        if not raw_path.exists():
            print(f"[SKIP] {sid} 无结果文件（{raw_path}）")
            continue
        pj = json.loads(raw_path.read_text(encoding="utf-8"))["parsed_json"]
        s = samples[sid]
        dims = {k: (pj.get(k) or {}).get("status", "?") for k in DIMS}
        cells, n_ok = [], 0
        for k in DIMS:
            ok = s[f"human_{k}"] == dims[k]
            total += 1
            match += ok
            n_ok += ok
            cells.append("OK" if ok else f"X({dims[k]})")
        ok = s["reviewer_label"] == pj.get("overall")
        total += 1
        match += ok
        n_ok += ok
        cells.append("OK" if ok else f"X({pj.get('overall')})")
        per_sample.append((sid, n_ok))
        print(f"{sid:<6}" + "".join(f"{c:<10}" if i < 6 else f"{c:<18}" for i, c in enumerate(cells)) + f"{n_ok}/7")

    if total:
        print(f"\n逐项吻合（A1-A6+overall）：{match}/{total} = {match / total * 100:.1f}%")
    return 0


def cmd_web(args) -> int:
    """启动本机网页界面（详见 webapp.py）。"""
    try:
        import webapp  # noqa: F401
    except ImportError:
        print("webapp.py 不存在")
        return 1
    import webbrowser
    from http.server import ThreadingHTTPServer
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), webapp.make_handler())
    url = f"http://127.0.0.1:{args.port}"
    print(f"网页版已启动：{url}（Ctrl+C 退出）")
    webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已退出")
    return 0


# ---------------------------------------------------------------------------
# argparse
# ---------------------------------------------------------------------------

# ============================================================
# 区块 ⑫ ｜ 入口 argparse + main
# ------------------------------------------------------------
# 【模块整体在干嘛】
#   把命令行参数（python app.py diagnose ... 之类）解析成具体的子命令和参数，
#   并在 main() 里派发给上面 4 个 cmd_ 函数之一去执行。
#   是整个文件的"总收银台"：负责接单 + 派发。
# ------------------------------------------------------------
# 【具体解释】
#   · argparse 配置：定义 4 个子命令 + 各自参数
#       （--file / --port / --batch）
#   · main 函数：解析参数 → 根据 args.cmd 派发 → 返回退出码
#   · if __name__ == "__main__" 入口：
#       直接 python app.py 跑会执行 main()；
#       其他文件 import 这个 app 不会触发
# ============================================================


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="app.py",
        description="AI 香氛短视频内容诊断（网易严选 0感香氛）— 统一主入口",
    )
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("diagnose", help="单条脚本诊断")
    sp.add_argument("text", nargs="?", help="脚本文本（或用 --file）")
    sp.add_argument("--file", help="从文本文件读脚本")
    sp.add_argument("--prompt", default=DEFAULT_PROMPT, help=f"prompt 版本（默认 {DEFAULT_PROMPT}）")
    sp.set_defaults(func=cmd_diagnose)

    sp = sub.add_parser("batch", help="批量诊断样本库脚本")
    sp.add_argument("ids", nargs="*", help="样本 ID（默认全量）")
    sp.add_argument("--prompt", default=DEFAULT_PROMPT, help=f"prompt 版本（默认 {DEFAULT_PROMPT}）")
    sp.set_defaults(func=cmd_batch)

    sp = sub.add_parser("eval", help="AI 判定 vs 人工标注吻合率评估")
    sp.add_argument("--batch", choices=["old", "new", "all"], default="all", help="评估批次（默认 all）")
    sp.set_defaults(func=cmd_eval)

    sp = sub.add_parser("web", help="启动本机网页界面")
    sp.add_argument("--port", type=int, default=8501)
    sp.set_defaults(func=cmd_web)
    return p


def main() -> int:
    # Windows 控制台默认 GBK，强制 stdout 用 UTF-8 避免中文/符号编码错误
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
