"""
Agent 可视化演示 —— 面试用
运行方式：python app.py
然后在浏览器打开 http://127.0.0.1:7860
"""

import gradio as gr
from ai import analyze_review, client, tools
import json

# ============================================================
# 预设示例评论（面试时快速演示用）
# ============================================================
EXAMPLES = [
    ["东西质量还行，但是发货太慢了，等了一周还没到，客服也不回消息"],
    ["这个耳机的降噪效果绝了，戴上以后地铁噪音完全听不见，推荐！"],
    ["建议你们加一个深色模式，晚上刷商品太刺眼了"],
    ["买了两件衣服，一件颜色跟图片差太多退货了，另一件还行"],
    ["快递包装很好，还送了小礼品，客服态度也特别好"],
]

# ============================================================
# 核心处理函数：拆开两步显示
# ============================================================
def process_review(review_text):
    """拆解 Agent 两步过程，让面试官看到中间结果"""
    if not review_text.strip():
        return "请先输入评论内容", "", "", ""

    # ---- 第 1 步：意图识别 ----
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": f"分析这条用户评论：{review_text}"}],
        tools=tools,
        tool_choice="auto",
        temperature=0.2,
    )
    tool_call = response.choices[0].message.tool_calls[0]
    args = json.loads(tool_call.function.arguments)
    category = args["category"]
    key_issue = args["key_issue"]

    # 把第 1 步大模型返回的原始 JSON 展示出来
    step1_raw = json.dumps(args, ensure_ascii=False, indent=2)

    # 分类标签映射
    label_map = {
        "complaint": "投诉",
        "praise": "好评",
        "suggestion": "建议",
    }

    # ---- 第 2 步：生成建议 ----
    advice_prompt = {
        "complaint":  f"商家收到投诉：{key_issue}，给出3条具体改进建议",
        "praise":     f"商家收到好评：{key_issue}，给出1条如何保持并放大优势的建议",
        "suggestion": f"用户提出建议：{key_issue}，评估可行性并给出回应方向",
    }
    used_prompt = advice_prompt[category]

    advice_response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": used_prompt}],
        temperature=0.5,
    )
    advice = advice_response.choices[0].message.content

    return (
        f"{label_map[category]}",
        key_issue,
        step1_raw,
        f"**发送给大模型的 Prompt：**\n\n{used_prompt}",
        advice,
    )


# ============================================================
# 构建 Web 界面
# ============================================================
with gr.Blocks(title="AI Agent - 评论分析演示") as demo:
    gr.Markdown(
        """
        # AI Agent：用户评论分析 + 优化建议生成

        **面试演示** — 输入一条电商评论，Agent 自动完成两步推理：

        **第 1 步** → 大模型调用 Function Calling，结构化输出「评论类型」和「核心问题」
        **第 2 步** → 根据分类结果，拼装对应 Prompt 再次调大模型，生成商家优化建议
        """
    )

    # ---- 输入区 ----
    with gr.Row():
        with gr.Column(scale=2):
            input_box = gr.Textbox(
                label="输入用户评论",
                placeholder="例如：东西质量还行，但是发货太慢了...",
                lines=3,
            )
        with gr.Column(scale=1):
            submit_btn = gr.Button("提交分析", variant="primary", size="lg")
            gr.Examples(
                examples=EXAMPLES,
                inputs=input_box,
                label="或点选预设示例",
            )

    gr.Markdown("---")

    # ---- 第 1 步结果 ----
    gr.Markdown("## 第 1 步：意图识别（Function Calling）")
    with gr.Row():
        with gr.Column(scale=1):
            category_out = gr.Textbox(label="评论类型", interactive=False)
        with gr.Column(scale=2):
            key_issue_out = gr.Textbox(label="核心问题/亮点（模型提炼）", interactive=False)

    with gr.Accordion("查看第 1 步大模型返回的原始 JSON（Function Calling 参数）", open=False):
        step1_json = gr.Code(label="模型返回的 tool_call.arguments", language="json")

    gr.Markdown("---")

    # ---- 第 2 步结果 ----
    gr.Markdown("## 第 2 步：生成优化建议（Prompt Engineering）")
    with gr.Accordion("查看第 2 步发送给大模型的 Prompt", open=False):
        step2_prompt = gr.Markdown()

    advice_out = gr.Markdown(label="优化建议")

    # ---- 绑定事件 ----
    submit_btn.click(
        fn=process_review,
        inputs=input_box,
        outputs=[category_out, key_issue_out, step1_json, step2_prompt, advice_out],
    )

    # 也支持回车提交
    input_box.submit(
        fn=process_review,
        inputs=input_box,
        outputs=[category_out, key_issue_out, step1_json, step2_prompt, advice_out],
    )


if __name__ == "__main__":
    # share=True 会生成一个公网临时链接（72小时有效），
    # 面试电脑在任何网络下都能通过浏览器打开，不需要装 Python。
    demo.launch(share=True)
