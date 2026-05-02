/**
 * OpenClaw Cognix Memory Plugin
 *
 * Long-term memory via Cognix — self-hosted markdown + SQLite hybrid memory system
 *
 * Features:
 * - 5 tools: memory_search, memory_list, memory_store, memory_get, memory_forget
 *   (with session/long-term scope support via scope and longTerm parameters)
 * - Short-term (session-scoped) and long-term (user-scoped) memory
 * - Auto-recall: injects relevant memories (both scopes) before each agent turn
 * - Auto-capture: stores key facts scoped to the current session after each agent turn
 * - Full compatibility with Mem0 plugin interface — drop-in replacement
 */

import { Type } from "@sinclair/typebox";
import { definePluginEntry, type OpenClawPluginApi } from "openclaw/plugin-sdk/plugin-entry";

// ============================================================================
// Types
// ============================================================================

type CognixConfig = {
  apiKey: string;
  host?: string;
  userId: string;
  autoCapture: boolean;
  autoRecall: boolean;
  searchThreshold: number;
  topK: number;
  agentId?: string;
  customInstructions: string;
};

interface AddOptions {
  agent_id?: string;
  user_id: string;
  run_id?: string;
  custom_instructions?: string;
  long_term?: boolean;
}

interface SearchOptions {
  agent_id?: string;
  user_id: string;
  run_id?: string;
  top_k?: number;
  threshold?: number;
  limit?: number;
}

interface ListOptions {
  user_id: string;
  run_id?: string;
  page_size?: number;
}

interface MemoryItem {
  id: string;
  memory: string;
  user_id?: string;
  score?: number;
  categories?: string[];
  metadata?: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
}

interface AddResultItem {
  id: string;
  memory: string;
  event: "ADD" | "UPDATE" | "DELETE" | "NOOP";
}

interface AddResult {
  results: AddResultItem[];
}

// ============================================================================
// Cognix Provider
// ============================================================================

interface CognixProvider {
  add(
    messages: Array<{ role: string; content: string }>,
    options: AddOptions,
  ): Promise<AddResult>;
  search(query: string, options: SearchOptions): Promise<MemoryItem[]>;
  get(memoryId: string): Promise<MemoryItem>;
  getAll(options: ListOptions): Promise<MemoryItem[]>;
  delete(memoryId: string): Promise<void>;
}

class DefaultCognixProvider implements CognixProvider {
  private readonly baseUrl: string;
  private readonly headers: Record<string, string>;

