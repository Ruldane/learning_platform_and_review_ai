import { screen, within } from "@testing-library/react";
import { HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { postingsApi, refusal } from "@/test/postingsApi";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { GapOverviewPage } from "./GapOverviewPage";

function setup(api: Parameters<typeof postingsApi>[0] = {}) {
  server.use(...postingsApi(api).handlers);
  return renderRoutes(
    [
      { path: "/carriere/ecarts", element: <GapOverviewPage /> },
      { path: "/carriere/offres", element: <p>Liste des offres</p> },
      { path: "/competences", element: <p>Carte des compétences</p> },
    ],
    "/carriere/ecarts",
  );
}

describe("GapOverviewPage", () => {
  it("lists the most missing skills and links to the skills map", async () => {
    const { user, router } = setup();
    const list = await screen.findByRole("list", { name: "Compétences les plus manquantes" });
    const items = within(list).getAllByRole("listitem");
    expect(items[0]).toHaveTextContent("Python — 5 offres, exigée dans 4");
    expect(items[1]).toHaveTextContent("Docker — 1 offre, jamais exigée");
    await user.click(screen.getByRole("link", { name: "Voir la carte des compétences" }));
    expect(router.state.location.pathname).toBe("/competences");
  });

  it("opens the skills map from a skill", async () => {
    const { user, router } = setup();
    await user.click(await screen.findByRole("button", { name: /Python/ }));
    expect(router.state.location.pathname).toBe("/competences");
  });

  it("offers to add a posting when nothing is missing yet", async () => {
    const { user, router } = setup({ top: () => HttpResponse.json([]) });
    expect(await screen.findByText("Aucun écart à afficher")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Ajouter une offre" }));
    expect(router.state.location.pathname).toBe("/carriere/offres");
  });

  it("shows a retryable error", async () => {
    let failing = true;
    const { user } = setup({
      top: () =>
        failing
          ? refusal(500, "internal_error", "Panne du serveur.")
          : HttpResponse.json([{ skill: "Python", postings: 2, required_in: 1 }]),
    });
    expect(screen.getByText("Chargement des écarts…")).toBeInTheDocument();
    expect(await screen.findByText("Panne du serveur.")).toBeInTheDocument();
    failing = false;
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(await screen.findByText("Python — 2 offres, exigée dans 1")).toBeInTheDocument();
  });
});
