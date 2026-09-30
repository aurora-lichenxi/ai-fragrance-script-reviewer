# -*- coding: utf-8 -*-
"""追加新 5 条脚本（S012-S016）到 data/scripts.csv，人工标注取自 新5条人工review.docx
口径：维度档位取表2（AI Semantic Diagnosis），整体取表3 首行"""
import csv

CSV = r"C:\Users\HP\Desktop\ai-fragrance-review\data\scripts.csv"

new_rows = [
    {
        "sample_id": "S012", "product_brief": "PB01", "source_type": "douyin_transcript",
        "privacy_note": "",
        "script": ("今天我挑了一个香薰，很多兄弟可能不理解啊，大老爷们买这干什么？它的除菌率和除味率都是 99 以上，有什么用啊？"
                   "首先它是个香薰，它能除味，大家第一印象就是放客厅啊，或者放卧室，你往那一放确实很好用，它扩味也快。"
                   "再一个，很多兄弟这个鞋柜，尤其运动完、打完球，现在还是夏天，全是味，你往那一放，它确实很管用。"
                   "再比如说放衣柜，基本上一到两天你衣服就带那个香味，它不腻，没有香水那种刻意，但是很好闻。"
                   "据品牌方说，它还能除甲醛，也有那个检测报告什么的，这个我不是很清楚啊，如果真有这个问题的话，还是多通风吧。\n"
                   "很多香薰啊，它跑一半它不跑了。这个是倒着放，不会这个问题。"
                   "用的话，从这儿给它撕开，把这一拧，这盖给它拧下来，再给它安回去，哎，这样一放就好了。"
                   "它味道还挺多的啊，这两个应该是偏冷一点的，这个橘子味，还有一个味是什么？应该是偏暖一点的，大家看自己喜欢。"
                   "它一瓶大概能放两到三个月左右，价格是 25 块钱一瓶，它现在应该是有券，大家自己点开看看能领多少，有需要的下单，好吗？"),
        "reviewer_label": "Needs Revision",
        "human_A1": "Pass", "human_A2": "Pass", "human_A3": "Pass",
        "human_A4": "Reminder", "human_A5": "Pass", "human_A6": "Pass",
    },
    {
        "sample_id": "S013", "product_brief": "PB01", "source_type": "douyin_transcript",
        "privacy_note": "",
        "script": ("如果你们家卫生间也总是臭臭的，真的一定要试试网易严选这款倒置香氛。"
                   "我也就打开这个紫色“鸢尾邂逅”几分钟，整个卫生间都是干净清雅的鸢尾花香。"
                   "还有这个“佛手柑橘”，就像在房间里挤爆了一整颗橘子，完全不是那种冲鼻子的工业香精味，是那种温润柔和的果香，高级又好闻。"
                   "它不是靠香味去硬压住臭味，是真的能把异味给分解掉，再慢慢散出很自然柔和的淡香。"
                   "还是特殊倒置的设计，锁香扩香都特别稳定，卧室、玄关、客厅随便放，整个家走到哪都是很温柔治愈的舒服味道。"),
        "reviewer_label": "Pass",
        "human_A1": "Pass", "human_A2": "Pass", "human_A3": "Pass",
        "human_A4": "Pass", "human_A5": "Reminder", "human_A6": "Reminder",
    },
    {
        "sample_id": "S014", "product_brief": "PB01", "source_type": "douyin_transcript",
        "privacy_note": "",
        "script": ("不知道你们有没有这种感觉，到了换季就觉得房间里闷闷的，整个人都昏昏沉沉的，很没劲。"
                   "但是我最近发现，闻一闻植物的清香就特别地治愈放松。"
                   "这是我最近新发现的，能完美还原植物花香的香氛——网易严选新出的灵感倒置香氛，"
                   "就这么一撕、一开、一倒，盖子里是七面的扩香棉片，能让整个家里都变得香香的，很舒畅。\n"
                   "这个“鸢尾邂逅”跟我那瓶香加子邂逅一样，酸酸甜甜的水果味中又有一丝花香，前调很清爽，后调是那种疗愈舒缓的高级香。"
                   "我每次闻到这个味道就觉得活力满满，很有力量。"
                   "他们家这个可不是单纯只是有香味，而是每款香味都添加了独特的“情绪香氛技术”。"
                   "像这瓶是添加的活力香氛技术，很能缓解不好的情绪。\n"
                   "我每次沉闷的时候闻到就觉得茅塞顿开，真的很能安抚到我。"
                   "而且你仔细看，它里边还有紫晶亮片，好美，紫气东来也是好兆头。"
                   "外形更是寓意着霉运清零、好运来临，妥妥的好运能量香。"
                   "它的味道也是很高级、很有层次感，不是用浓香去压臭味，而是从源头上分解异味后再释放香味。"
                   "像我家有小孩嘛，这种又能抑菌，我就很喜欢。而且都是植萃配方，家里有小宝宝或者毛孩子的，用起来也很安心。\n"
                   "我家客厅放的是粉色的“桃气玫瑰”，就是那种初夏刚刚绽放的桃花香气，遇到晚风后留下的淡淡玫瑰香，闻起来很有幸福感，就是家的温暖味道。"
                   "这个香氛真的是能调动治愈情绪的，甜甜的味道就是会增加愉悦幸福感。"
                   "果然玄学也是科学，最打动我的就是它那句 slogan：“让好运被承接，主动开启好运循环。”"
                   "30+ 的我，生活中的烦心琐事太多太多，很多都不能马上解决，但至少可以把窒息的沉闷感倒空归零，让大脑换上一瓶又甜又软的新风，疗愈一下自己。"),
        "reviewer_label": "Needs Revision",
        "human_A1": "Pass", "human_A2": "Pass", "human_A3": "Pass",
        "human_A4": "Reminder", "human_A5": "Reminder", "human_A6": "Reminder",
    },
    {
        "sample_id": "S015", "product_brief": "PB01", "source_type": "douyin_transcript",
        "privacy_note": "",
        "script": ("哇，你知道这有多香吗？你只要把它放 5 分钟，你整个家里都是香香的。"
                   "特别是这个“佛手柑橘”，它的味道非常地高级，里边还带这种亮晶晶的。"
                   "如果你喜欢那种木质调中性香，你可以试试“无极雪松”。"
                   "这个你放哪都行，客厅啊、卧室啊、卫生间啊，持久挥发香味，淡雅却不浓郁。"
                   "还是网易严选他们家出的，看看无极雪松里边的小亮晶晶，天呐，超级漂亮！"
                   "如果你想要家里香香的，那这个空气除味香氛，你必须得给我安排上。"),
        "reviewer_label": "Pass",
        "human_A1": "Pass", "human_A2": "Reminder", "human_A3": "Pass",
        "human_A4": "Pass", "human_A5": "Pass", "human_A6": "Pass",
    },
    {
        "sample_id": "S016", "product_brief": "PB01", "source_type": "douyin_transcript",
        "privacy_note": "",
        "script": ("我上次去朋友新家，他那个房间里就总是有一股奇怪的板材味。"
                   "我直接给他买了网易严选的灵感倒置香氛，尤其是这个金灿灿的，不仅适合秋冬，搬家乔迁礼它也超级合适。"
                   "这个是网易严选做的新款升级，因为我用他们家的这个香氛确实时间很久了，"
                   "其他的我感觉都有点杂七杂八的“以香盖臭、以次充好”，甚至母婴或养狗养宠物的家庭是没有办法用的，这个它可以，因为它有相关的安全报告。"
                   "而且它还能去板材的甲醛味、浴室的尿骚味、还有客厅抽烟的那种尼古丁的味道。"
                   "甚至新版这个升级里面，它把一块海绵升级成了这种立体环绕式的海绵，"
                   "就哪怕滴一滴进去，整个房间都会散出这种淡淡的清甜的花果香，甚至这个味道散得又快又均匀，而且对着鼻闻也是 OK 的，不会有刺激性的味道。"
                   "但是最让我觉得喜欢的，是它这里面增加了一些这样子的小晶石，每个里面都有，巨漂亮。"
                   "搬家的小伙伴，或者你的长时间的柜子里还有一股奇怪的板材臭味，这个一定要试一下，这种小物件带来的微小的治愈感，真的无法比拟。"),
        "reviewer_label": "Needs Revision",
        "human_A1": "Pass", "human_A2": "Pass", "human_A3": "Pass",
        "human_A4": "Reminder", "human_A5": "Reminder", "human_A6": "Reminder",
    },
]

# 检查是否已存在，避免重复追加
with open(CSV, encoding="utf-8-sig", newline="") as f:
    existing = {r["sample_id"] for r in csv.DictReader(f)}
dup = [r["sample_id"] for r in new_rows if r["sample_id"] in existing]
if dup:
    print(f"[SKIP] 已存在，不追加：{dup}")
else:
    fieldnames = ["sample_id", "product_brief", "script", "source_type", "privacy_note",
                  "reviewer_label", "human_A1", "human_A2", "human_A3", "human_A4", "human_A5", "human_A6"]
    with open(CSV, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        for r in new_rows:
            w.writerow({k: r[k] for k in fieldnames})
    print(f"已追加 {len(new_rows)} 条：S012-S016")

# 校验
with open(CSV, encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))
print(f"当前共 {len(rows)} 条样本")
for r in rows[-5:]:
    print(f"  {r['sample_id']} script={len(r['script'])}字 label={r['reviewer_label']} "
          f"A1-A6={r['human_A1']},{r['human_A2']},{r['human_A3']},{r['human_A4']},{r['human_A5']},{r['human_A6']}")
