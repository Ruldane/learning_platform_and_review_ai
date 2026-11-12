import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CouncilStageBar } from "./CouncilStageBar";

describe("CouncilStageBar", () => {
  it("lists the five stages in order", () => {
    render(<CouncilStageBar stage="framing" round={0} rounds={3} />);
    const list = screen.getByRole("list", { name: "Étapes du Conseil" });
    expect(list.textContent).toMatch(/Cadrage.*Recherche.*Débat.*Propositions.*Programme/);
    expect(screen.getAllByRole("listitem")).toHaveLength(5);
  });

  it("marks the current stage", () => {
    render(<CouncilStageBar stage="debate" round={2} rounds={3} />);
    expect(screen.getByText("Débat")).toHaveAttribute("aria-current", "step");
    expect(screen.getByText("Cadrage")).not.toHaveAttribute("aria-current");
    expect(screen.getByText("Programme")).not.toHaveAttribute("aria-current");
  });

  it("says which stages are over, for screen readers", () => {
    render(<CouncilStageBar stage="debate" round={1} rounds={3} />);
    const framing = screen.getByText("Cadrage").closest("li");
    expect(framing).toHaveTextContent("terminée");
    expect(screen.getByText("Propositions").closest("li")).not.toHaveTextContent("terminée");
  });

  it("shows the round during the debate only", () => {
    const { rerender } = render(<CouncilStageBar stage="debate" round={2} rounds={3} />);
    expect(screen.getByText("Tour 2 / 3")).toBeInTheDocument();
    rerender(<CouncilStageBar stage="proposals" round={3} rounds={3} />);
    expect(screen.queryByText(/Tour/)).toBeNull();
  });

  it("does not show a round that has not started", () => {
    render(<CouncilStageBar stage="debate" round={0} rounds={3} />);
    expect(screen.queryByText(/Tour/)).toBeNull();
  });
});
