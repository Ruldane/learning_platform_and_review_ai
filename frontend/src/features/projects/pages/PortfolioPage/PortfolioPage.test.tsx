import { screen, waitFor, within } from "@testing-library/react";
import { HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { apiError } from "@/test/councilHarness";
import { fourDrafts, projectOut } from "@/test/projectsApi";
import { renderProjects } from "@/test/projectsHarness";
import { ProjectPage } from "../ProjectPage";
import { PortfolioPage } from "./PortfolioPage";

const setup = (api: Parameters<typeof renderProjects>[1] = {}, path?: string) =>
  renderProjects(
    (createSocket) => ({
      portfolio: <PortfolioPage />,
      project: <ProjectPage createSocket={createSocket} />,
    }),
    api,
    path,
  );

const PROJECTS = [
  projectOut("p1", { title: "Pipeline de ventes", status: "validated", drafts: fourDrafts() }),
  projectOut("p2", { title: "Tableau de bord", status: "todo" }),
  projectOut("p3", { title: "API de prix", status: "to_redo" }),
  projectOut("p4", { title: "Export mensuel", status: "reviewing", session_id: "s4" }),
  projectOut("p5", { title: "Nettoyage de données", status: "brief_pending", brief: null }),
  projectOut("p6", { title: "Rapport final", status: "brief_failed", brief: null }),
];

describe("PortfolioPage", () => {
  it("groups the projects by status, what waits for January first, each card a link", async () => {
    setup({ projects: PROJECTS });
    await screen.findByRole("heading", { name: "To rework" });
    const headings = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
    expect(headings).toEqual([
      "To rework",
      "To do",
      "Under review",
      "Brief being prepared",
      "Brief to retry",
      "Validated",
    ]);
    const todo = screen.getByRole("region", { name: "To do" });
    expect(within(todo).getByRole("link", { name: "Tableau de bord" })).toHaveAttribute(
      "href",
      "/skills/portfolio/p2",
    );
    expect(within(todo).getByText("Status: To do")).toBeVisible();
    expect(within(todo).getByText("6 h estimated")).toBeVisible();
    const validated = screen.getByRole("region", { name: "Validated" });
    expect(within(validated).getByText("Status: Validated")).toBeVisible();
  });

  it("omits the groups that are empty", async () => {
    setup({ projects: [PROJECTS[1]!] });
    await screen.findByRole("heading", { name: "To do" });
    expect(screen.getAllByRole("heading", { level: 2 })).toHaveLength(1);
  });

  it("says the projects come with the weeks of the program when there are none", async () => {
    setup({ projects: [] });
    expect(
      await screen.findByRole("heading", { name: "No projects yet" }),
    ).toBeVisible();
    expect(
      screen.getByText("Your projects arrive with the weeks of your program."),
    ).toBeVisible();
  });

  it("opens the page of a project from its card", async () => {
    const { user, router } = setup({ projects: PROJECTS });
    await user.click(await screen.findByRole("link", { name: "Tableau de bord" }));
    expect(router.state.location.pathname).toBe("/skills/portfolio/p2");
    expect(await screen.findByRole("heading", { level: 1, name: "Tableau de bord" })).toBeVisible();
  });

  it("shows a loading state, then an error with « Réessayer » that reads again", async () => {
    let fail = true;
    const { user, state } = setup({
      projects: PROJECTS,
      listReply: () =>
        fail
          ? HttpResponse.json(apiError("internal_error", "Une erreur est survenue."), {
              status: 500,
            })
          : HttpResponse.json([]),
    });
    expect(screen.getByRole("status")).toHaveTextContent("Loading the Portfolio…");
    expect(await screen.findByRole("alert")).toHaveTextContent("Une erreur est survenue.");
    fail = false;
    await user.click(screen.getByRole("button", { name: "Retry" }));
    await screen.findByRole("heading", { name: "No projects yet" });
    expect(state.listReads).toBe(2);
  });

  it("reads the list at every opening (a status may have changed)", async () => {
    const { state, router } = setup({ projects: [PROJECTS[1]!] });
    await screen.findByRole("link", { name: "Tableau de bord" });
    await router.navigate("/skills");
    await screen.findByText("Page de la carte des compétences");
    await router.navigate("/skills/portfolio");
    await waitFor(() => expect(state.listReads).toBe(2));
  });
});
