import { screen, waitFor, within } from "@testing-library/react";
import { HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { apiError } from "@/test/councilHarness";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { graphOut, skillsApi } from "@/test/skillsApi";
import { SkillsPage } from "./SkillsPage";

function setup(api: Parameters<typeof skillsApi>[0] = {}) {
  const skills = skillsApi(api);
  server.use(...skills.handlers);
  const view = renderRoutes(
    [
      { path: "/competences", element: <SkillsPage /> },
      { path: "/apprendre/objectifs", element: <p>Objectifs</p> },
    ],
    "/competences",
  );
  return { ...view, reads: skills.reads };
}

describe("SkillsPage", () => {
  it("shows the graph and opens a node", async () => {
    const { user, reads } = setup();
    const node = await screen.findByRole("button", { name: "CSS : En cours" });
    node.focus();
    await user.keyboard("{Enter}");
    const drawer = await screen.findByRole("dialog", { name: "CSS" });
    expect(reads.detail).toBe(1);
    expect(within(drawer).getByText("Programme web")).toBeInTheDocument();
    await user.click(within(drawer).getByRole("button", { name: "Fermer" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(node).toHaveFocus());
  });

  it("switches to radar, progress and compare", async () => {
    const { user } = setup();
    await user.click(screen.getByRole("tab", { name: "Radar" }));
    expect(await screen.findByText("web : 62 sur 100")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Progression" }));
    expect(await screen.findByText(/Dernier relevé, semaine du/)).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Comparaison" }));
    expect(await screen.findByText("Cible : Data engineer")).toBeInTheDocument();
    expect(screen.getByText("Atteint")).toBeInTheDocument();
    expect(screen.getByText("Manque 3 niveaux")).toBeInTheDocument();
  });

  it("offers to create a goal when there is nothing to compare with", async () => {
    const { user, router } = setup({
      compare: () =>
        HttpResponse.json(apiError("no_compare_target", "Aucun objectif."), { status: 404 }),
    });
    await user.click(screen.getByRole("tab", { name: "Comparaison" }));
    await user.click(await screen.findByRole("button", { name: "Créer un objectif" }));
    expect(router.state.location.pathname).toBe("/apprendre/objectifs");
  });

  it("shows an empty state, a loading state and a retryable error", async () => {
    let failing = true;
    const { user } = setup({
      graph: () =>
        failing
          ? HttpResponse.json(apiError("internal_error", "Panne du serveur."), { status: 500 })
          : HttpResponse.json(graphOut({ nodes: [], edges: [], domains: [] })),
    });
    expect(screen.getByText("Chargement de la carte…")).toBeInTheDocument();
    expect(await screen.findByText("Panne du serveur.")).toBeInTheDocument();
    failing = false;
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(await screen.findByText("Aucune compétence sur la carte")).toBeInTheDocument();
  });
});
