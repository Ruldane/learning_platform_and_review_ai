import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { CostRowView } from "../viewTypes";
import { CostByDayChart } from "./CostByDayChart";

const day = (key: string, costUsd: number): CostRowView => ({
  key,
  label: key,
  calls: costUsd > 0 ? 2 : 0,
  tokensIn: costUsd > 0 ? 500 : 0,
  tokensOut: costUsd > 0 ? 100 : 0,
  costUsd,
  estimatedCalls: 0,
});

const rows = [day("2026-11-14", 0), day("2026-11-15", 0.2), day("2026-11-16", 0.05)];

describe("CostByDayChart", () => {
  it("draws the chart as a named image", () => {
    const { container } = render(
      <CostByDayChart rows={rows} since="2026-11-14" until="2026-11-16" totalCostUsd={0.25} />,
    );
    expect(
      screen.getByRole("img", {
        name: "Coût par jour, du sam. 14 nov. au lun. 16 nov. : 0,25 $ au total",
      }),
    ).toBeInTheDocument();
    expect(container.querySelector(".recharts-bar")).toBeInTheDocument();
  });

  it("gives the same figures as a table, one row per day", () => {
    render(
      <CostByDayChart rows={rows} since="2026-11-14" until="2026-11-16" totalCostUsd={0.25} />,
    );
    const table = screen.getByRole("table", { name: "Appels, jetons et coût par jour" });
    expect(within(table).getAllByRole("row")).toHaveLength(4);
    const monday = within(within(table).getByRole("row", { name: /lun\. 16 nov\./ }));
    expect(monday.getByText("0,05 $")).toBeInTheDocument();
    expect(monday.getByText("500")).toBeInTheDocument();
  });
});
