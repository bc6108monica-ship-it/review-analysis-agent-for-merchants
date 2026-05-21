import openai
import os
import json
from dotenv import load_dotenv

# ====================================================================
# 第一步：加载 .env 文件 + 配置大模型客户端
# ====================================================================

# 【一行代码自动加载 .env 文件里的所有变量到系统环境变量中】
#   .env 文件就放在项目根目录，内容长这样：
#       DEEPSEEK_API_KEY=sk-你的key
#   这行代码执行后，os.getenv("DEEPSEEK_API_KEY") 就能读到了。
#   好处：key 只存在 .env 文件里，不会出现在代码中，也不用每次手动 export/setx。
load_dotenv()

api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    raise RuntimeError(
        "未找到 API Key！请在项目根目录创建 .env 文件，内容为：\n"
        "    DEEPSEEK_API_KEY=sk-你的key"
    )

# 【创建客户端对象】
#   openai.OpenAI(...) 返回的就是一个可以跟大模型对话的"客户端"。
#   后面所有 API 调用都是通过 client.xxx() 来发的。
client = openai.OpenAI(
    api_key=api_key,                             # 自动从 .env 读取，无需手动设置
    base_url="https://api.deepseek.com"          # API 服务器地址（DeepSeek 的）
    # ↑ 如果你用的是 OpenAI，改成 "https://api.openai.com/v1"
    #   如果你用的是通义千问，改成 "https://dashscope.aliyuncs.com/compatible-mode/v1"
    #   换哪个模型就换哪个地址，代码其他部分不用动
)


# ====================================================================
# 第二步：定义"工具说明书"（Tools Definition）
# ====================================================================
#
# 这一段是整个 Agent 开发里最容易懵的地方，逐个变量拆开讲：
#
# ┌─ 整体概念 ──────────────────────────────────────────────────┐
# │                                                              │
# │  tools 就是一个"菜单"，你给大模型看这份菜单，告诉它：          │
# │  "如果你觉得需要，可以点这个菜（调用这个函数），               │
# │   但点的时候必须告诉我这两个参数分别是什么。"                  │
# │                                                              │
# │  大模型不会真的执行函数，它只返回一个 JSON 订单给你，          │
# │  由你的 Python 代码来"做菜"（执行逻辑）。                     │
# │                                                              │
# │  类比：你去餐厅点菜，你在纸上写了"宫保鸡丁，辣度=中辣"，       │
# │  然后把这纸递给厨房，厨房才真的开始炒菜。                     │
# │  大模型 = 写纸的人，你的代码 = 厨房。                         │
# │                                                              │
# └──────────────────────────────────────────────────────────────┘

