#!/usr/bin/env node
/**
 * Flow Think MCP Server - Entry Point
 *
 * A Model Context Protocol server providing structured thinking capabilities
 * for the Flow Framework. Enables cascaded reasoning with step tracking,
 * confidence scoring, revision support, and Beads integration.
 *
 * @module flow-think-mcp
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { FLOW_THINK_TOOL } from "./schema.js";
import { loadConfig, logConfig } from "./config.js";
import { FlowThinkServer } from "./server.js";

// Get package version
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

let version = "0.1.0";
try {
  const pkg = JSON.parse(readFileSync(join(__dirname, "..", "package.json"), "utf8"));
  version = pkg.version;
} catch {
  // Use default version if package.json not found (during development)
}

const name = "flow-think-mcp";

// Create MCP server instance
const server = new Server(
  { name, version },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Load configuration
const config = loadConfig();

// Log startup
console.error("🧠 Flow Think MCP Server Starting...");
console.error(`   Version: ${version}`);
logConfig(config);

// Create FlowThink server instance
const flowServer = new FlowThinkServer(config);

// Register tool listing handler
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [FLOW_THINK_TOOL],
}));

// Register tool call handler
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name: toolName, arguments: args } = request.params;

  if (toolName === "flow_think") {
    return flowServer.processStep(args);
  }

  return {
    content: [
      {
        type: "text",
        text: JSON.stringify({
          error: `Unknown tool: ${toolName}`,
          available_tools: ["flow_think"],
        }),
      },
    ],
    isError: true,
  };
});

// Run the server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("✅ Flow Think MCP Server running on stdio");
  console.error("📚 Use 'flow_think' tool for structured reasoning");
  console.error("");
}

main().catch((error) => {
  console.error("❌ Fatal error:", error);
  process.exit(1);
});
