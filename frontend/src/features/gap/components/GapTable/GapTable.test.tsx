import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { GapRowView } from "../viewTypes";
import { GapTable } from "./GapTable";

const row = (skill: string, patch: Partial<GapRowView>): GapRowView => ({
  skill,
  required: false,
  level: null,
  action: "to_add",
  week: null,
  source: "posting",
  ...patch,
});

const ROWS: GapRowView[] = [
  row("React", { required: true, level: "valide", action: "in_program", week: 4 }),
  row("Docker", { required: true }),
  row("SQL", { level: "declare" }),
  row("SAP", { action: "out_of_scope" }),
  row("Kafka", { source: "cv_review" }),
];

function setup(props: Partial<Parameters<typeof GapTable>[0]> = {}) {
  const onToggle = vi.fn();
  const onAddToPlan = vi.fn();
  render(
    <GapTable
      rows={ROWS}
      selected={[]}
      onToggle={onToggle}
      onAddToPlan={onAddToPlan}
      adding={false}
      {...props}
    />,
  );
  return { onToggle, onAddToPlan };
}

const rowOf = (skill: string) => screen.getByRole("row", { name: new RegExp(skill) });

describe("GapTable", () => {
  it("shows the column headers and the action of each row", () => {
    setup();
    const headers = screen.getAllByRole("columnheader").map((header) => header.textContent);
    expect(headers).toEqual(["Selection", "Skill", "Required", "My level", "Action"]);
    expect(within(rowOf("React")).getByText("In your program, week 4")).toBeInTheDocument();
    expect(within(rowOf("React")).getByText("Validated")).toBeInTheDocument();
    expect(within(rowOf("Docker")).getByText("To add")).toBeInTheDocument();
    expect(within(rowOf("Docker")).getByText("Missing")).toBeInTheDocument();
    expect(within(rowOf("SAP")).getByText("Out of scope")).toBeInTheDocument();
  });

  it("gives a checkbox to eligible rows and rows outside the scope", () => {
    setup();
    expect(screen.getAllByRole("checkbox").map((box) => box.getAttribute("aria-label"))).toEqual([
      "Add Docker to the schedule",
      "Add SQL to the schedule",
      "Add SAP to the schedule",
      "Add Kafka to the schedule",
    ]);
    expect(within(rowOf("React")).queryByRole("checkbox")).not.toBeInTheDocument();
  });

  it("offers no checkbox for a skill already validated or proved", () => {
    setup({
      rows: [
        row("Go", { level: "valide" }),
        row("Rust", { level: "prouve" }),
        row("SQL", { level: "en_cours" }),
      ],
    });
    expect(within(rowOf("Go")).getByText("Already acquired")).toBeInTheDocument();
    expect(within(rowOf("Go")).queryByRole("checkbox")).toBeNull();
    expect(within(rowOf("Rust")).queryByRole("checkbox")).toBeNull();
    expect(within(rowOf("SQL")).getByRole("checkbox")).toBeInTheDocument();
  });

  it("marks the keywords sent by the CV review", () => {
    setup();
    expect(within(rowOf("Kafka")).getByText("flagged by the CV review")).toBeInTheDocument();
    expect(
      within(rowOf("Docker")).queryByText("flagged by the CV review"),
    ).not.toBeInTheDocument();
  });

  it("toggles a skill", async () => {
    const { onToggle } = setup();
    await userEvent.click(screen.getByRole("checkbox", { name: "Add SQL to the schedule" }));
    expect(onToggle).toHaveBeenCalledExactlyOnceWith("SQL");
  });

  it("counts the selection in the button", async () => {
    const { onAddToPlan } = setup({ selected: ["Docker", "SQL", "Kafka"] });
    await userEvent.click(screen.getByRole("button", { name: "Add to schedule (3)" }));
    expect(onAddToPlan).toHaveBeenCalledTimes(1);
  });

  it("disables the button without selection", () => {
    setup();
    expect(screen.getByRole("button", { name: "Add to schedule" })).toBeDisabled();
  });

  it("locks the other boxes at ten skills", () => {
    const many = Array.from({ length: 12 }, (_, index) => row(`Comp ${index}`, {}));
    setup({ rows: many, selected: many.slice(0, 10).map((r) => r.skill) });
    const boxes = screen.getAllByRole("checkbox");
    expect(boxes.filter((box) => box.hasAttribute("disabled"))).toHaveLength(2);
    expect(boxes[0]).toBeEnabled();
    expect(boxes[11]).toBeDisabled();
    expect(screen.getByText("10 skills max per addition.")).toBeInTheDocument();
  });

  it("locks everything while adding", () => {
    setup({ selected: ["Docker"], adding: true });
    expect(screen.getByRole("button", { name: "Adding…" })).toBeDisabled();
    for (const box of screen.getAllByRole("checkbox")) expect(box).toBeDisabled();
  });

  it("can be driven with the keyboard only", async () => {
    const { onToggle } = setup();
    await userEvent.tab();
    expect(screen.getByRole("checkbox", { name: "Add Docker to the schedule" })).toHaveFocus();
    await userEvent.keyboard(" ");
    expect(onToggle).toHaveBeenCalledExactlyOnceWith("Docker");
  });

  it("says when there is no row", () => {
    setup({ rows: [] });
    expect(screen.getByText("No skills to compare for this posting.")).toBeInTheDocument();
  });
});