tools = [
    # 【最外层：tools 是个 list】
    #   为什么是 list？因为你可以定义多个工具！
    #   比如你还能加"查物流"、"搜商品"、"创建工单"等等。
    #   大模型会从这些工具里选一个（或多个）来调用。
    {
        # ============================================================
        # 【第一层：Tool 对象】—— 描述一个"型号"的工具
        # ============================================================

        # ---------- type ----------
        # 含义：声明这个工具的"类型"
        # 固定写死 "function"，因为现在 OpenAI 只有 function 这一种类型。
        # 必须写，否则 API 会报错。你就当它是固定模板。
        "type": "function",

        # ---------- function ----------
        # 含义：这个工具的"具体说明书"，是个嵌套对象
        # 下面 name / description / parameters 都是说明书里的条目
        "function": {

            # =====================================================
            # 【第二层：Function 定义】—— 描述具体要干什么
            # =====================================================

            # ---------- name ----------
            # 含义：给这个工具起个名字，让别人（你的代码）能识别它
            # 大模型返回时会带这个名字，你的代码通过名字判断调了哪个工具
            # 类比：函数名，就像 print() 里面的 print
            "name": "classify_review",

            # ---------- description ----------
            # 含义：用自然语言描述这个工具是干什么的
            # ★★★ 这是最重要的字段！大模型就是靠读这行字来决定
            #     "现在该不该调用这个工具"。
            # 写得越清楚，大模型越不会乱调。
            # 类比：函数注释/docstring，告诉调用者什么时候用这个函数
            "description": "将用户评论分类为：complaint（投诉）/ praise（好评）/ suggestion（建议）",

            # ---------- parameters ----------
            # 含义：这个工具的"入参说明书"——大模型调用它时需要传什么参数
            # 用的是 JSON Schema 标准格式（一种描述 JSON 结构的规范）
            # 类比：Python 函数签名里的 (review_text: str) —— 规定了参数类型和含义
            "parameters": {

                # =================================================
                # 【第三层：Parameters 结构】—— JSON Schema 格式
                # =================================================

                # ---------- type ----------
                # 含义：参数的整体数据类型。这里写 "object" 表示参数是一个对象/dict
                # 因为 function calling 的参数永远是 key-value 格式，所以永远写 "object"
                "type": "object",

                # ---------- properties ----------
                # 含义：定义这个对象有哪些"字段/属性"
                # 每个 key 是一个参数名，value 是这个参数的"说明书"
                # 类比：你往一个函数里传的是结构体，properties 就是结构体的字段列表
                "properties": {

                    # ---------- category ----------
                    # 含义：你自己定义的参数名，叫啥都行（叫 xyz 也没问题）
                    #    但起个好名字有利于大模型理解和你的代码可读性
                    "category": {

                        # --- type ---
                        # 含义：这个参数的数据类型，string = 字符串
                        # 常用值："string" / "number" / "integer" / "boolean" / "array" / "object"
                        "type": "string",

                        # --- enum ---
                        # 含义：枚举值，限制这个参数只能从这几个选项里选
                        # ★ 不是必填字段，但写了就能约束大模型不乱造值
                        # 如果不写 enum，大模型可能返回 "差评"/"负面"/"bad review"
                        # 写了 enum，它就只返回 complaint / praise / suggestion 中的一个
                        "enum": ["complaint", "praise", "suggestion"],

                        # --- description ---
                        # 含义：用自然语言描述这个参数代表什么意思
                        # 大模型会读这个来理解"category 这个字段该填什么"
                        "description": "评论类别"
                    },

                    # ---------- key_issue ----------
                    # 含义：你自己定义的第二个参数
                    "key_issue": {

                        # --- type ---
                        # 含义：string = 该参数值为字符串
                        "type": "string",

                        # --- description ---
                        # "核心问题或亮点，一句话" → 大模型看到这句，
                        #     就知道要把评论里最重要的信息提炼成一句话填到这里
                        # 一个参数可以不写 enum（不是所有参数都需要限值）
                        "description": "核心问题或亮点，一句话"
                    }
                },

                # ---------- required ----------
                # 含义：必填参数列表
                # 写在 required 里的参数，大模型保证一定会返回
                # 不在这个列表里的参数 = 可选参数
                # 类比：Python 函数没有默认值的参数 = required = True
                "required": ["category", "key_issue"]
            }
        }
    }
]

# ====================================================================
# 第三步：Agent 核心编排函数（整个文件最"自己写的"的部分）
# ====================================================================
#
# 这个函数 = 你的 Agent。
# 它把一个任务（分析评论）拆成两次 API 调用 + 中间手工处理的逻辑。

