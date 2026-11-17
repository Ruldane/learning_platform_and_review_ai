/** Clés TanStack Query de la feature : des noms de lectures, jamais une valeur de jeton. */
export const mcpKeys = {
  settings: ["mcp", "settings"] as const,
  features: ["mcp", "features"] as const,
  actions: ["mcp", "actions"] as const,
  tokens: ["mcp", "tokens"] as const,
  confirmations: ["mcp", "confirmations"] as const,
  calls: ["mcp", "calls"] as const,
  changes: ["mcp", "changes"] as const,
} as const;
