import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SessionStatusBar } from "./SessionStatusBar";

const cost = { tokens_in: 100, tokens_out: 50, cost_usd: 0.01, cap_tokens: 300000 };

describe("SessionStatusBar", () => {
  it("shows status, step, round and cost", () => {
    render(<SessionStatusBar status="running" stepLabel="Débat" round={2} cost={cost} />);
    expect(screen.getByText("En cours")).toBeInTheDocument();
    expect(screen.getByText("Débat")).toBeInTheDocument();
    expect(screen.getByText("Tour 2")).toBeInTheDocument();
    expect(screen.getByText(/150 tokens/)).toBeInTheDocument();
  });

  it("announces status changes politely", () => {
    render(<SessionStatusBar status="waiting_user" cost={null} />);
    expect(screen.getByText("En attente de ta réponse").closest("[role=status]")).not.toBeNull();
  });

  it.each([
    ["paused", "En pause"],
    ["completed", "Terminée"],
    ["failed", "Échouée"],
    ["cancelled", "Annulée"],
  ] as const)("labels %s in French", (status, label) => {
    render(<SessionStatusBar status={status} cost={null} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it("omits the round when it is unknown", () => {
    render(<SessionStatusBar status="running" cost={null} />);
    expect(screen.queryByText(/^Tour/)).toBeNull();
  });
});
