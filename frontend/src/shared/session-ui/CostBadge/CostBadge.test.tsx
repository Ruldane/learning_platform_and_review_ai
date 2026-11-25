import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CostBadge } from "./CostBadge";

const cost = { tokens_in: 10000, tokens_out: 2340, cost_usd: 0.0412, cap_tokens: 300000 };

describe("CostBadge", () => {
  it("formats token counts and US dollar amounts in English", () => {
    render(<CostBadge cost={cost} />);
    expect(screen.getByText(/12,340 tokens · ≈ \$0\.04/)).toBeInTheDocument();
  });

  it("puts tokens and the cap in the title", () => {
    render(<CostBadge cost={cost} />);
    const title = screen.getByText(/12,340 tokens/).getAttribute("title");
    expect(title).toBe("12,340 tokens used out of a 300,000 cap");
  });

  it("shows a placeholder before the first measure", () => {
    render(<CostBadge cost={null} />);
    expect(screen.getByText("Cost: not measured yet")).toBeInTheDocument();
  });

  it("never writes a non-zero cost as zero", () => {
    render(<CostBadge cost={{ ...cost, cost_usd: 0.0002 }} />);
    expect(screen.getByText(/· < \$0\.001/)).toBeInTheDocument();
    expect(screen.queryByText(/0\.000/)).not.toBeInTheDocument();
    expect(screen.queryByText(/≈ </)).not.toBeInTheDocument();
  });

  it("keeps sub-cent costs visible", () => {
    render(<CostBadge cost={{ ...cost, cost_usd: 0.004 }} />);
    expect(screen.getByText(/≈ \$0\.004/)).toBeInTheDocument();
  });
});
