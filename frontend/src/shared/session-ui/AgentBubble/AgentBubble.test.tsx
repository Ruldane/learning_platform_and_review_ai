import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AgentBubble } from "./AgentBubble";

describe("AgentBubble", () => {
  it("announces streaming text politely", () => {
    render(<AgentBubble agent="demo_critic" text="Bon" streaming intent="je relis" tools={[]} />);
    const region = screen.getByText("Bon").closest("[aria-live]");
    expect(region).toHaveAttribute("aria-live", "polite");
    expect(region).toHaveAttribute("aria-busy", "true");
    expect(screen.getByText("je relis")).toBeInTheDocument();
  });

  it("shows the intent in italics above the text", () => {
    render(
      <AgentBubble agent="scout" text="Voici" streaming={false} intent="je cherche" tools={[]} />,
    );
    const intent = screen.getByText("je cherche");
    expect(intent).toHaveClass("italic");
    expect(intent.compareDocumentPosition(screen.getByText("Voici"))).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING,
    );
  });

  it("always names the agent and is no longer busy once finished", () => {
    render(<AgentBubble agent="demo_critic" text="Fini" streaming={false} tools={[]} />);
    expect(screen.getByText("Critique")).toBeInTheDocument();
    expect(screen.getByText("Fini").closest("[aria-live]")).toHaveAttribute("aria-busy", "false");
  });

  it("falls back to the raw slug for an unknown agent", () => {
    render(<AgentBubble agent="mystere" text="Salut" streaming={false} tools={[]} />);
    expect(screen.getByText("mystere")).toBeInTheDocument();
  });

  it("renders the tool calls as chips and names the activity", () => {
    const tools = [{ callId: "c1", tool: "search", args: { q: "rust" } }];
    render(<AgentBubble agent="scout" text="" streaming tools={tools} />);
    expect(screen.getByText("search")).toBeInTheDocument();
    expect(screen.getByText("Cherche…")).toBeInTheDocument();
  });

  it("says it is thinking while nothing is written yet", () => {
    render(<AgentBubble agent="scout" text="" streaming tools={[]} />);
    expect(screen.getByText("Réfléchit…")).toBeInTheDocument();
  });

  it("says it is writing once text arrives", () => {
    render(<AgentBubble agent="scout" text="Début" streaming tools={[]} />);
    expect(screen.getByText("Écrit…")).toBeInTheDocument();
  });
});
