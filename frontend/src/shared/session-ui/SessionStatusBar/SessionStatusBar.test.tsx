import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SessionStatusBar } from "./SessionStatusBar";

const cost = { tokens_in: 100, tokens_out: 50, cost_usd: 0.01, cap_tokens: 300000 };

describe("SessionStatusBar", () => {
  it("shows status, step, round and cost", () => {
    render(<SessionStatusBar status="running" stepLabel="Debate" round={2} cost={cost} />);
    expect(screen.getByText("Running")).toBeInTheDocument();
    expect(screen.getByText("Debate")).toBeInTheDocument();
    expect(screen.getByText("Round 2")).toBeInTheDocument();
    expect(screen.getByText(/150 tokens/)).toBeInTheDocument();
  });

  it.each([
    ["codex", "Played by Codex"],
    ["claude-code", "Played by Claude"],
  ] as const)("identifies the %s client", (playedBy, label) => {
    render(<SessionStatusBar status="running" cost={null} playedBy={playedBy} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it("announces status changes politely", () => {
    render(<SessionStatusBar status="waiting_user" cost={null} />);
    expect(screen.getByText("Waiting for your answer").closest("[role=status]")).not.toBeNull();
  });

  it.each([
    ["paused", "Paused"],
    ["completed", "Completed"],
    ["failed", "Failed"],
    ["cancelled", "Cancelled"],
    ["expired", "Expired"],
  ] as const)("labels %s in English", (status, label) => {
    render(<SessionStatusBar status={status} cost={null} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it("omits the round when it is unknown", () => {
    render(<SessionStatusBar status="running" cost={null} />);
    expect(screen.queryByText(/^Round/)).toBeNull();
  });
});