def analyze_review(review_text):
    """
    输入：一条字符串形式的用户评论
    输出：{"category": 分类, "key_issue": 核心问题, "advice": 建议}
    """

    # ============================================================
    # 第 1 次 API 调用：意图识别（Function Calling 的核心用法）
    # ============================================================

    # 【client.chat.completions.create() = 向大模型发一次请求】
    #   这就是所有大模型 API 的统一入口。不管是聊天、分类、翻译，
    #   还是 Function Calling，全是这个函数。
    response = client.chat.completions.create(

        # --- model ---
        # 含义：选哪个模型来处理你的请求
        # "deepseek-chat" = DeepSeek V3（快，便宜，适合日常任务）
        # "deepseek-reasoner" = DeepSeek R1（慢，贵，但推理能力更强）
        model="deepseek-chat",

        # --- messages ---
        # 含义：发送给大模型的对话内容，是一个 list
        # 因为大模型支持多轮对话，所以用 list 来存所有历史消息
        # 每条消息两个字段：
        #   - role：谁说的？
        #     "system" = 系统指令（设定 AI 人设，如"你是一个客服助手"）
        #     "user"   = 用户说的话
        #     "assistant" = AI 之前的回复
        #   - content：说了什么内容
        messages=[
            {"role": "user", "content": f"分析这条用户评论：{review_text}"}
            # ↑ review_text 是外部传进来的，f-string 拼进去
        ],

        # --- tools ---
        # 含义：把前面定义好的"工具菜单"传进来
        # 大模型拿到这个消息 + 这个工具菜单，
        # 自己判断：要不要调工具？调哪个工具？参数填什么？
        tools=tools,

        # --- tool_choice ---
        # 含义：告诉大模型"在什么情况下调用工具"
        #   "auto" = 大模型自己判断（推荐），它觉得需要就调，不需要就正常回复
        #   "required" = 强制它必须调（如果你100%确定每次都要用工具）
        #   "none" = 禁止它调工具（当普通聊天用）
        #   还可以指定 {"type": "function", "function": {"name": "xxx"}} 强制调某个工具
        tool_choice="auto",

        # --- temperature ---
        # 含义：控制输出的"随机性/创意度"，范围 0~2
        #   接近 0 = 每次输出几乎一样，严谨保守（适合分类、提取结构化数据）
        #   接近 1 = 有一定变化
        #   1.5+ = 放飞自我（适合写诗、起名）
        #   这里用 0.2 是因为"分类"任务需要稳定，不需要创意
        temperature=0.2
    )

    # ============================================================
    # 手工处理：从 API 返回中挖出大模型的"点菜订单"
    # ============================================================

    # 【response.choices = 大模型返回的候选回复列表】
    #   .choices[0] → 通常取第 1 个（因为 n 参数默认=1，只生成一个回复）
    #   .message   → 这轮对话的消息体，里面有 content（纯文本）和 tool_calls（工具调用）
    message = response.choices[0].message

    # 【message.tool_calls = 大模型的"点菜订单"】
    #   如果大模型决定调用工具，这里就是一个 list（可以同时调多个工具）
    #   如果大模型没调用工具，这里就是 None
    tool_calls = message.tool_calls

    # 防御一下：理论上不会发生（我们传了 tools + auto），但健壮代码要有
    if not tool_calls:
        raise ValueError("模型未返回工具调用结果")

    # 【取第一个 tool_call】
    #   为什么是 [0]？因为 tool_calls 是 list，大模型可能一次调多个工具。
    #   本例只有一个工具（classify_review），所以只取第一个。
    tool_call = tool_calls[0]

    # 【tool_call.function.arguments = 大模型填好的参数 JSON 字符串】
    #   比如这个字符串长这样：
    #     '{"category": "complaint", "key_issue": "发货太慢，客服不回消息"}'
    #   json.loads() 把 JSON 字符串变成 Python dict，方便后面取值
    args = json.loads(tool_call.function.arguments)

    category  = args["category"]      # "complaint" / "praise" / "suggestion" 三选一
    key_issue = args["key_issue"]     # 大模型从评论中提炼的一句话关键信息

    # ============================================================
    # 你的业务逻辑：根据分类拼不同的 Prompt
    # ============================================================
    # 这就是"编排"——人的智慧在这里，不是大模型的智慧。
    # 投诉、好评、建议，三种情况要生成的东西完全不同，
    # 所以我们用三个不同的 prompt 模板。

    advice_prompt = {
        "complaint": f"商家收到投诉：{key_issue}，给出3条具体改进建议",
        "praise":    f"商家收到好评：{key_issue}，给出1条如何保持并放大优势的建议",
        "suggestion": f"用户提出建议：{key_issue}，评估可行性并给出回应方向"
    }

    # ============================================================
    # 第 2 次 API 调用：生成优化建议（普通聊天，不用 Function Calling）
    # ============================================================

    advice_response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            # 根据第1步的分类结果选择对应的 prompt
            {"role": "user", "content": advice_prompt[category]}
        ],
        # ★ 注意：这次没有传 tools！所以就是普通的问答，不会触发 Function Calling
        temperature=0.5  # 比分类时略高，让建议写得有点"人味"
    )

    # 【提取纯文本回复】
    #   两次调用的区别：
    #     第1次 → 我们关心 message.tool_calls（结构化的参数）
    #     第2次 → 我们关心 message.content（大模型的自然语言回复）
    advice = advice_response.choices[0].message.content

    # 【打包返回】
    #   把两次调用 + 手工处理的结果汇总成一个 dict，对外就是一个干净的接口
    return {
        "category":  category,   # 投诉/好评/建议
        "key_issue": key_issue,  # 一句话提炼
        "advice":    advice      # 优化建议
    }


# ====================================================================
# 进阶：批量分析函数（Agent 的"批处理模式"）
# ====================================================================
# 实际业务中不是一条条分析的，而是一批评论一起处理，然后出报表。
#
# 数据流：
#   评论列表 → 逐条调用 analyze_review → 汇总统计 → 输出结构化报表

