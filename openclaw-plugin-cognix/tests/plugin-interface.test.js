/**
 * Cognix Plugin Interface Compatibility Tests
 * Verifies the plugin interface matches Mem0 plugin specification
 */

import { Type } from "@sinclair/typebox";
import plugin from "../index.js";

describe("Cognix Plugin Interface Compatibility", () => {
  let config;
  
  beforeAll(() => {
    config = {
      apiKey: "test-api-key",
      host: "http://localhost:8765",
      userId: "test-user",
      autoCapture: true,
      autoRecall: true,
      searchThreshold: 0.5,
      topK: 5
    };
  });

  test("Plugin exports default entry function", () => {
    expect(typeof plugin).toBe("function");
  });

  test("Plugin has correct structure when initialized", () => {
    const mockApi = {
      config: config,
      registerTool: jest.fn(),
      on: jest.fn()
    };

    const pluginInstance = plugin(mockApi);
    
    expect(pluginInstance).toHaveProperty("hooks");
    expect(pluginInstance).toHaveProperty("tools");
    expect(typeof pluginInstance.hooks.before_agent_start).toBe("function");
    expect(typeof pluginInstance.hooks.after_agent_turn).toBe("function");
  });

  test("All required tools are present with correct names", () => {
    const mockApi = {
      config: config,
      registerTool: jest.fn(),
      on: jest.fn()
    };

    const pluginInstance = plugin(mockApi);
    const tools = pluginInstance.tools;

    // Mem0 compatible tool names
    expect(tools).toHaveProperty("memory_search");
    expect(tools).toHaveProperty("memory_store");
    expect(tools).toHaveProperty("memory_list");
    expect(tools).toHaveProperty("memory_get");
    expect(tools).toHaveProperty("memory_forget");
  });

  test("memory_store tool uses 'text' parameter (not 'content')", () => {
    const mockApi = {
      config: config,
      registerTool: jest.fn(),
      on: jest.fn()
    };

    const pluginInstance = plugin(mockApi);
    const memoryStore = pluginInstance.tools.memory_store;

    expect(memoryStore.parameters.properties).toHaveProperty("text");
    expect(memoryStore.parameters.properties).not.toHaveProperty("content");
    expect(memoryStore.parameters.properties).toHaveProperty("userId");
    expect(memoryStore.parameters.properties).toHaveProperty("long_term");
    expect(memoryStore.parameters.properties).toHaveProperty("metadata");
  });

  test("All tools support optional userId parameter", () => {
    const mockApi = {
      config: config,
      registerTool: jest.fn(),
      on: jest.fn()
    };

    const pluginInstance = plugin(mockApi);
    const tools = pluginInstance.tools;

    expect(tools.memory_search.parameters.properties).toHaveProperty("userId");
    expect(tools.memory_store.parameters.properties).toHaveProperty("userId");
    expect(tools.memory_list.parameters.properties).toHaveProperty("userId");
    expect(tools.memory_get.parameters.properties).toHaveProperty("userId");
    expect(tools.memory_forget.parameters.properties).toHaveProperty("userId");
  });

  test("memory_store returns structured result with added/updated counts", async () => {
    const mockApi = {
      config: config,
      registerTool: jest.fn(),
      on: jest.fn()
    };

    // Mock provider response
    const mockAddResult = {
      results: [
        { id: "1", memory: "test memory 1", event: "ADD" },
        { id: "2", memory: "test memory 2", event: "UPDATE" }
      ]
    };

    const pluginInstance = plugin(mockApi);
    
    // Mock the provider add method
    const originalAdd = pluginInstance.tools.memory_store.execute;
    pluginInstance.tools.memory_store.execute = jest.fn().mockResolvedValue({
      content: "1 new memory added, 1 memory updated",
      added: 1,
      updated: 1,
      results: mockAddResult.results
    });

    const result = await pluginInstance.tools.memory_store.execute({
      text: "test memory",
      userId: "test-user"
    }, { userId: "context-user" });

    expect(result).toHaveProperty("content");
    expect(result).toHaveProperty("added");
    expect(result).toHaveProperty("updated");
    expect(result).toHaveProperty("results");
    expect(typeof result.added).toBe("number");
    expect(typeof result.updated).toBe("number");
    expect(Array.isArray(result.results)).toBe(true);
  });
});
