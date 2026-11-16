import { screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { openStream } from "@/test/applicationsHarness";
import { committeeOut, diffOut } from "@/test/committeeApi";
import { councilEvents } from "@/test/councilEvents";
import { setup } from "./committeeTestkit";

describe("CommitteePage", () => {
  beforeEach(() => useSessionStore.getState().reset("cm-s1"));

  it("introduces the committee with the application, the permanent simulation banner and the way back", async () => {
    setup();
    expect(
      await screen.findByRole("heading", { level: 1, name: "Comité de recrutement simulé" }),
    ).toBeVisible();
    expect(await screen.findByText("Acme, Data engineer")).toBeVisible();
    expect(screen.getByRole("note")).toHaveTextContent("Simulation, pas une prédiction.");
    expect(screen.getByRole("link", { name: "Retour à la fiche" })).toHaveAttribute(
      "href",
      "/candidatures/a1",
    );
    expect(await screen.findByText(/Aucun comité pour cette offre/)).toBeVisible();
    expect(screen.getByRole("button", { name: "Lancer le comité" })).toBeEnabled();
  });

  it("keeps the banner on every state of the page, results included", async () => {
    setup({ runs: [committeeOut()] });
    await screen.findByRole("tab", { name: "Verdict" });
    expect(screen.getByRole("note")).toHaveTextContent("Simulation, pas une prédiction.");
  });

  it("says a missing application in words, with a way back to the board", async () => {
    setup({}, {}, "/candidatures/zz/comite");
    expect(await screen.findByText("Cette candidature n'existe plus.")).toBeVisible();
    expect(screen.getByRole("heading", { level: 1, name: "Fiche introuvable" })).toBeVisible();
  });

  it("asks for an analysed offer when the application has none", async () => {
    setup({}, { posting_id: null });
    expect(await screen.findByText(/n'est liée à aucune offre analysée/)).toBeVisible();
    expect(screen.queryByRole("button", { name: /comité/ })).toBeNull();
    expect(screen.getByRole("note")).toHaveTextContent("Simulation, pas une prédiction.");
  });

  it("opens on the latest committee: its debate on the left, three tabs on the right, the verdict first", async () => {
    const { sockets } = setup({ runs: [committeeOut()] });
    const stream = await openStream(sockets, "cm-s1");
    const e = councilEvents("cm-s1");
    stream.push(
      e.message("ats_reader-impression", "Le CV passe bien le tri.", "ats_reader"),
      e.message("moderator-synthese", "Voici la synthèse.", "moderator"),
    );
    const feed = await screen.findByRole("region", { name: "Débat du comité" });
    expect(await within(feed).findByRole("article", { name: "Lecteur ATS" })).toBeVisible();
    expect(within(feed).getByRole("article", { name: "Modérateur" })).toBeVisible();

    const tabs = await screen.findAllByRole("tab");
    expect(tabs.map((tab) => tab.textContent)).toEqual(["Votes", "Verdict", "Avant / après"]);
    expect(screen.getByRole("tab", { name: "Verdict" })).toHaveAttribute("aria-selected", "true");
    const panel = screen.getByRole("tabpanel", { name: "Verdict" });
    expect(within(panel).getByText("Le comité dit :")).toBeVisible();
    expect(within(panel).getByText("Oui")).toBeVisible();
    expect(within(panel).getByText("Les voix : 3 oui ; 1 non ; 0 peut-être.")).toBeVisible();
  });

  it("nests its headings under the page title without skipping a level or doubling a region", async () => {
    setup({ runs: [committeeOut()] });
    await screen.findByRole("tab", { name: "Verdict" });
    expect(screen.getByRole("heading", { level: 2, name: "Verdict du comité" })).toBeVisible();
    expect(screen.getByRole("heading", { level: 3, name: /Objections/ })).toBeVisible();
    expect(screen.queryByRole("region", { name: "Verdict du comité" })).toBeNull();
    expect(screen.queryByRole("heading", { level: 4 })).toBeNull();
  });

  it("shows the four motivated votes with each main objection on the Votes tab, navigable by keyboard", async () => {
    const { user } = setup({ runs: [committeeOut()] });
    const verdict = await screen.findByRole("tab", { name: "Verdict" });
    verdict.focus();
    await user.keyboard("{ArrowLeft}");
    expect(screen.getByRole("tab", { name: "Votes" })).toHaveFocus();
    const panel = screen.getByRole("tabpanel", { name: "Votes" });
    const items = within(panel).getAllByRole("listitem");
    expect(items).toHaveLength(4);
    expect(items[2]).toHaveTextContent("Manager");
    expect(items[2]).toHaveTextContent("Non");
    expect(items[2]).toHaveTextContent("Objection de manager.");
    expect(items[2]).toHaveTextContent("Raison de manager.");
  });

  it("ranks the objections and the three changes, one of which is to acquire, on the Verdict tab", async () => {
    setup({ runs: [committeeOut()] });
    const panel = await screen.findByRole("tabpanel", { name: "Verdict" });
    const objections = within(panel)
      .getByRole("heading", { name: /Objections/ })
      .parentElement!.querySelectorAll("li");
    expect(objections).toHaveLength(2);
    expect(objections[0]).toHaveTextContent("Peu de résultats chiffrés.");
    const changes = within(
      within(panel).getByRole("heading", { name: "Trois changements à faire" }).parentElement!,
    ).getAllByRole("listitem");
    expect(changes).toHaveLength(3);
    expect(within(changes[1]!).getByText("À acquérir")).toBeVisible();
    expect(changes[1]).toHaveTextContent("ne l'écris pas dans ton CV");
    expect(within(changes[0]!).queryByText("À acquérir")).toBeNull();
  });

  it("says the first committee has nothing to compare, then shows the before and after of the next", async () => {
    const first = setup({ runs: [committeeOut()] });
    await first.user.click(await screen.findByRole("tab", { name: "Avant / après" }));
    expect(
      within(screen.getByRole("tabpanel", { name: "Avant / après" })).getByText(
        /C'est le premier comité/,
      ),
    ).toBeVisible();
  });

  it("compares with the previous committee: votes before and after, objections gone and new", async () => {
    const { user } = setup({
      runs: [committeeOut({ id: "c2", previous: diffOut({ previous_id: "c1" }) }), committeeOut()],
    });
    await user.click(await screen.findByRole("tab", { name: "Avant / après" }));
    const panel = screen.getByRole("tabpanel", { name: "Avant / après" });
    const rows = within(within(panel).getByRole("table")).getAllByRole("row").slice(1);
    expect(rows[0]).toHaveTextContent(/Lecteur ATS.*Non.*Oui.*Plus favorable/);
    expect(rows[1]).toHaveTextContent(/Recruteur.*Oui.*Oui.*Inchangé/);
    expect(within(panel).getByText("Mot clé Kubernetes absent.")).toBeVisible();
    expect(within(panel).getByText("Résumé trop long.")).toBeVisible();
  });

  it("says a failed committee ended without a verdict and offers to run it again", async () => {
    setup({
      runs: [
        committeeOut({ status: "failed", verdict: null, votes: [], objections: [], changes: [] }),
      ],
    });
    expect(
      await screen.findByText(/Le comité s'est arrêté sans verdict\. Tu peux le relancer\./),
    ).toBeVisible();
    expect(screen.getByRole("button", { name: "Relancer le comité" })).toBeEnabled();
  });
});
