/** TanStack Query keys of the feature: read names, never a token value. */
export const mcpKeys = {
  settings: ["mcp", "settings"] as const,
  features: ["mcp", "features"] as const,
  actions: ["mcp", "actions"] as const,
  tokens: ["mcp", "tokens"] as const,
  relay: ["mcp", "relay"] as const,
  confirmations: ["mcp", "confirmations"] as const,
  calls: ["mcp", "calls"] as const,
  changes: ["mcp", "changes"] as const,
} as const;
