### OpenClaw 记忆插件开发的核心要求
记忆插件属于 OpenClaw 的**独占插槽插件**（`plugins.slots.memory`），必须满足以下硬性要求：
---
#### 🔹 基础结构要求
1. **插件清单文件**
   根目录必须包含 `openclaw.plugin.json`，且至少包含以下字段：
   ```json
   {
     "id": "your-memory-plugin-id",
     "name": "记忆插件名称",
     "description": "插件功能描述",
     "kind": "memory", // 必须声明为memory类型
     "version": "1.0.0",
     "configSchema": { // JSON Schema 定义配置参数
       "type": "object",
       "properties": {
         "apiKey": { "type": "string", "description": "API密钥" },
         "autoRecall": { "type": "boolean", "default": true, "description": "是否启用自动召回" }
       },
       "required": ["apiKey"]
     },
     "dependencies": {
       "openclaw": ">=0.4.0" // 兼容的最低OpenClaw版本
     }
   }
   ```
2. **入口文件**
   根目录必须有 `index.ts`/`index.js`，默认导出插件对象，包含 `register` 方法：
   ```typescript
   import type { OpenClawPluginApi } from "@openclaw/gateway";
   
   export default {
     id: "your-memory-plugin-id",
     name: "记忆插件名称",
     description: "插件功能描述",
     kind: "memory" as const,
     configSchema: ConfigSchema,
     
     async register(api: OpenClawPluginApi) {
       // 在这里注册工具、钩子、服务等
       // 插件初始化逻辑
     }
   };
   ```
---
#### 🔹 核心功能接口要求
必须实现 OpenClaw 标准的记忆工具接口，否则无法被系统正常调用：
| 工具名称 | 参数要求 | 返回要求 | 功能说明 |
|---------|---------|---------|---------|
| `memory_search` | `query: string`（查询文本）<br>`limit?: number`（返回结果数，默认10）<br>`file_filter?: string[]`（限定搜索文件） | `{ results: Array<{ text: string; path: string; score: number; start_line?: number; end_line?: number }> }` | 语义搜索相关记忆片段 |
| `memory_get` | `path: string`（文件路径）<br>`start_line?: number`<br>`end_line?: number` | `{ text: string; path: string }` | 读取指定记忆文件内容，文件不存在时返回空字符串，不抛出异常 |
| `memory_write` | `path: string`（写入路径）<br>`content: string`（写入内容）<br>`append?: boolean`（是否追加，默认false） | `{ success: boolean; path: string }` | 写入内容到记忆文件，必须保证原子性 |
| `memory_list` | `pattern?: string`（文件匹配模式） | `{ files: Array<{ path: string; last_modified: number; size: number }> }` | 列出所有记忆文件 |
---
#### 🔹 生命周期钩子要求
建议实现以下生命周期钩子，实现增强能力：
1. **`before_agent_start` 钩子**（自动召回）
   ```typescript
   api.registerHook("before_agent_start", async (event) => {
     if (api.config.autoRecall) {
       // 根据用户查询召回相关记忆
       const memories = await memorySearch(event.userMessage);
       // 将记忆注入到上下文开头
       return {
         prependContext: memories.map(m => `[记忆] ${m.text}`).join("\n")
       };
     }
     return {};
   });
   ```
   - 必须设置超时限制（最大5秒），超时返回空，不能阻塞会话启动
   - 必须捕获所有异常，钩子失败不能导致会话崩溃
2. **`agent_end` 钩子**（自动捕获）
   ```typescript
   api.registerHook("agent_end", async (event) => {
     if (api.config.autoCapture) {
       // 分析会话内容，提取重要信息写入记忆
       await autoCaptureMemory(event.conversationHistory);
     }
   });
   ```
   - 必须异步执行，不阻塞用户响应
   - 必须过滤敏感信息（密码、API密钥、信用卡号等）
---
#### 🔹 兼容性要求
1. **文件系统兼容**
   - 必须严格遵循 OpenClaw 标准工作区布局，所有记忆文件必须写入 `agents.defaults.workspace` 目录下
   - 必须支持 `MEMORY.md` 和 `memory/YYYY-MM-DD.md` 的默认读写
   - 写入格式必须为纯 Markdown，不能添加私有二进制格式或特殊标记
2. **优雅降级**
   - 插件初始化失败（如API不可用、配置错误）时必须正常加载，不能导致网关启动失败
   - 工具调用失败时必须返回友好的错误信息，不能抛出未捕获的异常
3. **数据安全**
   - 所有持久化数据必须存储在用户本地工作区，不得默认上传到第三方服务
   - 配置中的敏感信息（API密钥）必须加密存储，不得明文写入日志
---
### 对外提供服务的方式
记忆插件可以通过以下方式向 OpenClaw 生态提供服务：
#### 🔹 智能体工具服务
所有注册的 `memory_*` 工具会自动暴露给智能体，LLM 可以直接调用这些工具完成记忆相关操作，无需额外配置。
#### 🔹 网关 RPC 服务
通过 `api.registerGatewayMethod` 注册 RPC 接口，供外部系统调用：
```typescript
api.registerGatewayMethod("memory.search", async (params) => {
  return await memorySearch(params.query, params.limit);
});
```
调用方式：
```bash
openclaw rpc memory.search --query "用户偏好" --limit 5
```
#### 🔹 CLI 命令服务
通过 `api.registerCli` 注册命令行工具，供用户直接操作记忆：
```typescript
api.registerCli({
  command: "memory search <query>",
  description: "搜索记忆内容",
  handler: async (args) => {
    const results = await memorySearch(args.query);
    console.log(results);
  }
});
```
使用方式：
```bash
openclaw memory search "用户偏好"
```
#### 🔹 HTTP 接口服务
通过 `api.registerHttpRoute` 暴露 HTTP 端点，供外部系统集成：
```typescript
api.registerHttpRoute({
  path: "/memory/search",
  auth: "gateway",
  handler: async (req, res) => {
    const query = req.query.q as string;
    const results = await memorySearch(query);
    res.setHeader("Content-Type", "application/json");
    res.end(JSON.stringify(results));
    return true;
  }
});
```
调用方式：
```bash
curl http://localhost:7391/memory/search?q=用户偏好
```
---
### 发布与部署要求
1. 必须发布为 npm 包，遵循 `@your-org/openclaw-plugin-memory-xxx` 命名规范
2. 必须提供完整的安装和配置文档，包含必填参数说明、使用示例
3. 必须支持通过 `openclaw plugins install @your-org/openclaw-plugin-memory-xxx` 一键安装
4. 必须在配置中将 `plugins.slots.memory` 设置为插件 ID 即可完成替换，无需修改其他核心配置
> 参考官方实现：[memory-core](https://github.com/openclaw/openclaw/tree/main/extensions/memory-core) 插件源码，是最标准的记忆插件实现参考。