# Cognix插件兼容性修复实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 修复Cognix插件与Mem0参考实现的所有兼容性问题，实现100%接口兼容，可作为drop-in replacement直接使用。

**架构：** 保持现有Provider层（HTTP API调用）不变，仅修改工具层的参数结构、返回格式和功能实现，对齐Mem0的行为。

**技术栈：** TypeScript, esbuild, OpenClaw plugin SDK

---

## 任务1：修复memory_store参数名不一致（高优先级）

**文件：**
- 修改：`index.ts:409-426`（memory_store工具定义）

- [ ] **步骤1：修改参数结构，将content改为text，添加userId参数**

```typescript
memory_store: {
  description: "Save important information in long-term memory. Use for preferences, facts, decisions, and anything worth remembering.",
  parameters: Type.Object({
    text: Type.String({ description: "Information to remember" }),
    userId: Type.Optional(Type.String({ description: "User ID to scope this memory" })),
    long_term: Type.Optional(Type.Boolean({ description: "Store as long-term memory, default true", default: true })),
    metadata: Type.Optional(Type.Record(Type.String(), Type.Any(), { description: "Additional metadata" })),
  }),
  async execute({ text, userId, long_term, metadata }, context: any) {        
    const result = await provider.add(
      [{ role: "user", content: text }],
      {
        user_id: userId ?? context.userId ?? config.userId,
        agent_id: context.agentId ?? config.agentId,
        run_id: !long_term ? context.runId : undefined,
        long_term,
      }
    );
    
    const added = result.results?.filter(r => r.event === "ADD") ?? [];
    const updated = result.results?.filter(r => r.event === "UPDATE") ?? [];
    
    const summary = [];
    if (added.length > 0) summary.push(`${added.length} new ${added.length === 1 ? "memory" : "memories"} added`);
    if (updated.length > 0) summary.push(`${updated.length} ${updated.length === 1 ? "memory" : "memories"} updated`);
    
    return {
      content: summary.join(", "),
      added: added.length,
      updated: updated.length,
      results: result.results,
    };
  },
},
```

- [ ] **步骤2：验证修改是否符合Mem0接口定义**
- [ ] **步骤3：提交代码**

## 任务2：为所有工具添加userId参数支持（高优先级）

**文件：**
- 修改：`index.ts` 中 `memory_search`, `memory_list`, `memory_get`, `memory_forget` 工具定义

- [ ] **步骤1：修改memory_search工具，添加userId参数**

```typescript
memory_search: {
  description: "Search through long-term memories. Use when you need context about user preferences, past decisions, or previously discussed topics.",
  parameters: Type.Object({
    query: Type.String({ description: "Search query text" }),
    limit: Type.Optional(Type.Number({ description: "Number of results to return, default 10", default: 10 })),
    userId: Type.Optional(Type.String({ description: "User ID to scope search" })),
  }),
  async execute({ query, limit, userId }, context: any) {
    const results = await provider.search(query, {
      user_id: userId ?? context.userId ?? config.userId,
      agent_id: context.agentId ?? config.agentId,
      top_k: limit ?? 10,
      threshold: config.searchThreshold,
    });
    
    const standardResults = results.map(m => ({
      text: m.memory,
      path: m.metadata?.path || `memory/${m.id}.md`,
      score: m.score || 0,
      start_line: m.metadata?.start_line,
      end_line: m.metadata?.end_line,
    }));
    
    return {
      results: standardResults,
    };
  },
},
```

- [ ] **步骤2：修改memory_list工具，添加userId参数**

```typescript
memory_list: {
  description: "List all memories for the user",
  parameters: Type.Object({
    limit: Type.Optional(Type.Number({ description: "Maximum number of memories to return, default 20", default: 20 })),
    userId: Type.Optional(Type.String({ description: "User ID to scope list" })),
  }),
  async execute({ limit, userId }, context: any) {
    const results = await provider.getAll({
      user_id: userId ?? context.userId ?? config.userId,
      agent_id: context.agentId ?? config.agentId,
      page_size: limit,
    });
    return {
      content: JSON.stringify(results, null, 2),
      contentType: "json",
    };
  },
},
```