  constructor(
    private readonly apiKey: string,
    private readonly host: string = "http://localhost:8765",
    private readonly userId?: string,
  ) {
    this.baseUrl = host.endsWith("/") ? host.slice(0, -1) : host;
    this.headers = {
      "Authorization": `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    };
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const response = await fetch(url, {
      headers: this.headers,
      ...options,
    });
    
    if (!response.ok) {
      throw new Error(`Cognix API request failed: ${response.status} ${response.statusText}`);
    }
    
    return await response.json();
  }

  async add(
    messages: Array<{ role: string; content: string }>,
    options: AddOptions,
  ): Promise<AddResult> {
    const result = await this.request("/v1/memories", {
      method: "POST",
      body: JSON.stringify({
        messages,
        user_id: options.user_id,
        run_id: options.run_id,
        agent_id: options.agent_id,
        custom_instructions: options.custom_instructions,
        long_term: options.long_term ?? true,
      }),
    });
    
    return normalizeAddResult(result);
  }

  async search(query: string, options: SearchOptions): Promise<MemoryItem[]> {
    const params = new URLSearchParams({
      q: query,
      user_id: options.user_id,
      ...(options.run_id && { run_id: options.run_id }),
      ...(options.top_k != null && { top_k: String(options.top_k) }),
      ...(options.threshold != null && { threshold: String(options.threshold) }),
      ...(options.agent_id && { agent_id: options.agent_id }),
    });
    
    const results = await this.request(`/v1/memories/search?${params}`);
    return normalizeSearchResults(results);
  }

  async get(memoryId: string): Promise<MemoryItem> {
    const result = await this.request(`/v1/memories/${memoryId}`);
    return normalizeMemoryItem(result);
  }

  async getAll(options: ListOptions): Promise<MemoryItem[]> {
    const params = new URLSearchParams({
      user_id: options.user_id,
      ...(options.run_id && { run_id: options.run_id }),
      ...(options.page_size != null && { limit: String(options.page_size) }),
    });
    
    const results = await this.request(`/v1/memories?${params}`);
    if (Array.isArray(results)) return results.map(normalizeMemoryItem);
    if (results?.results && Array.isArray(results.results))
      return results.results.map(normalizeMemoryItem);
    return [];
  }

  async delete(memoryId: string): Promise<void> {
    await this.request(`/v1/memories/${memoryId}`, {
      method: "DELETE",
    });
  }
}

// ============================================================================
// Result Normalizers
// ============================================================================

function normalizeMemoryItem(raw: any): MemoryItem {
  return {
    id: raw.id ?? raw.memory_id ?? "",
    memory: raw.memory ?? raw.text ?? raw.content ?? "",
    user_id: raw.user_id ?? raw.userId,
    score: raw.score,
    categories: raw.categories,
    metadata: raw.metadata,
    created_at: raw.created_at ?? raw.createdAt,
    updated_at: raw.updated_at ?? raw.updatedAt,
  };
}

function normalizeSearchResults(raw: any): MemoryItem[] {
  if (Array.isArray(raw)) return raw.map(normalizeMemoryItem);
  if (raw?.results && Array.isArray(raw.results))
    return raw.results.map(normalizeMemoryItem);
  return [];
}

function normalizeAddResult(raw: any): AddResult {
  if (raw?.results && Array.isArray(raw.results)) {
    return {
      results: raw.results.map((r: any) => ({
        id: r.id ?? r.memory_id ?? "",
        memory: r.memory ?? r.text ?? "",
        event: r.event ?? r.metadata?.event ?? "ADD",
      })),
    };
  }
  if (Array.isArray(raw)) {
    return {
      results: raw.map((r: any) => ({
        id: r.id ?? r.memory_id ?? "",
        memory: r.memory ?? r.text ?? "",
        event: r.event ?? r.metadata?.event ?? "ADD",
      })),
    };
  }
  return { results: [] };
}

// ============================================================================
// Config Parser
// ============================================================================

function resolveEnvVars(value: string): string {
  return value.replace(/\$\{([^}]+)\}/g, (_, envVar) => {
    const envValue = process.env[envVar];
    if (!envValue) {
      throw new Error(`Environment variable ${envVar} is not set`);
    }
    return envValue;
  });
}

// ============================================================================
// Default Custom Instructions
// ============================================================================

const DEFAULT_CUSTOM_INSTRUCTIONS = `Your Task: Extract and maintain a structured, evolving profile of the user from their conversations. Capture information that helps the assistant provide personalized, context-aware responses.

Information to Extract:
1. Identity & Preferences: Name, role, communication style, tool preferences, content preferences
2. Work & Projects: Current projects, goals, deadlines, technical stack, work patterns
3. Decisions & Knowledge: Important decisions, lessons learned, technical context, rules
4. Relationships & Workflows: Team members, approval processes, recurring workflows

Guidelines:
- Store memories as clear, self-contained statements
- Use third person: "User prefers..." not "I prefer..."
- Include temporal context when relevant
- Update existing memories when information changes
- Merge related facts into coherent memories
- Preserve specificity
`;

// ============================================================================
// Config Schema
// ============================================================================

const ALLOWED_KEYS = [
  "apiKey",
  "userId",
  "host",
  "autoCapture",
  "autoRecall",
  "customInstructions",
  "searchThreshold",
  "topK",
  "agentId",
];

function assertAllowedKeys(
  value: Record<string, unknown>,
  allowed: string[],
  label: string,
) {
  const unknown = Object.keys(value).filter((key) => !allowed.includes(key));
  if (unknown.length === 0) return;
  throw new Error(`${label} has unknown keys: ${unknown.join(", ")}`);
}

const cognixConfigSchema = {
  parse(value: unknown): CognixConfig {
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      throw new Error("openclaw-cognix-plugin config required");
    }
    const cfg = value as Record<string, unknown>;
    assertAllowedKeys(cfg, ALLOWED_KEYS, "openclaw-cognix-plugin config");

    if (typeof cfg.apiKey !== "string" || !cfg.apiKey) {
      throw new Error("apiKey is required for Cognix plugin");
    }

    return {
      apiKey: typeof cfg.apiKey === "string" ? resolveEnvVars(cfg.apiKey) : undefined,
      agentId: typeof cfg.agentId === "string" ? cfg.agentId : undefined,
      userId: typeof cfg.userId === "string" && cfg.userId ? cfg.userId : "default",
      host: typeof cfg.host === "string" ? resolveEnvVars(cfg.host) : undefined,
      autoCapture: cfg.autoCapture !== false,
      autoRecall: cfg.autoRecall !== false,
      customInstructions:
        typeof cfg.customInstructions === "string"
          ? cfg.customInstructions
          : DEFAULT_CUSTOM_INSTRUCTIONS,
      searchThreshold:
        typeof cfg.searchThreshold === "number" ? cfg.searchThreshold : 0.5,
      topK: typeof cfg.topK === "number" ? cfg.topK : 5,
    };
  },
};

// ============================================================================
// Provider Factory
// ============================================================================

function createProvider(
  cfg: CognixConfig,
): CognixProvider {
  return new DefaultCognixProvider(cfg.apiKey!, cfg.host, cfg.userId);
}

// ============================================================================
// Plugin Definition
// ============================================================================

export default definePluginEntry((api) => {
  const config = cognixConfigSchema.parse(api.config);
  const provider = createProvider(config);

  // Auto-recall: inject memories before agent start
  const before_agent_start = async (context: any) => {
    if (!config.autoRecall) return;

    const lastUserMessage = context.messages.findLast(m => m.role === "user")?.content;
    if (!lastUserMessage) return;

    try {
      const memories = await provider.search(lastUserMessage, {
        user_id: context.userId ?? config.userId,
        agent_id: context.agentId ?? config.agentId,
        top_k: config.topK,
        threshold: config.searchThreshold,
      });

      if (memories.length > 0) {
        context.systemPrompt = `【用户记忆】\n${memories.map(m => `- ${m.memory}`).join("\n")}\n\n${context.systemPrompt}`;
      }
    } catch (e) {
      console.error("Failed to recall memories:", e);
    }
  };

  // Auto-capture: store memories after agent turn
  const after_agent_turn = async (context: any) => {
    if (!config.autoCapture) return;

    try {
      await provider.add(context.messages, {
        user_id: context.userId ?? config.userId,
        agent_id: context.agentId ?? config.agentId,
        run_id: context.runId,
        custom_instructions: config.customInstructions,
      });
    } catch (e) {
      console.error("Failed to capture memories:", e);
    }
  };

  return {
    hooks: {
      before_agent_start,
      after_agent_turn,
    },
    tools: {
      memory_search: {
        description: "Semantic search for relevant memory fragments",
        parameters: Type.Object({
          query: Type.String({ description: "Search query text" }),
          limit: Type.Optional(Type.Number({ description: "Number of results to return, default 10", default: 10 })),
          file_filter: Type.Optional(Type.Array(Type.String(), { description: "Limit search to specific files" })),
        }),
        async execute({ query, limit, file_filter }, context: any) {
          const results = await provider.search(query, {
            user_id: context.userId ?? config.userId,
            agent_id: context.agentId ?? config.agentId,
            top_k: limit ?? 10,
            threshold: config.searchThreshold,
          });
          
          // 转换为标准返回格式
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
      memory_write: {
        description: "Write content to memory file, supports append mode",
        parameters: Type.Object({
          path: Type.String({ description: "Path to the memory file, e.g. MEMORY.md or memory/2026-05-02.md" }),
          content: Type.String({ description: "Content to write" }),
          append: Type.Optional(Type.Boolean({ description: "Whether to append to the file, default false", default: false })),
          long_term: Type.Optional(Type.Boolean({ description: "Store as long-term memory", default: true })),
        }),
        async execute({ path, content, append, long_term }, context: any) {
          // 处理路径，如果是MEMORY.md或日期格式的文件，使用分类存储
          let storeContent = content;
          if (append) {
            // 追加模式，先读取现有内容再合并
            try {
              const existing = await provider.get(path);
              if (existing?.memory) {
                storeContent = existing.memory + "\n" + content;
              }
            } catch (e) {
              // 文件不存在，直接写入
            }
          }
          
          const result = await provider.add(
            [{ role: "user", content: storeContent }],
            {
              user_id: context.userId ?? config.userId,
              agent_id: context.agentId ?? config.agentId,
              run_id: context.runId,
              long_term,
            }
          );
          
          return {
            success: result.results.length > 0,
            path: path,
          };
        },
      },
      memory_list: {
        description: "List all memory files",
        parameters: Type.Object({
          pattern: Type.Optional(Type.String({ description: "File matching pattern" })),
        }),
        async execute({ pattern }, context: any) {
          const results = await provider.getAll({
            user_id: context.userId ?? config.userId,
            agent_id: context.agentId ?? config.agentId,
          });
          
          // 转换为标准返回格式
          const files = results.map(m => ({
            path: m.metadata?.path || `memory/${m.id}.md`,
            last_modified: new Date(m.updated_at || m.created_at || Date.now()).getTime(),
            size: m.memory?.length || 0,
          }));
          
          // 应用pattern过滤
          const filtered = pattern 
            ? files.filter(f => f.path.includes(pattern.replace("*", "")))
            : files;
          
          return {
            files: filtered,
          };
        },
      },
      memory_get: {
        description: "Read content from specified memory file",
        parameters: Type.Object({
          path: Type.String({ description: "Path to the memory file" }),
          start_line: Type.Optional(Type.Number({ description: "Start line number" })),
          end_line: Type.Optional(Type.Number({ description: "End line number" })),
        }),
        async execute({ path, start_line, end_line }, context: any) {
          try {
            const result = await provider.get(path);
            let text = result?.memory || "";
            
            // 处理行范围
            if (start_line || end_line) {
              const lines = text.split("\n");
              const start = start_line ? Math.max(0, start_line - 1) : 0;
              const end = end_line ? Math.min(lines.length, end_line) : lines.length;
              text = lines.slice(start, end).join("\n");
            }
            
            return {
              text: text,
              path: path,
            };
          } catch (e) {
            // 文件不存在时返回空字符串
            return {
              text: "",
              path: path,
            };
          }
        },
      },
      memory_forget: {
        description: "Delete a specific memory by ID",
        parameters: Type.Object({
          memory_id: Type.String({ description: "ID of the memory to delete" }),
        }),
        async execute({ memory_id }, context: any) {
          await provider.delete(memory_id);
          return {
            content: JSON.stringify({ status: "success", message: "Memory deleted" }),
            contentType: "json",
          };
        },
      },
    },
  };
});
