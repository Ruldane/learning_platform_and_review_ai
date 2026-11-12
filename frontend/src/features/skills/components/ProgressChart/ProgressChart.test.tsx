import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { HistoryPointView } from "../viewTypes";
import { ProgressChart } from "./ProgressChart";

const points: HistoryPointView[] = [
  { weekStart: "2026-11-02", counts: { declare: 4, en_cours: 1, valide: 0, prouve: 0 }, score: 18 },
  { weekStart: "2026-11-09", counts: { declare: 3, en_cours: 2, valide: 1, prouve: 0 }, score: 31 },
];

describe("ProgressChart", () => {
  it("draws one line per level", () => {
    const { container } = render(<ProgressChart points={points} />);
    expect(container.querySelectorAll(".recharts-line")).toHaveLength(5);
    const legend = container.querySelector(".recharts-legend-wrapper");
    for (const name of ["Déclaré", "En cours", "Validé", "Prouvé", "Score"]) {
      expect(legend).toHaveTextContent(name);
    }
  });

  it("gives every line its own stroke", () => {
    const { container } = render(<ProgressChart points={points} />);
    const strokes = Array.from(container.querySelectorAll(".recharts-line-curve")).map((path) =>
      path.getAttribute("stroke"),
    );
    expect(strokes).toHaveLength(5);
    expect(new Set(strokes).size).toBe(5);
  });

  it("gives the latest reading as text", () => {
    render(<ProgressChart points={points} />);
    expect(
      screen.getByText(
        "Dernier relevé, semaine du lun. 9 nov. : Déclaré 3, En cours 2, Validé 1, Prouvé 0 · score 31 sur 100",
      ),
    ).toBeInTheDocument();
  });

  it("names the chart for assistive technologies", () => {
    render(<ProgressChart points={points} />);
    expect(screen.getByRole("img", { name: "Progression par semaine" })).toBeInTheDocument();
  });

  it("says when there is no reading yet", () => {
    render(<ProgressChart points={[]} />);
    expect(screen.getByText("Aucun relevé pour l'instant")).toBeInTheDocument();
  });
});
