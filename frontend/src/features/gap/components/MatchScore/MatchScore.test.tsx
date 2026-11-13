import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MatchScore } from "./MatchScore";

describe("MatchScore", () => {
  it("shows the score, a gauge and its name", () => {
    render(<MatchScore score={62} />);
    expect(screen.getByText("62/100")).toBeInTheDocument();
    expect(screen.getByText("Score de match")).toBeInTheDocument();
    const gauge = screen.getByRole("meter", { name: "Score de match : 62 sur 100" });
    expect(gauge).toHaveAttribute("aria-valuenow", "62");
    expect(gauge).toHaveAttribute("aria-valuemin", "0");
    expect(gauge).toHaveAttribute("aria-valuemax", "100");
  });

  it("promises nothing", () => {
    render(<MatchScore score={95} />);
    expect(screen.getByText(/il ne prédit pas la réponse d'un recruteur/)).toBeInTheDocument();
  });

  it("keeps the score between 0 and 100", () => {
    const { rerender } = render(<MatchScore score={140} />);
    expect(screen.getByText("100/100")).toBeInTheDocument();
    rerender(<MatchScore score={-3} />);
    expect(screen.getByText("0/100")).toBeInTheDocument();
    rerender(<MatchScore score={61.6} />);
    expect(screen.getByText("62/100")).toBeInTheDocument();
  });
});
