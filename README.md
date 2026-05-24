# AI Agent：电商评论分析与反话检测

基于 DeepSeek API + Function Calling 的智能评论分析 Agent，支持批量处理、反话/讽刺检测、情感极性独立校验，并自动生成优化建议。

---

## 项目结构

```
刷题/
├── ai.py          # 核心 Agent 逻辑（API 调用、编排、校验）
├── app.py         # Gradio Web 界面（可视化演示）
├── demo.html      # 静态演示页面（面试/汇报用）
├── .env           # API Key 配置（需自行创建）
└── README.md      # 本文件
```

---

## 架构总览

```
用户评论
   │
   ▼
┌─────────────────────────────────────────────────────┐
│ API 1：Function Calling（分类 + 反话检测）            │
│   输入：原始评论 + System Prompt（含 3 条反话示例）   │
│   输出：category / key_issue / is_sarcastic          │
│   技术：tools 定义 + few-shot prompting              │
├─────────────────────────────────────────────────────┤
│         ▼                                            │
│   并行执行（ThreadPoolExecutor）                      │
│         │                                            │
│    ┌────┴────┐                                       │
│    ▼         ▼                                       │
│ API 2      API 3                                     │
│ 情感校验   优化建议                                    │
│                                                      │
│ API 2：独立情感极性判断                               │
│   输入：仅原始评论（不知 API 1 结果）                 │
│   输出：sentiment（positive/negative/neutral）        │
│                                                      │
│ API 3：生成优化建议                                   │
│   输入：分类结果 → 拼装对应 Prompt 模板                │
│   输出：3 条具体改进建议                               │
│                                                      │
│         ▼                                            │
│   Python 侧对比：category vs sentiment               │
│   冲突 → need_review=true → 标记人工复核              │
│   一致 → need_review=false → 自动通过                 │
└─────────────────────────────────────────────────────┘
   │
   ▼
返回：{ category, key_issue, is_sarcastic, advice, need_review, review_note }
```

---

## 反话检测：两层防护机制

### 方案一：few-shot 内嵌（API 1 内置）

System Prompt 中注入 3 条反话示例，Function Calling schema 中新增 `is_sarcastic` 字段，让模型在分类时同步判断是否反话。

| few-shot 示例 | 讽刺方向 |
|---|---|
| "哇发货真的快呢，等了三周才到" | 物流 |
| "客服超级耐心，问了五次都没人回" | 客服 |
| "包装很精致，碎了一半到货" | 包装 |

### 方案二：独立情感校验（API 2 + Python 对比）

`verify_sentiment()` 只接收原始评论，独立判断情感极性，不知道 API 1 的分类结果。在 Python 侧对比：

```
complaint + negative → 一致，通过
praise    + positive → 一致，通过
praise    + negative → 冲突 → need_review（反话漏判，方案二兜底）
complaint + positive → 冲突 → need_review（可能误判）
```

**关键设计**：API 2 全程不知道 API 1 的分类结果，避免锚定偏差。

---

## 各模块说明

### ai.py — 核心引擎

| 函数 | 作用 |
|---|---|
| `analyze_review(review_text)` | 单条评论分析入口，编排 3 次 API 调用 |
| `verify_sentiment(review_text)` | 独立情感极性判断（与分类结果隔离） |
| `batch_analyze(reviews)` | 批量分析，调用 `analyze_review` 后汇总统计 |

### app.py — Gradio 可视化

| Tab | 功能 |
|---|---|
| 单条评论分析 | 输入一条评论，展示 3 步 Pipeline 完整结果 |
| 批量分析报表 | 多条评论一键汇总，占比统计 + 优先级建议 |

### demo.html — 静态演示页

纯前端页面，双击浏览器即可打开。展示 Agent 执行架构、反话检测示例、批量分析报表、创新点方向。**无需 Python 环境**。

---

## 运行手册（SOP）

### 前置条件

1. Python 3.9+ 已安装
2. 安装依赖：

```bash
pip install openai python-dotenv gradio
```

3. 在项目根目录创建 `.env` 文件：

```
DEEPSEEK_API_KEY=sk-你的key
```

### 方式一：命令行测试

```bash
cd D:\DL_data\刷题
python ai.py
```

输出单条 + 批量测试结果，包括反话检测和人工复核标记。

### 方式二：Web 界面（Gradio）

```bash
cd D:\DL_data\刷题
python app.py
```

浏览器打开 `http://127.0.0.1:7860`（端口被占用会自动切换到 7861/7862，看终端提示）。

- Tab「单条评论分析」：输入评论 → 查看 3 步 Pipeline 结果
- Tab「批量分析报表」：多行评论 → 汇总统计

### 方式三：静态页面（无需 Python）

双击 `demo.html` 直接在浏览器打开，点击示例卡片查看演示效果。

---

## 创新点与改进方向

### 趋势分析（时间维度）

单条评论是静态快照，加入时间维度后可以追踪问题演变：“上周投诉最多的是物流，本周变成了客服”——说明物流改善了但客服变差了，辅助运营做动态调配。竞品只做静态分类，做不到这一点。

### 商家画像（问题聚类）

批量分析多个商家后，按投诉结构给每个商家生成“问题画像”——物流差型、客服差型、产品差型，不同类型给不同的改进路径，而不是千篇一律的建议模板。

> 以上创新点已写入 `demo.html`，待数据集到位后实现。

---

## 技术栈

- **LLM**：DeepSeek V3（deepseek-chat）
- **API 范式**：Function Calling（结构化输出）+ 普通 Chat
- **编排**：Python（json、ThreadPoolExecutor 并行）
- **UI**：Gradio + 纯 HTML/CSS/JS
