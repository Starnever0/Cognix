# Cognix记忆增强智能体示例

## 概述
这是一个非侵入式接入Cognix记忆系统的智能体示例，完全通过CLI命令调用Cognix功能，不依赖Cognix内部代码。

## 特性
- ✅ 非侵入式设计，通过CLI调用Cognix
- ✅ 自动记忆用户信息、偏好、习惯
- ✅ 回答问题时自动召回相关记忆
- ✅ 支持获取近期上下文
- ✅ 兼容任意支持工具调用的LLM

## 快速开始

### 1. 配置环境
复制 `.env.example` 为 `.env` 并填写你的API配置：
```env
# OpenAI/DeepSeek 等兼容OpenAI API的配置
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-chat
```

### 2. 安装依赖
```bash
pip install openai python-dotenv
```

### 3. 运行智能体
```bash
python chat.py
```

## 使用示例

### 基础记忆测试
```
用户: 我叫张三，是一名软件工程师，喜欢用Python开发
[工具调用] remember: {'heading': '用户信息', 'content': '姓名：张三，职业：软件工程师，喜欢用Python开发', 'persistent': True}
助理: 你好张三！很高兴认识你，我会记住你是一名Python开发工程师。

用户: 我每周五都要发周报给王经理
[工具调用] remember: {'heading': '工作习惯', 'content': '每周五需要发周报给王经理', 'persistent': True}
助理: 好的，我记住了，以后会提醒你每周五发周报。

用户: 我应该什么时候发周报？发给谁？
[工具调用] recall: {'query': '周报 王经理'}
助理: 根据我的记录，你每周五需要发周报给王经理。
```

### 上下文获取
```
用户: 最近我们讨论了什么？
[工具调用] get_context: {'days': 1}
助理: 最近我们讨论了：
1. 你是张三，一名Python开发工程师
2. 你每周五需要发周报给王经理
```

## 目录结构
```
examples/cognix_langchain_agent/
├── .env.example    # 环境变量示例
├── cognix_tools.py # Cognix CLI工具封装
├── agent.py        # 智能体核心实现
├── chat.py         # 命令行交互入口
└── README.md       # 说明文档
```

## 工作原理
```
用户输入 → 智能体 → LLM判断是否需要调用工具
                          ↓
                  调用Cognix CLI命令
                          ↓
                  工具结果返回给LLM
                          ↓
                  LLM生成自然语言回答
                          ↓
                       输出给用户
```
