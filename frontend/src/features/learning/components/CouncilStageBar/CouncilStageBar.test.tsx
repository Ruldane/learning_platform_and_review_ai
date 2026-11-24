import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CouncilStageBar } from "./CouncilStageBar";

describe("CouncilStageBar", () => {
  it("lists the five stages in order", () => {
    render(<CouncilStageBar stage="framing" round={0} rounds={3} />);
    const list = screen.getByRole("list", { name: "Council stages" });
    expect(list.textContent).toMatch(/Framing.*Research.*Debate.*Proposals.*Program/);
    expect(screen.getAllByRole("listitem")).toHaveLength(5);
  });

  it("marks the current stage", () => {
    render(<CouncilStageBar stage="debate" round={2} rounds={3} />);
    expect(screen.getByText("Debate")).toHaveAttribute("aria-current", "step");
    expect(screen.getByText("Framing")).not.toHaveAttribute("aria-current");
    expect(screen.getByText("Program")).not.toHaveAttribute("aria-current");
  });

  it("says which stages are over, for screen readers", () => {
    render(<CouncilStageBar stage="debate" round={1} rounds={3} />);
    const framing = screen.getByText("Framing").closest("li");
    expect(framing).toHaveTextContent("done");
    expect(screen.getByText("Proposals").closest("li")).not.toHaveTextContent("done");
  });

  it("shows the round during the debate only", () => {
    const { rerender } = render(<CouncilStageBar stage="debate" round={2} rounds={3} />);
    expect(screen.getByText("Round 2 / 3")).toBeInTheDocument();
    rerender(<CouncilStageBar stage="proposals" round={3} rounds={3} />);
    expect(screen.queryByText(/Round/)).toBeNull();
  });

  it("does not show a round that has not started", () => {
    render(<CouncilStageBar stage="debate" round={0} rounds={3} />);
    expect(screen.queryByText(/Round/)).toBeNull();
  });
});
