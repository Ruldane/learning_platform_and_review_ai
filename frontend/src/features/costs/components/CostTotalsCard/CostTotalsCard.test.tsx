import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { CostTotalsView } from "../viewTypes";
import { CostTotalsCard } from "./CostTotalsCard";

const totals: CostTotalsView = {
  calls: 12,
  tokensIn: 4800,
  tokensOut: 1360,
  costUsd: 0.42,
  estimatedCalls: 3,
};

describe("CostTotalsCard", () => {
  it("gives calls, tokens and cost for the window", () => {
    render(<CostTotalsCard days={7} totals={totals} />);
    expect(screen.getByRole("heading", { name: "Total over 7 days" })).toBeInTheDocument();
    expect(screen.getByText("4,800")).toBeInTheDocument();
    expect(screen.getByText("1,360")).toBeInTheDocument();
    expect(screen.getByText("$0.42")).toBeInTheDocument();
    expect(screen.getByText("including 3 estimated")).toBeInTheDocument();
  });

  it("says nothing about estimates when none is estimated", () => {
    render(<CostTotalsCard days={7} totals={{ ...totals, estimatedCalls: 0 }} />);
    expect(screen.queryByText(/including \d+ estimated/)).not.toBeInTheDocument();
  });

  it("uses the singular for one estimated call", () => {
    render(<CostTotalsCard days={7} totals={{ ...totals, estimatedCalls: 1 }} />);
    expect(screen.getByText("including 1 estimated")).toBeInTheDocument();
  });
});
