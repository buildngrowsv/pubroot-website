/**
 * Builds a (stateless) MCP server instance exposing the read-only Pubroot tools.
 *
 * Uses the low-level `Server` from the official @modelcontextprotocol/sdk with
 * hand-written JSON Schemas (no zod→JSON-Schema conversion per request) to keep
 * CPU time per request small on the Workers Free plan.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { CfWorkerJsonSchemaValidator } from "@modelcontextprotocol/sdk/validation/cfworker";
import {
  CallToolRequestSchema,
  ErrorCode,
  ListToolsRequestSchema,
  McpError,
  type CallToolResult,
} from "@modelcontextprotocol/sdk/types.js";
import type { Env } from "./data.js";
import { TOOL_DEFINITIONS, TOOL_NAMES, ToolInputError, callTool } from "./tools.js";

export const SERVER_NAME = "pubroot";
export const SERVER_VERSION = "0.2.0";

const INSTRUCTIONS =
  "Read-only access to Pubroot (https://pubroot.com), an AI peer-reviewed knowledge base. " +
  "Use search_papers / get_paper / get_review to find papers and their reviews, verify_claim to look up " +
  "claims checked in reviews, get_related_work for related papers, and get_submission_guide / " +
  "prepare_submission to draft a submission (prepare_submission only returns a prefilled GitHub issue URL; " +
  "it never creates anything).";

function asResult(data: Record<string, unknown>, isError = false): CallToolResult {
  return {
    content: [{ type: "text", text: JSON.stringify(data, null, 2) }],
    structuredContent: data,
    ...(isError ? { isError: true } : {}),
  };
}

export function createMcpServer(env: Env): Server {
  const server = new Server(
    { name: SERVER_NAME, version: SERVER_VERSION, title: "Pubroot (read-only)", websiteUrl: "https://pubroot.com" },
    {
      capabilities: { tools: { listChanged: false } },
      instructions: INSTRUCTIONS,
      // ajv (the SDK default) relies on code generation, which Workers forbid.
      jsonSchemaValidator: new CfWorkerJsonSchemaValidator(),
    },
  );

  server.setRequestHandler(ListToolsRequestSchema, async () => ({
    tools: TOOL_DEFINITIONS as unknown as Array<Record<string, unknown>> as never,
  }));

  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;
    if (!TOOL_NAMES.has(name)) {
      throw new McpError(ErrorCode.InvalidParams, `Unknown tool: ${name}`);
    }
    try {
      return asResult(await callTool(env, name, args));
    } catch (err) {
      if (err instanceof ToolInputError) {
        return asResult({ error: err.message }, true);
      }
      const msg = err instanceof Error ? err.message : String(err);
      return asResult({ error: `Tool failed: ${msg}` }, true);
    }
  });

  return server;
}
