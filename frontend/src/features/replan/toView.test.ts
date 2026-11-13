import { describe, expect, it } from "vitest";
import { buildVersion, versionOut } from "@/test/replanApi";
import { pendingVersion, toPlanDiffView, toVersionView } from "./toView";
import type { PlanVersionOut } from "./types";

const out = (over: Record<string, unknown> = {}) => versionOut(over) as unknown as PlanVersionOut;

describe("replan toView", () => {
  it("splits « module / tâche » keys into the shared diff shape", () => {
    const diff = toPlanDiffView(out().diff!);
    expect(diff.added).toEqual([
      {
        id: "Web / Réviser les verbes",
        title: "Réviser les verbes",
        moduleTitle: "Web",
        plannedDate: null,
      },
    ]);
    expect(diff.moved[0]).toMatchObject({
      title: "Lire le chapitre 1",
      from: "2026-11-16",
      to: "2026-11-18",
    });
  });

  it("keeps a key without module as a bare title", () => {
    const diff = toPlanDiffView({
      added: ["Seule"],
      removed: [],
      moved: [],
      weeks_before: 1,
      weeks_after: 1,
    });
    expect(diff.added[0]).toMatchObject({ title: "Seule", moduleTitle: "" });
  });

  it("renames the loads and keeps a build version without diff", () => {
    const view = toVersionView(out());
    expect(view.weekLoads[0]).toEqual({
      rank: 1,
      startDate: "2026-11-16",
      before: 600,
      after: 540,
      cap: 714,
    });
    expect(toVersionView(buildVersion() as unknown as PlanVersionOut).diff).toBeNull();
  });

  it("finds the pending proposal only", () => {
    const views = [toVersionView(out({ status: "refused" })), toVersionView(out({ version: 3 }))];
    expect(pendingVersion(views)?.version).toBe(3);
    expect(pendingVersion([views[0]!])).toBeNull();
  });
});
