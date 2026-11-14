import { screen, waitFor, within } from "@testing-library/react";
import { HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { apiError } from "@/test/councilHarness";
import { summaryOut } from "@/test/postingsApi";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { compareOut, graphOut, skillsApi } from "@/test/skillsApi";
import { SkillsPage } from "./SkillsPage";

function setup(api: Parameters<typeof skillsApi>[0] = {}) {
  const skills = skillsApi(api);
  server.use(...skills.handlers);
  const view = renderRoutes(
    [
      { path: "/competences", element: <SkillsPage /> },
      { path: "/apprendre/objectifs", element: <p>Objectifs</p> },
      { path: "/etudier/session", element: <p>Session guidée</p> },
      { path: "/carriere/offres", element: <p>Liste des offres</p> },
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

  describe("comparison with a posting", () => {
    const postings = () =>
      HttpResponse.json([
        summaryOut(),
        summaryOut({ id: "p2", title: "En cours", status: "analyzing" }),
        summaryOut({ id: "p3", title: null, status: "rejected" }),
      ]);

    it("compares with the posting picked in the list", async () => {
      const { user, reads } = setup({
        postings,
        compare: (request) =>
          new URL(request.url).searchParams.get("target") === "posting"
            ? HttpResponse.json({
                ...compareOut(),
                target_label: "Ingénieure données",
                coverage: 50,
              })
            : HttpResponse.json(compareOut()),
      });
      await user.click(screen.getByRole("tab", { name: "Comparaison" }));
      expect(await screen.findByText("Cible : Data engineer")).toBeInTheDocument();
      expect(reads.postings).toBe(0);
      await user.click(screen.getByRole("radio", { name: "Une offre" }));
      const select = await screen.findByRole("combobox", { name: "Offre" });
      expect(screen.getAllByRole("option")).toHaveLength(2);
      expect(screen.getByText("Choisis une offre pour la comparer à ta carte.")).toBeVisible();
      await user.selectOptions(select, "p1");
      expect(await screen.findByText("Cible : Ingénieure données")).toBeInTheDocument();
      expect(reads.compareQueries.at(-1)).toBe("?target=posting&posting_id=p1");
    });

    it("says when the posting has no computed gap yet", async () => {
      const { user } = setup({
        postings,
        compare: (request) =>
          new URL(request.url).searchParams.get("target") === "posting"
            ? HttpResponse.json(apiError("no_compare_target", "Pas d'écart."), { status: 404 })
            : HttpResponse.json(compareOut()),
      });
      await user.click(screen.getByRole("tab", { name: "Comparaison" }));
      await user.click(await screen.findByRole("radio", { name: "Une offre" }));
      await user.selectOptions(await screen.findByRole("combobox", { name: "Offre" }), "p1");
      expect(await screen.findByText(/n'a pas encore d'écart calculé/)).toBeInTheDocument();
    });

    it("offers to add a posting when none is analysed", async () => {
      const { user, router } = setup({ postings: () => HttpResponse.json([]) });
      await user.click(screen.getByRole("tab", { name: "Comparaison" }));
      await user.click(await screen.findByRole("radio", { name: "Une offre" }));
      expect(await screen.findByText("Aucune offre analysée")).toBeInTheDocument();
      await user.click(screen.getByRole("button", { name: "Ajouter une offre" }));
      expect(router.state.location.pathname).toBe("/carriere/offres");
    });

    it("shows a retryable error when the postings cannot be read", async () => {
      let failing = true;
      const { user } = setup({
        postings: () =>
          failing
            ? HttpResponse.json(apiError("internal_error", "Panne du serveur."), { status: 500 })
            : postings(),
      });
      await user.click(screen.getByRole("tab", { name: "Comparaison" }));
      await user.click(await screen.findByRole("radio", { name: "Une offre" }));
      expect(await screen.findByText("Panne du serveur.")).toBeInTheDocument();
      failing = false;
      await user.click(screen.getByRole("button", { name: "Réessayer" }));
      expect(await screen.findByRole("combobox", { name: "Offre" })).toBeInTheDocument();
    });
  });

  describe("empty states with an action (revue finale 5, C-m5)", () => {
    const empty = () => HttpResponse.json(graphOut({ nodes: [], edges: [], domains: [] }));

    it("offers to create a goal from an empty graph", async () => {
      const { user, router } = setup({ graph: empty });
      expect(await screen.findByText("Aucune compétence sur la carte")).toBeInTheDocument();
      await user.click(screen.getByRole("button", { name: "Créer un objectif" }));
      expect(router.state.location.pathname).toBe("/apprendre/objectifs");
    });

    it("offers to create a goal from an empty radar", async () => {
      const { user, router } = setup({ graph: empty });
      await user.click(screen.getByRole("tab", { name: "Radar" }));
      expect(await screen.findByText("Aucun domaine à afficher")).toBeInTheDocument();
      await user.click(screen.getByRole("button", { name: "Créer un objectif" }));
      expect(router.state.location.pathname).toBe("/apprendre/objectifs");
    });

    it("offers to study from an empty progress", async () => {
      const { user, router } = setup({ history: () => HttpResponse.json({ points: [] }) });
      await user.click(screen.getByRole("tab", { name: "Progression" }));
      expect(await screen.findByText("Aucun relevé pour l'instant")).toBeInTheDocument();
      await user.click(screen.getByRole("button", { name: "Commencer une session" }));
      expect(router.state.location.pathname).toBe("/etudier/session");
    });

    it("offers to see the goals from an empty comparison", async () => {
      const { user, router } = setup({
        compare: () => HttpResponse.json({ target_label: "Data", coverage: 0, rows: [] }),
      });
      await user.click(screen.getByRole("tab", { name: "Comparaison" }));
      expect(await screen.findByText("Aucune compétence à comparer")).toBeInTheDocument();
      await user.click(screen.getByRole("button", { name: "Voir mes objectifs" }));
      expect(router.state.location.pathname).toBe("/apprendre/objectifs");
    });
  });
});
