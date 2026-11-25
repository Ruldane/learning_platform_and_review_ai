import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { PlanDiffView } from "./types";
import { PlanDiff } from "./PlanDiff";

const DIFF: PlanDiffView = {
  added: [{ id: "a1", title: "Read PEP 8", moduleTitle: "Style", plannedDate: "2026-11-17" }],
  removed: [
    { id: "r1", title: "Watch video 3", moduleTitle: "Basics", plannedDate: "2026-11-19" },
  ],
  moved: [
    {
      id: "m1",
      title: "Practice loops",
      moduleTitle: "Basics",
      from: "2026-11-16",
      to: "2026-11-18",
    },
  ],
};

describe("PlanDiff", () => {
  it("lists added, removed and moved tasks under their own heading", () => {
    render(<PlanDiff diff={DIFF} />);
    const added = screen.getByRole("region", { name: "Added" });
    expect(within(added).getByText("Read PEP 8")).toBeInTheDocument();
    const removed = screen.getByRole("region", { name: "Removed" });
    expect(within(removed).getByText("Watch video 3")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Moved" })).toBeInTheDocument();
  });

  it("lists moved tasks with both dates", () => {
    render(<PlanDiff diff={DIFF} />);
    expect(screen.getByText("Practice loops")).toBeInTheDocument();
    expect(screen.getByText("Mon 16 Nov → Wed 18 Nov")).toBeInTheDocument();
  });

  it("leaves out the empty sections", () => {
    render(<PlanDiff diff={{ added: [], removed: DIFF.removed, moved: [] }} />);
    expect(screen.queryByRole("region", { name: "Added" })).toBeNull();
    expect(screen.queryByRole("region", { name: "Moved" })).toBeNull();
    expect(screen.getByRole("region", { name: "Removed" })).toBeInTheDocument();
  });

  it("says when nothing changed", () => {
    render(<PlanDiff diff={{ added: [], removed: [], moved: [] }} />);
    expect(screen.getByText("No changes.")).toBeInTheDocument();
  });

  it("leaves out the module line when the module is unknown", () => {
    const task = { id: "a", title: "Standalone task", moduleTitle: "", plannedDate: null };
    render(<PlanDiff diff={{ added: [task], removed: [], moved: [] }} />);
    expect(screen.getByText("Standalone task")).toBeInTheDocument();
    expect(screen.queryByText(/Module/)).toBeNull();
  });
});
