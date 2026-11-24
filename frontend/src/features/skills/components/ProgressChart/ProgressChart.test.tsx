import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { HistoryPointView } from "../viewTypes";
import { ProgressChart } from "./ProgressChart";

const points: HistoryPointView[] = [
  {
    weekStart: "2026-11-02",
    counts: { declared: 4, in_progress: 1, validated: 0, proven: 0 },
    score: 18,
  },
  {
    weekStart: "2026-11-09",
    counts: { declared: 3, in_progress: 2, validated: 1, proven: 0 },
    score: 31,
  },
];

describe("ProgressChart", () => {
  it("draws one line per level", () => {
    const { container } = render(<ProgressChart points={points} />);
    expect(container.querySelectorAll(".recharts-line")).toHaveLength(5);
    const legend = container.querySelector(".recharts-legend-wrapper");
    for (const name of ["Declared", "In progress", "Validated", "Proven", "Score"]) {
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
        /Latest snapshot, week of .+: Declared 3, In progress 2, Validated 1, Proven 0 · score 31/,
      ),
    ).toBeInTheDocument();
  });

  it("names the chart for assistive technologies", () => {
    render(<ProgressChart points={points} />);
    expect(screen.getByRole("img", { name: "Progress by week" })).toBeInTheDocument();
  });

  it("says when there is no reading yet", () => {
    render(<ProgressChart points={[]} />);
    expect(screen.getByText("No snapshots yet")).toBeInTheDocument();
  });
});
