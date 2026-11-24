import { act, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  briefOut,
  criterionOut,
  evaluationOut,
  projectOut,
  submissionOut,
} from "@/test/projectsApi";
import { openStream, renderProjects } from "@/test/projectsHarness";
import { PortfolioPage } from "../PortfolioPage";
import { ProjectPage } from "./ProjectPage";

const setup = (api: Parameters<typeof renderProjects>[1]) =>
  renderProjects(
    (createSocket) => ({
      portfolio: <PortfolioPage />,
      project: <ProjectPage createSocket={createSocket} />,
    }),
    api,
    "/skills/portfolio/p1",
  );

const advance = (ms: number) => act(() => vi.advanceTimersByTimeAsync(ms));

// Le flux reste muet : seule la relecture de repli de 5 s peut voir le statut changer.
describe("ProjectPage : relecture de secours", () => {
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }));
  afterEach(() => vi.useRealTimers());

  it("re-reads a project under review, shows the result, then stops reading", async () => {
    const reviewing = projectOut("p1", {
      status: "reviewing",
      session_id: "sess-r",
      submissions: [submissionOut()],
    });
    const { state, settle, sockets } = setup({ projects: [reviewing] });
    await screen.findByRole("heading", { name: "Évaluation en cours" });
    await openStream(sockets, "sess-r");

    const before = state.reads;
    await advance(5_500);
    expect(state.reads).toBeGreaterThan(before);
    expect(screen.getByRole("heading", { name: "Évaluation en cours" })).toBeVisible();

    settle("p1", {
      status: "to_redo",
      session_id: null,
      evaluation: evaluationOut({ results: [criterionOut(1, true, "Requête correcte.")] }),
    });
    await advance(5_500);
    expect(await screen.findByText("Projet à refaire")).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Évaluation en cours" })).toBeNull();

    const settled = state.reads;
    await advance(21_000);
    expect(state.reads).toBe(settled);
  });

  it("re-reads a brief being written, shows it when written, then stops reading", async () => {
    const pending = projectOut("p1", {
      status: "brief_pending",
      brief: null,
      session_id: "sess-b",
    });
    const { state, settle, sockets } = setup({ projects: [pending] });
    await screen.findByRole("heading", { name: "Énoncé en cours d'écriture" });
    await openStream(sockets, "sess-b");

    settle("p1", { status: "todo", brief: briefOut(), session_id: null });
    await advance(5_500);
    expect(await screen.findByText("Durée estimée : 6 h")).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Énoncé en cours d'écriture" })).toBeNull();

    const settled = state.reads;
    await advance(21_000);
    expect(state.reads).toBe(settled);
  });

  it("never polls a project that waits for January", async () => {
    const { state } = setup({ projects: [projectOut("p1")] });
    await screen.findByText("Durée estimée : 6 h");
    const first = state.reads;
    await advance(21_000);
    expect(state.reads).toBe(first);
  });
});
