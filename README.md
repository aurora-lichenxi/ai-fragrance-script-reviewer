# AI香氛视频脚本诊断工具 1.0

[![Download v1.0](https://img.shields.io/badge/⬇_Download-v1.0_exe-blue)](https://github.com/aurora-lichenxi/ai-fragrance-script-reviewer/releases/download/v1.0/AI-fragrance-script-reviewer-v1.0.exe)

用「确定性规则层 + LLM 语义诊断层」对抖音短视频口播脚本做机器 Review，替代人工初审。
**核心成果：Prompt v4.0 在 11 条定版集上逐项吻合率 74/77 = 96.1%**（口径修正后 98.7%），达到 ≥95% 立项目标。

> 2.0 迭代方向：通用视频脚本 AI 诊断工具——输入任何产品 brief → 自动生成诊断 prompt（可人工核查修改）→ 双层分析 → 输出判断及建议。1.0 已上线「输入 Brief 自动解析」能力。

---

## 一、最快上手（普通使用者，4 步）

1. **下载**：从 [Releases v1.0](https://github.com/aurora-lichenxi/ai-fragrance-script-reviewer/releases/download/v1.0/AI-fragrance-script-reviewer-v1.0.exe) 下载 `AI-fragrance-script-reviewer-v1.0.exe`（单文件，免安装），放到任意文件夹双击运行；
2. **填 Key**：首次使用会自动弹出浏览器页面，在「API Key」一栏填入你自己的阿里云 DashScope Key（[百炼平台](https://bailian.console.aliyun.com/) 免费申请），点「保存到本机」——Key 只保存在你自己电脑的 .env 文件里；
3. **解析 Brief**：把产品 brief 原文粘贴进「输入 Brief 自动解析」卡片，点「解析 Brief」自动生成结构化信息，缺少必需信息会提示补充（1.0 的诊断仍基于内置 0感香氛 brief，brief 草稿将在 2.0 接入诊断管线）；
4. **诊断**：把待审的口播脚本粘贴进输入框，点「开始诊断」，约 30-60 秒后得到：
- **整体判定**（Pass 通过 / Reminder 提醒修改 / Needs Revision 需修改）
- **规则层 R1-R4**：Brief 确定性 / 关键词植入 / 禁用词扫描 / CTA 词（字面匹配）
- **AI 语义诊断 A1-A6**：开头钩子 / 痛点共鸣 / 方案卖点 / 证明可信度 / CTA 质量 / 转化逻辑（含证据、原因、建议）
- **提请人工复核项**：规则层与 AI 层提交人工确认的事项汇总
- **人工判定**：对 A1-A6 与整体判定做人工确认并提交（保存于本机 results/feedback/，作为后续迭代依据）

> 🔒 程序完全在本机运行，不收集、不上传任何数据；诊断请求由本机直连阿里云 DashScope。
> 首次双击若弹出 Windows SmartScreen 提示，点「更多信息 → 仍要运行」即可（未购买代码签名证书所致）。

## 二、开发者用法（命令行）

项目零第三方依赖（纯 Python 标准库 + urllib）：

```bash
# 网页界面（同 exe）
python app.py web

# 单条诊断
python app.py diagnose "脚本文本……"
python app.py diagnose --file 脚本.txt

# 批量诊断样本库（data/scripts.csv）
python app.py batch S001 S002
python app.py batch                 # 全量

# 评估：AI 判定 vs 人工标注逐项吻合率
python app.py eval --batch old      # 老 11 条定版集 → 96.1%
python app.py eval --batch new      # 新 5 条盲测集 → 57.1%
```

配置：项目根目录 `.env`（参考 `.env.example`）：`QWEN_API_KEY` / `QWEN_BASE_URL` / `QWEN_MODEL`（默认 qwen-plus，temperature=0）。

## 三、项目结构

```
ai-fragrance-review/
├── app.py                # 统一主入口：diagnose / batch / eval / web
├── rules.py              # 规则层 R1-R4（纯字面匹配，不调 AI）
├── data/
│   ├── scripts.csv       # 评测样本 16 条（S001-S016，人工标注齐全）
│   ├── briefs/
│   │   ├── brief.json            # PB01 产品 brief（v2.4：content_reference + rule_config 双层）
│   │   └── brief_template.json   # brief 自由文本→结构化抽取模板（实验功能）
│   └── human_review/
│       ├── human_labels.json     # 评测用人工标注（结构化 JSON）
│       └── human_review_text.txt # 人工 Review 原文（带 yellow 高亮行内批注）
├── prompts/              # 5 个关键迭代版本存档：v1 / v2 / v3 / v4 / v4.1
├── results/              # 跑批原始输出 + diagnose/（单条诊断落盘）+ feedback/（人工审核表）
├── eval.csv              # D6：16 条 × 7 项 AI vs 人工逐项对照表
├── bad_cases.md          # D6：历轮 Bad Case 汇总（v1 → v4.1）
├── dist/
│   └── AI香氛视频脚本诊断工具1.0.exe   # 单文件可分发
├── archive/              # 「未归类」：GUI 工具包 + 历史脚本 + 文档归档
│   ├── gui/              #   GUI 网页版 + exe 打包入口（如需重打包先拷回根）
│   │   ├── webapp.py                 # 本机网页界面（标准库 http.server，无前端依赖）
│   │   ├── launcher.py               # exe 打包入口（PyInstaller）
│   │   └── 香氛脚本诊断工具.spec     # PyInstaller 打包配置（已同步 brief 新路径）
│   ├── history/          #   历轮跑批/对比/报告/导出/解析脚本（迭代轨迹归档）
│   │                         · run_v1/v2/v3.py            — v1-v3 各版本一次性跑批入口
│   │                         · compare_v38/v39/new5.py    — 吻合率统计
│   │                         · make_report_v1/v2/v3.py    — 各阶段报告生成
│   │                         · export_d6.py               — eval.csv 导出
│   │                         · dump_v4_new5.py / append_new5.py — v4 调试 & 样本追加
│   │                         · parse_human_labels.py / reparse_v1_raw.py — 数据预处理
│   ├── docs/             #   历史说明文档
│   │   ├── scripts_字段说明.md       # scripts.csv 字段结构详解
│   │   └── project_brief.md          # 项目早期 brief 文档
│   └── data_extras/
│       └── v4_new5_full.txt          # v4 新 5 条完整批跑日志
├── requirements.txt      # 仅 2 依赖：python-dotenv + requests
├── .env.example          # 环境变量样例（QWEN_API_KEY / BASE_URL / MODEL / TIMEOUT）
└── README.md
```

## 四、架构：两层判定

```
口播脚本 ──┬─→ 规则层 R1-R4（rules.py，字面匹配，毫秒级）
           │      R2 关键词缺失 / R3 命中风险词 → 整体直接 Needs Revision
           │
           └─→ AI 层 A1-A6（qwen-plus × prompt v4.0，语义诊断，~30-60s）
                  A1 开头钩子  A2 痛点共鸣  A3 方案卖点
                  A4 证明可信度  A5 CTA 质量  A6 转化逻辑
                          │
                          ▼
              三档整体推导：任一 NR→NR；无 NR 有 Rem→Rem；全 Pass→Pass
              （+ human_review_items：提请人工复核）
```

规则层管「找得到/找不到」的确定性检查，AI 层管「写得好不好」的语义判断，两层结果合并为最终整体判定——AI 不越权做词面裁定，规则不做语义理解。

## 五、Prompt 迭代轨迹（吻合率 = 每样本 7 项 × 样本数，对人工标注）

| 阶段     | 版本           | 测试集        | 吻合率                                             |
| ------ | ------------ | ---------- | ----------------------------------------------- |
| 冷启动    | v1（235 字精简版） | 11 条       | 暴露空泛/漏项/无证据 3 类问题                               |
| 规则注入   | v2           | 11 条       | ~57%                                            |
| 迭代     | v3.0 → v3.8  | 试跑+泛化+全量   | 42.9% → 85.7%                                   |
| **定版** | **v4.0**     | **11 条全量** | **74/77 = 96.1%**（口径修正 98.7%）                   |
| 泛化盲测   | v4.0         | 新 5 条      | 20/35 = 57.1%（约一半偏差源于新批次人工口径漂移，详见 bad_cases.md） |

迭代方法论：**明晰规则 + 例子辅助理解**（不加例子让 AI 机械按例判）；全程 19 轮记录见 `工作文件记录/promptv3-迭代记录.md`。

## 六、注意事项

- 诊断结果**仅供审核参考**，`human_review_items` 列出的事项需人工定夺；
- 新 5 条盲测暴露的泛化边界（A4 偏松 3 处、R3『第一印象』误报、人工口径漂移）已归档于 `bad_cases.md` v4.1 候选清单，本轮不做迭代（用户拍板：v4.0 定版交付）；
- 若换用其他模型，请先跑 `python app.py eval --batch old` 回归验证（当前基线 qwen-plus temperature=0）。
