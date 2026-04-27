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
  private client: any;
  private initPromise: Promise<void> | null = null;

  constructor(
    private readonly apiKey: string,
    private readonly host?: string,
    private readonly userId?: string,
  ) { }

  private async ensureClient(): Promise<void> {
    if (this.client) return;
    if (this.initPromise) return this.initPromise;
    this.initPromise = this._init();
    return this.initPromise;
  }

  private async _init(): Promise<void> {
    const { CognixClient } = await import("./lib/cognix.js");
    const opts = { 
      apiKey: this.apiKey,
      host: this.host,
      userId: this.userId
    };
    this.client = new CognixClient(opts);
  }

  async add(
    messages: Array<{ role: string; content: string }>,
    options: AddOptions,
  ): Promise<AddResult> {
    await this.ensureClient();
    const opts: Record<string, unknown> = { 
      user_id: options.user_id,
      long_term: options.long_term ?? true
    };
    if (options.run_id) opts.run_id = options.run_id;
    if (options.custom_instructions)
      opts.custom_instructions = options.custom_instructions;
    if (options.agent_id) opts.agent_id = options.agent_id;

    const result = await this.client.add(messages, opts);
    return normalizeAddResult(result);
  }

  async search(query: string, options: SearchOptions): Promise<MemoryItem[]> {
    await this.ensureClient();
    const opts: Record<string, unknown> = { user_id: options.user_id };
    if (options.run_id) opts.run_id = options.run_id;
    if (options.top_k != null) opts.top_k = options.top_k;
    if (options.threshold != null) opts.threshold = options.threshold;
    if (options.agent_id) opts.agent_id = options.agent_id;

    const results = await this.client.search(query, opts);
    return normalizeSearchResults(results);
  }

  async get(memoryId: string): Promise<MemoryItem> {
    await this.ensureClient();
    const result = await this.client.get(memoryId);
    return normalizeMemoryItem(result);
  }

  async getAll(options: ListOptions): Promise<MemoryItem[]> {
    await this.ensureClient();
    const opts: Record<string, unknown> = { user_id: options.user_id };
    if (options.run_id) opts.run_id = options.run_id;
    if (options.page_size != null) opts.page_size = options.page_size;

    const results = await this.client.getAll(opts);
    if (Array.isArray(results)) return results.map(normalizeMemoryItem);
    if (results?.results && Array.isArray(results.results))
      return results.results.map(normalizeMemoryItem);
    return [];
  }

  async delete(memoryId: string): Promise<void> {
    await this.ensureClient();
    await this.client.delete(memoryId);
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
        description: "Search user memories using semantic search",
        parameters: Type.Object({
          query: Type.String({ description: "Search query to find relevant memories" }),
          top_k: Type.Optional(Type.Number({ description: "Number of results to return", default: 5 })),
          threshold: Type.Optional(Type.Number({ description: "Minimum similarity score", default: 0.5 })),
          long_term: Type.Optional(Type.Boolean({ description: "Search long-term memories only", default: true })),
        }),
        async execute({ query, top_k, threshold }, context: any) {
          const results = await provider.search(query, {
            user_id: context.userId ?? config.userId,
            agent_id: context.agentId ?? config.agentId,
            top_k: top_k ?? config.topK,
            threshold: threshold ?? config.searchThreshold,
          });
          return {
            content: JSON.stringify(results, null, 2),
            contentType: "json",
          };
        },
      },
      memory_store: {
        description: "Store new memory for the user",
        parameters: Type.Object({
          content: Type.String({ description: "Memory content to store" }),
          long_term: Type.Optional(Type.Boolean({ description: "Store as long-term memory", default: true })),
          metadata: Type.Optional(Type.Record(Type.String(), Type.Any(), { description: "Additional metadata" })),
        }),
        async execute({ content, long_term, metadata }, context: any) {
          const result = await provider.add(
            [{ role: "user", content }],
            {
              user_id: context.userId ?? config.userId,
              agent_id: context.agentId ?? config.agentId,
              run_id: context.runId,
              long_term,
            }
          );
          return {
            content: JSON.stringify(result, null, 2),
            contentType: "json",
          };
        },
      },
      memory_list: {
        description: "List all memories for the user",
        parameters: Type.Object({
          limit: Type.Optional(Type.Number({ description: "Maximum number of memories to return", default: 20 })),
        }),
        async execute({ limit }, context: any) {
          const results = await provider.getAll({
            user_id: context.userId ?? config.userId,
            agent_id: context.agentId ?? config.agentId,
            page_size: limit,
          });
          return {
            content: JSON.stringify(results, null, 2),
            contentType: "json",
          };
        },
      },
      memory_get: {
        description: "Get a specific memory by ID",
        parameters: Type.Object({
          memory_id: Type.String({ description: "ID of the memory to retrieve" }),
        }),
        async execute({ memory_id }, context: any) {
          const result = await provider.get(memory_id);
          return {
            content: JSON.stringify(result, null, 2),
            contentType: "json",
          };
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