- [ ] **步骤3：修改memory_get工具，添加userId参数**

```typescript
memory_get: {
  description: "Get a specific memory by ID",
  parameters: Type.Object({
    memory_id: Type.String({ description: "ID of the memory to retrieve" }),
    userId: Type.Optional(Type.String({ description: "User ID the memory belongs to" })),
  }),
  async execute({ memory_id, userId }, context: any) {
    const result = await provider.get(memory_id);
    return {
      content: JSON.stringify(result, null, 2),
      contentType: "json",
    };
  },
},
```

- [ ] **步骤4：修改memory_forget工具，添加userId参数**
- [ ] **步骤5：验证所有工具参数结构与Mem0一致**
- [ ] **步骤6：提交代码**

## 任务3：实现Session级内存支持（中优先级）

**文件：**
- 修改：`index.ts` 中 `before_agent_start`, `after_agent_turn` hook 和 provider调用

- [ ] **步骤1：添加全局sessionId跟踪**

```typescript
let currentSessionId: string | undefined;
```

- [ ] **步骤2：修改before_agent_start hook，跟踪sessionId并搜索session记忆**

```typescript
const before_agent_start = async (context: any) => {
  if (!config.autoRecall) return;

  // Track session ID
  const sessionId = context?.sessionKey ?? undefined;
  if (sessionId) currentSessionId = sessionId;

  const lastUserMessage = context.messages.findLast(m => m.role === "user")?.content;
  if (!lastUserMessage) return;

  try {
    // Search long-term memories
    const longTermResults = await provider.search(lastUserMessage, {
      user_id: context.userId ?? config.userId,
      agent_id: context.agentId ?? config.agentId,
      top_k: config.topK,
      threshold: config.searchThreshold,
    });

    // Search session memories if we have a session ID
    let sessionResults: MemoryItem[] = [];
    if (currentSessionId) {
      sessionResults = await provider.search(lastUserMessage, {
        user_id: context.userId ?? config.userId,
        agent_id: context.agentId ?? config.agentId,
        run_id: currentSessionId,
        top_k: config.topK,
        threshold: config.searchThreshold,
      });
    }

    // Deduplicate session results against long-term
    const longTermIds = new Set(longTermResults.map(r => r.id));
    const uniqueSessionResults = sessionResults.filter(r => !longTermIds.has(r.id));

    const allResults = [...longTermResults, ...uniqueSessionResults];

    if (allResults.length > 0) {
      context.systemPrompt = `【用户记忆】\n${allResults.map(m => `- ${m.memory}`).join("\n")}\n\n${context.systemPrompt}`;
    }
  } catch (e) {
    console.error("Failed to recall memories:", e);
  }
};
```

- [ ] **步骤3：修改after_agent_turn hook，支持session级存储**

```typescript
const after_agent_turn = async (context: any) => {
  if (!config.autoCapture) return;

  try {
    await provider.add(context.messages, {
      user_id: context.userId ?? config.userId,
      agent_id: context.agentId ?? config.agentId,
      run_id: currentSessionId,
      custom_instructions: config.customInstructions,
    });
  } catch (e) {
    console.error("Failed to capture memories:", e);
  }
};
```

- [ ] **步骤4：验证long_term=false时会使用run_id进行session隔离**
- [ ] **步骤5：提交代码**

## 任务4：更新文档和版本（发布前准备）

**文件：**
- 修改：`README.md` 工具说明部分
- 修改：`package.json` 版本号

- [ ] **步骤1：更新README.md中的工具列表和参数说明**
- [ ] **步骤2：提升版本号（v1.1.0）**
- [ ] **步骤3：构建并测试插件**
- [ ] **步骤4：发布新版本到npm**

---

## 验收标准
1. 所有工具参数与Mem0参考实现完全一致
2. 支持session级记忆存储和召回
3. 构建无错误，可正常安装使用
4. 与Mem0插件的调用方式100%兼容，无需修改上层代码