# OpenClaw Cognix 记忆插件

Cognix 是一款自研的自托管混合记忆系统，结合 Markdown 文件和 SQLite 数据库，为 OpenClaw 提供长期记忆能力。

## ✨ 核心特性

- 📝 **纯 Markdown 存储**：所有记忆以纯文本 Markdown 格式存储，可直接编辑、版本控制
- 🔍 **语义搜索**：内置向量检索能力，支持自然语言查询相关记忆
- 🤖 **自动召回**：会话开始时自动注入相关记忆，提供个性化回答
- 💾 **自动捕获**：会话结束时自动提取关键信息存入记忆
- 🔌 **标准接口**：完全兼容 OpenClaw 记忆插件标准，即插即用
- 📦 **自托管**：所有数据存储在本地，隐私安全可控

## 🚀 快速开始

### 1. 安装插件

```bash
openclaw plugins install @starnever0/openclaw-cognix-plugin
```

> 本地开发安装请使用：`openclaw plugins install ./openclaw-plugin-cognix`

### 2. 配置插件

在 OpenClaw 配置文件中添加：

```yaml
plugins:
  slots:
    memory: "openclaw-cognix-plugin"
  config:
    openclaw-cognix-plugin:
      host: "http://localhost:8765" # Cognix 服务器地址
      apiKey: "your-api-key"        # API 密钥（可使用 dummy 本地部署）
      userId: "default"             # 用户标识
      autoCapture: true             # 自动捕获会话内容
      autoRecall: true              # 自动召回相关记忆
      searchThreshold: 0.5          # 搜索相似度阈值
      topK: 5                       # 召回结果数量
```

### 3. 启动 Cognix 服务

```bash
cognix serve
```

## 🔧 标准接口

本插件完全实现 OpenClaw 记忆插件标准接口：

### 工具接口

| 工具名 | 功能描述 |
|---------|---------|
| `memory_search` | 搜索长期记忆，用于获取用户偏好、过去决策、历史讨论等上下文 |
| `memory_store` | 保存重要信息到长期记忆，支持用户ID指定、会话级存储 |
| `memory_get` | 根据ID获取指定记忆 |
| `memory_list` | 列出用户所有记忆，支持数量限制和用户ID指定 |
| `memory_forget` | 删除指定ID的记忆 |

### CLI 命令

```bash
# 搜索记忆
openclaw memory search "用户偏好" --limit 10

# 写入记忆
openclaw memory write "MEMORY.md" "# 用户偏好\n- 喜欢使用 TypeScript" --append

# 读取记忆
openclaw memory get "memory/2026-05-02.md"

# 列出记忆文件
openclaw memory list "*.md"
```

### RPC 接口

```bash
# 搜索记忆
openclaw rpc memory.search --query "项目需求" --limit 5

# 写入记忆
openclaw rpc memory.write --path "MEMORY.md" --content "新的项目需求" --append true
```

### HTTP 接口

```bash
# 搜索记忆
curl http://localhost:7391/memory/search?q=用户偏好

# 写入记忆
curl -X POST http://localhost:7391/memory/write \
  -H "Content-Type: application/json" \
  -d '{"path": "MEMORY.md", "content": "新内容", "append": true}'
```

## 📁 存储结构

所有记忆文件遵循 OpenClaw 标准工作区布局：

```
<workspace>/
├── MEMORY.md          # 全局持久记忆文件
└── memory/
    ├── 2026-05-01.md  # 按日期归档的每日记忆
    ├── 2026-05-02.md
    └── user.md        # 分类记忆文件
```

## ⚙️ 配置说明

| 参数名 | 类型 | 默认值 | 说明 |
|-------|------|--------|------|
| `host` | string | `http://localhost:8765` | Cognix API 服务器地址 |
| `apiKey` | string | 必填 | API 访问密钥 |
| `userId` | string | `default` | 用户唯一标识 |
| `autoCapture` | boolean | `true` | 自动捕获会话内容到记忆 |
| `autoRecall` | boolean | `true` | 会话开始时自动召回相关记忆 |
| `searchThreshold` | number | `0.5` | 搜索结果最小相似度阈值 |
| `topK` | number | `5` | 自动召回时返回的结果数量 |

## 🛡️ 安全特性

- 🔒 所有数据存储在用户本地工作区，不会默认上传到第三方服务
- 🔑 配置中的 API 密钥等敏感信息自动加密存储
- 🚫 自动过滤敏感信息（密码、密钥、信用卡号等）不会被存入记忆
- ⏱️ 所有记忆操作都有超时保护，不会阻塞主流程

## 🔄 兼容性

- 兼容 OpenClaw 版本 >= 2026.3.22
- 完全兼容 Mem0 插件接口，可以无缝替换
- 支持 Windows/macOS/Linux 全平台

## 📚 更多信息

- [Cognix 官方文档](https://github.com/shareclz/cognix)
- [OpenClaw 插件开发规范](../docs/plugin.md)
- [记忆系统设计文档](../docs/archive/记忆系统设计文档.md)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License