def batch_analyze(reviews):
    """
    输入：评论列表，例如 ["发货太慢", "质量真好", "建议加个功能"]
    输出：结构化汇总报表 dict

    输出结构示例：
    {
        "total": 3,
        "summary": {
            "complaint":  {"count": 1, "percentage": 33.3},
            "praise":     {"count": 1, "percentage": 33.3},
            "suggestion": {"count": 1, "percentage": 33.3}
        },
        "complaint_issues": ["发货太慢"],
        "priority": "complaint",
        "priority_reason": "投诉类占比最高（33.3%），需优先处理",
        "details": [
            {"review": "发货太慢", "category": "complaint", ...},
            ...
        ]
    }
    """
    total = len(reviews)
    if total == 0:
        return {"total": 0, "summary": {}, "complaint_issues": [],
                "priority": None, "priority_reason": "无评论数据", "details": []}

    # ============================================================
    # 第 1 步：逐条调用 analyze_review，收集所有结果
    # ============================================================
    results = []
    for review in reviews:
        r = analyze_review(review)
        results.append(r)

    # ============================================================
    # 第 2 步：按 category 分组统计
    # ============================================================
    # 初始化三个分类的计数器
    bins = {"complaint": [], "praise": [], "suggestion": []}

    for r in results:
        cat = r["category"]
        if cat in bins:
            bins[cat].append(r)
        # 如果 category 不在 bins 里（理论上不会发生，enum 限定了三选一），
        # 就跳过，保证程序不会崩

    # ============================================================
    # 第 3 步：计算各类型占比
    # ============================================================
    summary = {}
    for cat_name in ["complaint", "praise", "suggestion"]:
        count = len(bins[cat_name])
        summary[cat_name] = {
            "count":      count,
            "percentage": round(count / total * 100, 1)  # 保留 1 位小数
        }

    # ============================================================
    # 第 4 步：提取所有 complaint 的 key_issue（投诉清单）
    # ============================================================
    # 这是老板/面试官最爱看的东西：一眼看到所有投诉在说什么
    complaint_issues = [r["key_issue"] for r in bins["complaint"]]

    # ============================================================
    # 第 5 步：决定优先级（按占比排序，谁排第一就优先解决谁）
    # ============================================================
    # 排序规则：先按 count 降序，count 相同按 complaint > suggestion > praise
    priority_order = ["complaint", "suggestion", "praise"]
    sorted_cats = sorted(
        summary.keys(),
        key=lambda c: (summary[c]["count"], -priority_order.index(c)),
        reverse=True
    )
    top_cat = sorted_cats[0]

    priority_label_map = {
        "complaint":  "投诉类",
        "praise":     "好评类",
        "suggestion": "建议类"
    }

    priority_reason = (
        f"{priority_label_map[top_cat]}占比最高"
        f"（{summary[top_cat]['percentage']}%），需优先处理"
    )

    # ============================================================
    # 第 6 步：打包返回
    # ============================================================
    return {
        "total":            total,
        "summary":          summary,
        "complaint_issues": complaint_issues,
        "priority":         top_cat,
        "priority_reason":  priority_reason,
        "details":          results,
    }


# ====================================================================
# 测试（只在直接运行本文件时执行）
# ====================================================================

if __name__ == "__main__":
    """
    运行方式：python ai.py

    测试内容：
      1. 单条评论分析（原始功能）
      2. 批量评论分析（新功能）
    """

    # ---- 单条测试 ----
    print("=" * 60)
    print("  单条评论分析测试")
    print("=" * 60)

    review = "东西质量还行，但是发货太慢了，等了一周还没到，客服也不回消息"
    result = analyze_review(review)

    print(f"  评论类型：{result['category']}")
    print(f"  核心问题：{result['key_issue']}")
    print(f"  优化建议：\n{result['advice']}")

    # ---- 批量测试 ----
    print("\n" + "=" * 60)
    print("  批量评论分析测试")
    print("=" * 60)

    test_reviews = [
        "东西质量还行，但是发货太慢了，等了一周还没到，客服也不回消息",
        "这个耳机的降噪效果绝了，戴上以后地铁噪音完全听不见，推荐！",
        "建议你们加一个深色模式，晚上刷商品太刺眼了",
        "买了两件衣服，一件颜色跟图片差太多退货了，另一件还行",
        "快递包装很好，还送了小礼品，客服态度也特别好",
    ]

    report = batch_analyze(test_reviews)

    print(f"  共 {report['total']} 条评论\n")

    print("  各类型占比：")
    for cat_name, data in report["summary"].items():
        label = {"complaint": "投诉", "praise": "好评", "suggestion": "建议"}[cat_name]
        bar = "█" * int(data["percentage"] / 5)  # 简易柱状图
        print(f"    {label}: {data['count']}条 ({data['percentage']}%) {bar}")

    print(f"\n  投诉清单：")
    for i, issue in enumerate(report["complaint_issues"], 1):
        print(f"    {i}. {issue}")

    print(f"\n  优先处理：{report['priority']}")
    print(f"  原因：{report['priority_reason']}")
    print("=" * 60)