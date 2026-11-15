import { screen, waitFor, within } from "@testing-library/react";
import { HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { applicationOut } from "@/test/applicationsApi";
import { renderApplications } from "@/test/applicationsHarness";
import { apiError } from "@/test/councilHarness";
import { applicationsManifest } from "../../manifest";

const routes = applicationsManifest.routes;

const ROWS = () => [
  applicationOut({ id: "a1", company: "Acme", title: "Data engineer", status: "applied" }),
  applicationOut({
    id: "a2",
    company: "Beta",
    title: "Analyste",
    status: "to_apply",
    applied_on: null,
    next_action: null,
    next_action_on: null,
    due_reminders: 0,
  }),
  applicationOut({ id: "a3", company: "Gamma", title: "Chef de projet", status: "interview" }),
];

function setup(api: Parameters<typeof renderApplications>[2] = {}) {
  return renderApplications(routes, "/candidatures", { applications: ROWS(), ...api });
}

describe("BoardPage", () => {
  it("shows the indicators and the cards in the column of their status", async () => {
    setup();
    expect(await screen.findByRole("heading", { level: 1, name: "Candidatures" })).toBeVisible();
    const applied = await screen.findByRole("group", { name: "Postulée, 1" });
    expect(within(applied).getByText("Acme")).toBeVisible();
    expect(
      within(screen.getByRole("group", { name: "Entretien, 1" })).getByText("Gamma"),
    ).toBeVisible();
    expect(
      await screen.findByRole("region", { name: "Indicateurs des candidatures" }),
    ).toBeVisible();
  });

  it("moves a card with the menu: posts a status event and the card changes column", async () => {
    const { user, state } = setup();
    await user.click(await screen.findByRole("button", { name: "Déplacer « Analyste » (Beta)" }));
    await user.click(screen.getByRole("menuitem", { name: "Offre" }));
    expect(state.events).toEqual([{ id: "a2", body: { kind: "status", status: "offer" } }]);
    const offer = await screen.findByRole("group", { name: "Offre, 1" });
    expect(within(offer).getByText("Beta")).toBeVisible();
    expect(screen.getByRole("group", { name: "À postuler, 0" })).toBeVisible();
  });

  it("gives the focus back to the moved card", async () => {
    const { user } = setup();
    await user.click(await screen.findByRole("button", { name: "Déplacer « Analyste » (Beta)" }));
    await user.click(screen.getByRole("menuitem", { name: "Offre" }));
    await screen.findByRole("group", { name: "Offre, 1" });
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Déplacer « Analyste » (Beta)" })).toHaveFocus(),
    );
  });

  it("puts the card back and says so when the server refuses the move", async () => {
    const { user } = setup({
      event: () =>
        HttpResponse.json(apiError("validation_error", "Ce statut n'est pas permis."), {
          status: 422,
        }),
    });
    await user.click(await screen.findByRole("button", { name: "Déplacer « Analyste » (Beta)" }));
    await user.click(screen.getByRole("menuitem", { name: "Offre" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Ce statut n'est pas permis.");
    await waitFor(() => expect(screen.getByRole("group", { name: "À postuler, 1" })).toBeVisible());
    expect(screen.getByRole("group", { name: "Offre, 0" })).toBeVisible();
  });

  it("switches to the table, sorts it and keeps one row per application", async () => {
    const { user } = setup();
    await user.click(await screen.findByRole("button", { name: "Tableau" }));
    expect(screen.getByRole("button", { name: "Tableau" })).toHaveAttribute("aria-pressed", "true");
    const table = await screen.findByRole("table", { name: "Candidatures" });
    expect(within(table).getAllByRole("row")).toHaveLength(4);
    await user.click(screen.getByRole("button", { name: "Trier par Entreprise" }));
    await user.click(screen.getByRole("button", { name: "Trier par Entreprise" }));
    const first = within(within(table).getAllByRole("row")[1]!).getAllByRole("cell")[0]!;
    expect(first).toHaveTextContent("Gamma");
  });

  it("opens the application drawer above the board when a card is opened", async () => {
    const { user, router } = setup();
    await user.click(
      await screen.findByRole("button", { name: "Ouvrir la fiche de Acme, poste Data engineer" }),
    );
    expect(router.state.location.pathname).toBe("/candidatures/a1");
    expect(await screen.findByRole("dialog", { name: /Acme, Data engineer/ })).toBeVisible();
    // Le suivi reste monté derrière le tiroir (masqué aux lecteurs d'écran par la boîte modale).
    expect(screen.getByRole("group", { name: "Postulée, 1", hidden: true })).toBeInTheDocument();
  });

  it("offers to create the first application when there is none", async () => {
    const { user, router } = setup({ applications: [] });
    expect(await screen.findByText("Aucune candidature pour l'instant")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Nouvelle candidature" }));
    expect(router.state.location.pathname).toBe("/candidatures/nouvelle");
  });

  it("links to the new application page", async () => {
    const { user, router } = setup();
    await user.click(await screen.findByRole("link", { name: "Nouvelle candidature" }));
    expect(router.state.location.pathname).toBe("/candidatures/nouvelle");
  });

  it("says it is loading, then shows the board", async () => {
    setup();
    expect(screen.getByText("Chargement des candidatures…")).toBeVisible();
    expect(await screen.findByRole("group", { name: "Postulée, 1" })).toBeVisible();
  });

  it("shows an error with a retry when the list cannot be read", async () => {
    let calls = 0;
    const { user } = setup({
      list: () => {
        calls += 1;
        return calls === 1
          ? HttpResponse.json(apiError("internal_error", "Le serveur ne répond pas."), {
              status: 500,
            })
          : HttpResponse.json(ROWS());
      },
    });
    expect(await screen.findByRole("alert")).toHaveTextContent("Le serveur ne répond pas.");
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(await screen.findByRole("group", { name: "Postulée, 1" })).toBeVisible();
  });
});
