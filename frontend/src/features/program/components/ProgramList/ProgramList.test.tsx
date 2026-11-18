import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import type { ProgramSummaryView } from "../viewTypes";
import { ProgramList } from "./ProgramList";

const programs: ProgramSummaryView[] = [
  { id: "new", title: "Bases du ML", status: "draft", startDate: "2026-11-16", weeks: 12, percent: 0 },
  {
    id: "old",
    title: "Python pour la data",
    status: "validated",
    startDate: "2026-10-05",
    weeks: 1,
    percent: 25,
  },
];

describe("ProgramList", () => {
  it("links every program with its status, weeks and progress", () => {
    render(
      <MemoryRouter>
        <ProgramList programs={programs} />
      </MemoryRouter>,
    );
    const [first, second] = screen.getAllByRole("listitem") as [HTMLElement, HTMLElement];
    expect(within(first).getByRole("link", { name: "Bases du ML" })).toHaveAttribute(
      "href",
      "/apprendre/programme/new",
    );
    expect(within(first).getByText("Brouillon")).toBeInTheDocument();
    expect(within(first).getByText("12 semaines")).toBeInTheDocument();
    expect(within(second).getByText("Validé")).toBeInTheDocument();
    expect(within(second).getByText("1 semaine")).toBeInTheDocument();
    expect(within(second).getByRole("progressbar")).toHaveAttribute("aria-valuenow", "25");
    expect(within(second).getByText("25 %")).toBeInTheDocument();
  });
});
