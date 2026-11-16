import { describe, expect, it } from "vitest";
import {
  criterionOut,
  evaluationOut,
  fourDrafts,
  projectOut,
  submissionOut,
} from "@/test/projectsFixtures";
import { groupByStatus, toCardView, toDetailView } from "./toView";
import type { ProjectOut, ProjectSummary } from "./types";

const asOut = (over: Record<string, unknown> = {}) =>
  projectOut("p1", over) as unknown as ProjectOut;

const card = (id: string, status: ProjectSummary["status"]) =>
  toCardView({
    id,
    module_id: id,
    program_id: "p",
    program_title: null,
    week: 1,
    rank: 1,
    title: id,
    status,
    hours: 6,
    skills: [],
    validated_at: null,
    profile_version: null,
    session_id: null,
  });

describe("groupByStatus", () => {
  it("orders the groups, keeps the program order inside them and drops the empty ones", () => {
    const groups = groupByStatus([
      card("a", "validated"),
      card("b", "todo"),
      card("c", "to_redo"),
      card("d", "todo"),
    ]);
    expect(groups.map((g) => g.status)).toEqual(["to_redo", "todo", "validated"]);
    expect(groups[1]!.projects.map((p) => p.id)).toEqual(["b", "d"]);
  });

  it("gives every card the address of its page", () => {
    expect(card("p9", "todo").href).toBe("/competences/portfolio/p9");
  });
});

describe("toDetailView", () => {
  it("derives `hasScreenshots` from the latest submission", () => {
    const some = toDetailView(
      asOut({
        evaluation: evaluationOut(),
        submissions: [submissionOut({ screenshots: 2 }), submissionOut({ screenshots: 0 })],
      }),
    );
    expect(some.evaluation?.hasScreenshots).toBe(true);
    const none = toDetailView(
      asOut({
        evaluation: evaluationOut(),
        submissions: [submissionOut({ screenshots: 0 }), submissionOut({ screenshots: 3 })],
      }),
    );
    expect(none.evaluation?.hasScreenshots).toBe(false);
  });

  it("keeps the results as the server gives them, by index, without their text", () => {
    const view = toDetailView(
      asOut({
        evaluation: evaluationOut({
          results: [criterionOut(2, false, "Non."), criterionOut(1, true)],
        }),
      }),
    );
    expect(view.evaluation?.results).toEqual([
      { index: 2, met: false, comment: "Non." },
      { index: 1, met: true, comment: "" },
    ]);
  });

  it("numbers the submissions for the screenshot route: the latest is 1", () => {
    const view = toDetailView(
      asOut({
        submissions: [submissionOut({ screenshots: 2 }), submissionOut({ screenshots: 1 })],
      }),
    );
    expect(view.submissions[0]!.screenshots.map((s) => s.src.split("/projects/")[1])).toEqual([
      "p1/screenshots/1?submission=1",
      "p1/screenshots/2?submission=1",
    ]);
    expect(view.submissions[1]!.screenshots[0]!.src).toMatch(/screenshots\/1\?submission=2$/);
  });

  it("separates the entry draft from the three text drafts", () => {
    const view = toDetailView(asOut({ status: "validated", drafts: fourDrafts() }));
    expect(view.drafts.map((d) => d.kind)).toEqual(["cv_line", "linkedin_post", "readme_plan"]);
    expect(view.entryDraft?.kind).toBe("profile_entry");
    expect(view.entry.name).toBe("Pipeline de ventes");
  });

  it("proposes the project title alone when there is no entry draft", () => {
    const view = toDetailView(asOut({ title: "Mon projet" }));
    expect(view.entry).toEqual({ name: "Mon projet", description: "", achievements: [] });
    expect(view.entryDraft).toBeNull();
  });
});
