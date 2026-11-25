import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { SkillTrendView } from "../viewTypes";
import { SkillRanking } from "./SkillRanking";

const item = (over: Partial<SkillTrendView>): SkillTrendView => ({
  rank: 1,
  skill: "SQL",
  share: 0.62,
  deltaShare: null,
  isNew: false,
  ...over,
});

function rowOf(skill: string): HTMLElement {
  return screen.getByText(skill).closest("li") as HTMLElement;
}

describe("SkillRanking", () => {
  it("shows the rank, the skill and the share in words and in a bar", () => {
    render(<SkillRanking ranking={[item({ deltaShare: 8 })]} />);
    const row = within(screen.getByRole("list", { name: "Skills ranking" }));
    expect(row.getByText("1.")).toBeInTheDocument();
    expect(row.getByText("SQL")).toBeInTheDocument();
    expect(row.getByText("62% of postings")).toBeInTheDocument();
    const bar = rowOf("SQL").querySelector("[aria-hidden='true'] > div") as HTMLElement;
    expect(bar.style.width).toBe("62%");
  });

  it("writes the evolution so that colour is never the only signal", () => {
    render(
      <SkillRanking
        ranking={[
          item({ rank: 1, skill: "SQL", deltaShare: 8 }),
          item({ rank: 2, skill: "Python", share: 0.5, deltaShare: -2 }),
          item({ rank: 3, skill: "dbt", share: 0.3, deltaShare: 0 }),
          item({ rank: 4, skill: "Airflow", share: 0.2, deltaShare: null, isNew: true }),
        ]}
      />,
    );
    expect(rowOf("SQL")).toHaveTextContent("+8 pts");
    expect(rowOf("Python")).toHaveTextContent("−2 pts");
    expect(rowOf("dbt")).toHaveTextContent("stable");
    expect(rowOf("Airflow")).toHaveTextContent("new");
  });

  it("marks the first scan when there is no previous run", () => {
    render(<SkillRanking ranking={[item({ deltaShare: null, isNew: false })]} />);
    expect(rowOf("SQL")).toHaveTextContent("first scan");
  });

  it("keeps the bars out of the accessibility tree", () => {
    render(<SkillRanking ranking={[item({ deltaShare: 1 })]} />);
    expect(screen.queryByRole("progressbar")).toBeNull();
    expect(rowOf("SQL").querySelector("[aria-hidden='true']")).not.toBeNull();
  });

  it("says when there is nothing to rank", () => {
    render(<SkillRanking ranking={[]} />);
    expect(screen.getByText("No skills to rank for this scan.")).toBeInTheDocument();
    expect(screen.queryByRole("list")).toBeNull();
  });
});
