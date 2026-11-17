import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { CostRowView } from "../viewTypes";
import { CostTable } from "./CostTable";

const row = (key: string, label: string, over: Partial<CostRowView> = {}): CostRowView => ({
  key,
  label,
  calls: 3,
  tokensIn: 1200,
  tokensOut: 340,
  costUsd: 0.12,
  estimatedCalls: 0,
  ...over,
});

describe("CostTable", () => {
  it("names the table by its title and lists one row per entry", () => {
    render(
      <CostTable
        title="Par agent"
        firstColumn="Agent"
        rows={[
          row("a", "Stratège", { color: "#4539ac" }),
          row("b", "Scribe", { estimatedCalls: 2 }),
        ]}
      />,
    );
    const scroller = screen.getByRole("region", { name: "Par agent" });
    expect(scroller).toHaveAttribute("tabindex", "0"); // défilement au clavier
    const table = screen.getByRole("table", { name: "Par agent" });
    expect(within(table).getByRole("columnheader", { name: "Agent" })).toBeInTheDocument();
    const rows = within(table).getAllByRole("row");
    expect(rows).toHaveLength(3);
    const scribe = within(rows[2]!);
    expect(scribe.getByRole("rowheader", { name: "Scribe" })).toBeInTheDocument();
    expect(scribe.getByText("1 200")).toBeInTheDocument();
    expect(scribe.getByText("0,12 $")).toBeInTheDocument();
    expect(scribe.getAllByRole("cell").at(-1)).toHaveTextContent("2");
  });
});
