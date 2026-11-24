import { screen, waitFor, within } from "@testing-library/react";
import { HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { applicationOut } from "@/test/applicationsApi";
import { openStream, renderApplications } from "@/test/applicationsHarness";
import { councilEvents } from "@/test/councilEvents";
import { apiError } from "@/test/councilHarness";
import { createFakeSocketServer } from "@/test/fakeSocket";
import { kitApi, kitItem, type KitApiOptions } from "@/test/kitApi";
import { server } from "@/test/server";
import { applicationsManifest } from "../../manifest";
import { KitPage } from "./KitPage";

const KIT_ROUTE = "applications/:applicationId/kit";

function setup(options: KitApiOptions = {}, api: Parameters<typeof renderApplications>[2] = {}) {
  const sockets = createFakeSocketServer();
  const kit = kitApi(options);
  server.use(...kit.handlers);
  const routes = applicationsManifest.routes.map((route) =>
    route.path === KIT_ROUTE
      ? { path: route.path, element: <KitPage createSocket={sockets.factory} /> }
      : route,
  );
  const view = renderApplications(routes, "/applications/a1/kit", {
    applications: [applicationOut({ id: "a1", company: "Acme", title: "Data engineer" })],
    ...api,
  });
  return { ...view, sockets, kit };
}

const piece = (title: string) => screen.findByRole("region", { name: title });

describe("KitPage", () => {
  beforeEach(() => useSessionStore.getState().reset("k1"));

  it("introduces the kit before it is generated: the application, the promise, one button", async () => {
    setup();
    expect(
      await screen.findByRole("heading", { level: 1, name: "Kit de candidature" }),
    ).toBeVisible();
    expect(await screen.findByText("Acme, Data engineer")).toBeVisible();
    expect(screen.getByText(/Rien n'est envoyé par l'application/)).toBeVisible();
    expect(await screen.findByText(/Le kit n'a pas encore été généré/)).toBeVisible();
    expect(screen.getByRole("button", { name: "Générer le kit" })).toBeEnabled();
    expect(screen.queryByRole("region", { name: "Lettre de motivation" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Télécharger l'archive" })).toBeNull();
    expect(screen.getByRole("link", { name: "Retour à la fiche" })).toHaveAttribute(
      "href",
      "/applications/a1",
    );
  });

  it("starts the kit, follows its session and shows each piece as it arrives, announced aloud", async () => {
    const { user, sockets, kit } = setup();
    await user.click(await screen.findByRole("button", { name: "Générer le kit" }));
    await waitFor(() => expect(kit.state.starts).toBe(1));
    const stream = await openStream(sockets, "k1");
    expect(await screen.findByText(/Le kit se prépare/)).toHaveFocus();
    expect(screen.queryByRole("button", { name: "Générer le kit" })).toBeNull();
    expect((await piece("Lettre de motivation")).textContent).toContain("En préparation");

    const e = councilEvents("k1");
    kit.arrive("letter", { content: "Madame, Monsieur,", words: 2 });
    stream.push(e.artifactReady("kit_item", "k-letter", null));
    const letter = within(await piece("Lettre de motivation"));
    await waitFor(() =>
      expect(letter.getByLabelText("Texte : Lettre de motivation")).toHaveValue(
        "Madame, Monsieur,",
      ),
    );
    expect(letter.getByText("Prête")).toBeVisible();
    expect(await screen.findByText("Lettre de motivation : prête.")).toBeInTheDocument();
    expect(screen.getByText("1 pièce sur 7 est arrivée.")).toBeVisible();

    kit.arrive("pitch", { status: "to_check", flags: ["Kubernetes"], content: "Je suis Camille." });
    stream.push(e.artifactReady("kit_item", "k-pitch", null));
    expect(await screen.findByText("Pitch de présentation : à vérifier.")).toBeInTheDocument();
    expect(within(await piece("Pitch de présentation")).getByRole("note")).toHaveTextContent(
      "Absent de ton profil : Kubernetes.",
    );
    // La lettre déjà là n'est pas réannoncée, ni remplacée.
    expect(screen.getByText("2 pièces sur 7 sont arrivées.")).toBeVisible();
  });

  it("reads the kit again at the end of the run even when an artifact.ready was lost", async () => {
    const { user, sockets, kit } = setup();
    await user.click(await screen.findByRole("button", { name: "Générer le kit" }));
    const stream = await openStream(sockets, "k1");
    const e = councilEvents("k1");
    // Le serveur a rangé deux pièces, mais aucun artifact.ready n'est arrivé (coupure du back).
    kit.arrive("cv", { content: "CV ciblé" });
    kit.arrive("followups", {
      status: "failed",
      content: "",
      error: "Le modèle n'a pas répondu.",
      words: null,
    });
    kit.finish();
    stream.push(e.completed());
    const followups = within(await piece("Relances"));
    expect(await followups.findByText("Échec")).toBeVisible();
    expect(followups.getByRole("note")).toHaveTextContent("Le modèle n'a pas répondu.");
    expect((await piece("CV ciblé")).textContent).toContain("Prête");
    expect(
      await screen.findByText(
        /Le kit est terminé : 1 pièce prête, 0 pièces à vérifier, 1 pièce en échec\./,
      ),
    ).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Relancer le kit" })).toBeVisible();
  });

  it.each([
    ["posting_required", /ni offre liée ni texte d'offre.*Ajouter le texte de l'offre/],
    ["profile_required", /Aucun profil maître validé/],
  ])("explains a refused start (%s) and keeps the button", async (code, message) => {
    const { user } = setup({
      start: () => HttpResponse.json(apiError(code, "Refusé."), { status: 409 }),
    });
    await user.click(await screen.findByRole("button", { name: "Générer le kit" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    expect(screen.getByRole("button", { name: "Générer le kit" })).toBeEnabled();
    if (code === "profile_required") {
      expect(screen.getByRole("link", { name: "Ouvrir mon profil" })).toHaveAttribute(
        "href",
        "/career/profile",
      );
    }
  });

  it("shows why a piece is to check even with no flag: salary answers and a brief without sources", async () => {
    setup({
      items: [
        kitItem("form_answers", {
          status: "to_check",
          salary_fields: 1,
          content: "### Quelles sont vos prétentions ?\nÀ remplir par toi",
        }),
        kitItem("company_brief", {
          status: "to_check",
          content: "Acme [1]",
          sources: [{ rank: 1, url: "https://example.org/acme", title: "Acme, le site" }],
        }),
      ],
    });
    const form = within(await piece("Réponses au formulaire"));
    expect(form.getByRole("note")).toHaveTextContent("1 réponse salariale est à remplir par toi");
    expect(form.getByLabelText("Quelles sont vos prétentions ?")).toHaveAccessibleDescription(
      "À remplir par toi",
    );
    const brief = within(await piece("Dossier sur l'entreprise"));
    expect(brief.getByRole("note")).toHaveTextContent(/passages sans source ont été retirés/);
    expect(brief.getByRole("link", { name: /Acme, le site/ })).toHaveAttribute(
      "href",
      "https://example.org/acme",
    );
  });

  it("saves an edit only on request, re-reads a piece to check and shows its new status", async () => {
    const { user, kit } = setup({
      items: [
        kitItem("letter", {
          status: "to_check",
          flags: ["Kubernetes"],
          content: "Avec Kubernetes.",
        }),
      ],
    });
    const letter = within(await piece("Lettre de motivation"));
    await user.clear(letter.getByLabelText("Texte : Lettre de motivation"));
    await user.type(letter.getByLabelText("Texte : Lettre de motivation"), "Sans le terme.");
    expect(kit.state.patches).toEqual([]);
    await user.click(letter.getByRole("button", { name: "Enregistrer : Lettre de motivation" }));
    await waitFor(() =>
      expect(kit.state.patches).toEqual([{ kind: "letter", body: { content: "Sans le terme." } }]),
    );
    expect(await letter.findByText("Modification enregistrée. La pièce est prête.")).toBeVisible();
    expect(letter.getByText("Prête")).toBeVisible();
    expect(letter.getByText("Modifiée par toi")).toBeVisible();
    expect(letter.queryByRole("note")).toBeNull();
  });

  it("never blocks an edit while the kit runs", async () => {
    const { user, kit } = setup({
      running: true,
      sessionId: "k9",
      items: [kitItem("letter", { content: "Ancienne." })],
    });
    const letter = within(await piece("Lettre de motivation"));
    await user.type(letter.getByLabelText("Texte : Lettre de motivation"), " Corrigée.");
    await user.click(letter.getByRole("button", { name: "Enregistrer : Lettre de motivation" }));
    await waitFor(() => expect(kit.state.patches).toHaveLength(1));
    expect(await letter.findByText(/Modification enregistrée/)).toBeVisible();
  });

  it("shows the refusal of a save under the piece", async () => {
    const { user } = setup({
      items: [kitItem("letter")],
      patch: () =>
        HttpResponse.json(
          apiError("profile_required", "Ta modification n'est pas relue : aucun profil validé."),
          { status: 409 },
        ),
    });
    const letter = within(await piece("Lettre de motivation"));
    await user.type(letter.getByLabelText("Texte : Lettre de motivation"), "!");
    await user.click(letter.getByRole("button", { name: "Enregistrer : Lettre de motivation" }));
    expect(await letter.findByRole("alert")).toHaveTextContent(
      "Ta modification n'est pas relue : aucun profil validé.",
    );
  });

  it("copies the text of a piece to the clipboard", async () => {
    const { user } = setup({ items: [kitItem("pitch", { content: "Je suis Camille." })] });
    const pitch = within(await piece("Pitch de présentation"));
    await user.click(pitch.getByRole("button", { name: "Copier : Pitch de présentation" }));
    expect(await pitch.findByText("Copié dans le presse-papiers.")).toBeVisible();
    expect(await navigator.clipboard.readText()).toBe("Je suis Camille.");
  });

  it("offers the archive once a piece exists, as a download of kit.zip", async () => {
    setup({ items: [kitItem("cv")] });
    const link = await screen.findByRole("link", { name: "Télécharger l'archive" });
    expect(link).toHaveAttribute(
      "href",
      expect.stringMatching(/\/api\/v1\/applications\/a1\/kit\.zip$/),
    );
    expect(link).toHaveAttribute("download");
  });

  it("lets January cancel a running kit", async () => {
    const { user, state } = setup({ running: true, sessionId: "k9", items: [kitItem("cv")] });
    await user.click(await screen.findByRole("button", { name: "Annuler le kit" }));
    await waitFor(() => expect(state.cancels).toEqual(["k9"]));
  });

  it("says the application is gone on a 404", async () => {
    setup({}, { applications: [] });
    expect(await screen.findByText("Cette candidature n'existe plus.")).toBeVisible();
    expect(screen.getByRole("button", { name: "Retour au suivi" })).toBeVisible();
    // La page n'a plus que cet état : son titre est le seul h1.
    expect(screen.getByRole("heading", { level: 1, name: "Fiche introuvable" })).toBeVisible();
  });

  it("offers to retry when the kit cannot be read", async () => {
    let failures = 2;
    const { user } = setup({
      items: [kitItem("cv")],
      read: () => {
        if (failures-- <= 0) return undefined;
        return HttpResponse.json(apiError("internal_error", "Panne du serveur."), { status: 500 });
      },
    });
    await user.click(await screen.findByRole("button", { name: "Réessayer" }, { timeout: 5000 }));
    expect((await piece("CV ciblé")).textContent).toContain("Prête");
  });
});
