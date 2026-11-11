import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CostBadge } from "./CostBadge";

const cost = { tokens_in: 10000, tokens_out: 2340, cost_usd: 0.0412, cap_tokens: 300000 };

describe("CostBadge", () => {
  it("formats tokens and cost in French", () => {
    render(<CostBadge cost={cost} />);
    expect(screen.getByText(/12 340 tokens · ≈ 0,04 \$/)).toBeInTheDocument();
  });

  it("puts tokens and the cap in the title", () => {
    render(<CostBadge cost={cost} />);
    const title = screen.getByText(/12 340 tokens/).getAttribute("title") ?? "";
    expect(title.replace(/\s/g, " ")).toBe("12 340 tokens utilisés sur un plafond de 300 000");
  });

  it("shows a placeholder before the first measure", () => {
    render(<CostBadge cost={null} />);
    expect(screen.getByText("Coût : pas encore mesuré")).toBeInTheDocument();
  });

  it("keeps sub-cent costs visible", () => {
    render(<CostBadge cost={{ ...cost, cost_usd: 0.004 }} />);
    expect(screen.getByText(/≈ 0,004 \$/)).toBeInTheDocument();
  });
});
