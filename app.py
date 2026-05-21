"""
Agent 可视化演示 —— 面试用
运行方式：python app.py
浏览器打开 http://127.0.0.1:7860

包含两个Tab：
  Tab 1 - 单条评论分析（Function Calling 完整链路）
  Tab 2 - 批量分析报表（多评论汇总统计）
"""

import gradio as gr
from ai import analyze_review, batch_analyze, client, tools
import json

# ============================================================
# 预设示例
# ============================================================
SINGLE_EXAMPLES = [
    ["东西质量还行，但是发货太慢了，等了一周还没到，客服也不回消息"],
    ["这个耳机的降噪效果绝了，戴上以后地铁噪音完全听不见，推荐！"],
    ["建议你们加一个深色模式，晚上刷商品太刺眼了"],
    ["买了两件衣服，一件颜色跟图片差太多退货了，另一件还行"],
    ["快递包装很好，还送了小礼品，客服态度也特别好"],
]

BATCH_EXAMPLE = (
    "东西质量还行，但是发货太慢了，等了一周还没到，客服也不回消息\n"
    "这个耳机的降噪效果绝了，戴上以后地铁噪音完全听不见，推荐！\n"
    "建议你们加一个深色模式，晚上刷商品太刺眼了\n"
    "买了两件衣服，一件颜色跟图片差太多退货了，另一件还行\n"
    "快递包装很好，还送了小礼品，客服态度也特别好"
)


# ============================================================
# Tab 1：单条评论分析（原有功能）
# ============================================================
def process_single(review_text):
    """拆解 Agent 两步过程，让面试官看到中间结果"""
    if not review_text.strip():
        return "请先输入评论内容", "", "", ""

    # 第 1 步
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
    step1_raw = json.dumps(args, ensure_ascii=False, indent=2)

    label_map = {"complaint": "投诉", "praise": "好评", "suggestion": "建议"}

    # 第 2 步
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
        f"**发给大模型的 Prompt：**\n\n{used_prompt}",
        advice,
    )


# ============================================================
# Tab 2：批量分析报表（新功能）
# ============================================================
def process_batch(reviews_text):
    """
    输入：多行文本，一行一条评论
    输出：汇总报表的各部分
    """
    # 按行切分，过滤空行
    lines = [line.strip() for line in reviews_text.strip().split("\n") if line.strip()]
    if not lines:
        return "请至少输入一条评论", "", "", "", ""

    # 调用 batch_analyze
    report = batch_analyze(lines)

    # 1. 各类型占比表（Markdown 格式）
    label_map = {"complaint": "投诉", "praise": "好评", "suggestion": "建议"}
    summary_md = f"| 类型 | 数量 | 占比 |\n|------|------|------|\n"
    for cat_name in ["complaint", "praise", "suggestion"]:
        data = report["summary"][cat_name]
        bar = "█" * max(1, int(data["percentage"] / 5))
        summary_md += f"| {label_map[cat_name]} | {data['count']} | {data['percentage']}% {bar} |\n"

    # 2. 投诉清单
    if report["complaint_issues"]:
        complaint_md = ""
        for i, issue in enumerate(report["complaint_issues"], 1):
            complaint_md += f"{i}. {issue}\n"
    else:
        complaint_md = "无投诉，用户满意度良好。"

    # 3. 优先级
    priority_label = label_map.get(report["priority"], report["priority"])
    priority_md = f"**{priority_label}** — {report['priority_reason']}"

    # 4. 原始明细（JSON 格式，方便查看）
    details_json = json.dumps(report["details"], ensure_ascii=False, indent=2)

    # 5. 总览文字
    total = report["total"]
    overview_md = f"共 **{total}** 条评论，各类型分布如下："

    return overview_md, summary_md, complaint_md, priority_md, details_json


# ============================================================
# 构建 Web 界面（两个 Tab）
# ============================================================
with gr.Blocks(title="AI Agent - 评论分析演示") as demo:
    gr.Markdown(
        """
        # AI Agent：用户评论分析 + 优化建议生成

        **面试演示** — 单条评论深度分析 + 批量汇总报表，覆盖两种真实业务场景。
        """
    )

    with gr.Tabs():
        # ========================
        # Tab 1：单条分析
        # ========================
        with gr.TabItem("单条评论分析"):
            gr.Markdown("### 逐条分析 — 展示 Function Calling 完整链路")

            with gr.Row():
                with gr.Column(scale=2):
                    input_single = gr.Textbox(
                        label="输入用户评论",
                        placeholder="例如：东西质量还行，但是发货太慢了...",
                        lines=3,
                    )
                with gr.Column(scale=1):
                    submit_single = gr.Button("提交分析", variant="primary")
                    gr.Examples(examples=SINGLE_EXAMPLES, inputs=input_single, label="预设示例")

            gr.Markdown("---")

            gr.Markdown("#### 第 1 步：意图识别（Function Calling）")
            with gr.Row():
                with gr.Column(scale=1):
                    cat_out = gr.Textbox(label="评论类型", interactive=False)
                with gr.Column(scale=2):
                    key_out = gr.Textbox(label="核心问题/亮点", interactive=False)
            with gr.Accordion("查看大模型返回的原始 Function Calling JSON", open=False):
                step1_json = gr.Code(label="tool_call.arguments", language="json")

            gr.Markdown("#### 第 2 步：生成优化建议（Prompt Engineering）")
            with gr.Accordion("查看发给大模型的 Prompt", open=False):
                prompt_out = gr.Markdown()
            advice_out = gr.Markdown(label="优化建议")

            submit_single.click(
                fn=process_single,
                inputs=input_single,
                outputs=[cat_out, key_out, step1_json, prompt_out, advice_out],
            )
            input_single.submit(
                fn=process_single,
                inputs=input_single,
                outputs=[cat_out, key_out, step1_json, prompt_out, advice_out],
            )

        # ========================
        # Tab 2：批量分析
        # ========================
        with gr.TabItem("批量分析报表"):
            gr.Markdown("### 批量汇总 — 多评论一键统计 + 优先级排序")

            with gr.Row():
                with gr.Column(scale=2):
                    input_batch = gr.Textbox(
                        label="输入多条评论（一行一条）",
                        placeholder="东西质量还行，但是发货太慢了...\n降噪效果绝了，推荐！\n建议加个深色模式...",
                        lines=8,
                        value=BATCH_EXAMPLE,
                    )
                with gr.Column(scale=1):
                    submit_batch = gr.Button("生成汇总报表", variant="primary", size="lg")
                    gr.Markdown(
                        """
                        **说明：**
                        会逐条调用 Agent 分析，
                        然后汇总统计各类型占比
                        和优先级建议。
                        5 条约需 30~40 秒。
                        """
                    )

            gr.Markdown("---")

            gr.Markdown("#### 总览")
            overview_out = gr.Markdown()

            gr.Markdown("#### 各类型占比")
            summary_out = gr.Markdown()

            gr.Markdown("#### 投诉清单")
            complaint_out = gr.Markdown()

            gr.Markdown("#### 优先处理建议")
            priority_out = gr.Markdown()

            with gr.Accordion("查看每条评论的完整分析明细（JSON）", open=False):
                details_out = gr.Code(label="details", language="json")

            submit_batch.click(
                fn=process_batch,
                inputs=input_batch,
                outputs=[overview_out, summary_out, complaint_out, priority_out, details_out],
            )


if __name__ == "__main__":
    demo.launch(share=True)
