import { describe, expect, it } from "vitest";
import * as sessionUi from "./index";

describe("session-ui public API", () => {
  it("exports every shared session component and the agent identities", () => {
    const names = [
      "AgentBubble",
      "UserMessageBubble",
      "ToolChip",
      "DebateFeed",
      "InterruptCard",
      "FreeTextAnswer",
      "SessionStatusBar",
      "CostBadge",
      "SessionControls",
      "MessageComposer",
      "Board",
      "MermaidSvg",
      "SourcesPanel",
      "SourceCard",
      "sourcesFromEvents",
      "AGENT_COLORS",
      "agentIdentity",
    ];
    for (const name of names) expect(sessionUi).toHaveProperty(name);
  });
});
