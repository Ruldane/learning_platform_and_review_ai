import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { PlanDiffView } from "./types";
import { PlanDiff } from "./PlanDiff";

const DIFF: PlanDiffView = {
  added: [{ id: "a1", title: "Lire la PEP 8", moduleTitle: "Style", plannedDate: "2026-11-17" }],
  removed: [
    { id: "r1", title: "Regarder la vidéo 3", moduleTitle: "Bases", plannedDate: "2026-11-19" },
  ],
  moved: [
    {
      id: "m1",
      title: "Pratiquer les boucles",
      moduleTitle: "Bases",
      from: "2026-11-16",
      to: "2026-11-18",
    },
  ],
};

describe("PlanDiff", () => {
  it("lists added, removed and moved tasks under their own heading", () => {
    render(<PlanDiff diff={DIFF} />);
    const added = screen.getByRole("region", { name: "Ajoutées" });
    expect(within(added).getByText("Lire la PEP 8")).toBeInTheDocument();
    const removed = screen.getByRole("region", { name: "Retirées" });
    expect(within(removed).getByText("Regarder la vidéo 3")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Déplacées" })).toBeInTheDocument();
  });

  it("lists moved tasks with both dates", () => {
    render(<PlanDiff diff={DIFF} />);
    expect(screen.getByText("Pratiquer les boucles")).toBeInTheDocument();
    expect(screen.getByText("lun. 16 nov. → mer. 18 nov.")).toBeInTheDocument();
  });

  it("leaves out the empty sections", () => {
    render(<PlanDiff diff={{ added: [], removed: DIFF.removed, moved: [] }} />);
    expect(screen.queryByRole("region", { name: "Ajoutées" })).toBeNull();
    expect(screen.queryByRole("region", { name: "Déplacées" })).toBeNull();
    expect(screen.getByRole("region", { name: "Retirées" })).toBeInTheDocument();
  });

  it("says when nothing changed", () => {
    render(<PlanDiff diff={{ added: [], removed: [], moved: [] }} />);
    expect(screen.getByText("Aucun changement.")).toBeInTheDocument();
  });
});
