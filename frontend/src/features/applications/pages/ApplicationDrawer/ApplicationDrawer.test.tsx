import { screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { applicationOut, eventOut, reminderOut } from "@/test/applicationsApi";
import { renderApplications } from "@/test/applicationsHarness";
import { todayString } from "../../dates";
import { applicationsManifest } from "../../manifest";

const routes = applicationsManifest.routes;
// Une fiche neuve par test : l'API en mémoire change les lignes qu'on lui donne.
const todo = () =>
  applicationOut({
    id: "a2",
    company: "Beta",
    title: "Analyste",
    status: "to_apply",
    applied_on: null,
    due_reminders: 0,
    cv_version_number: null,
  });

function setup(path = "/applications/a1", api: Parameters<typeof renderApplications>[2] = {}) {
  return renderApplications(routes, path, {
    applications: [applicationOut({ cv_version_number: 2 }), todo()],
    ...api,
  });
}

async function openDrawer(path?: string, api?: Parameters<typeof renderApplications>[2]) {
  const view = setup(path, api);
  const dialog = await screen.findByRole("dialog", { name: /,/ });
  await within(dialog).findByLabelText("Entreprise");
  return { ...view, dialog };
}

describe("ApplicationDrawer", () => {
  it("shows the application: fields, contacts, history, version and tools", async () => {
    const { dialog } = await openDrawer("/applications/a1", {
      details: {
        a1: {
          events: [
            eventOut(),
            eventOut({
              id: "e2",
              kind: "note",
              at: "2026-11-05T10:00:00Z",
              text: "Appel avec la RH",
            }),
          ],
        },
      },
    });
    expect(dialog).toHaveAccessibleName("Acme, Data engineer");
    expect(within(dialog).getByLabelText("Entreprise")).toHaveValue("Acme");
    expect(within(dialog).getByLabelText("Notes")).toHaveValue("Premier échange par téléphone.");
    expect(within(dialog).getByLabelText("Nom, contact 1")).toHaveValue("Camille Durand");
    expect(within(dialog).getByText("Appel avec la RH")).toBeVisible();
    expect(within(dialog).getByText("Version 2 du CV")).toBeVisible();
    expect(within(dialog).getByRole("link", { name: "Voir mes versions de CV" })).toHaveAttribute(
      "href",
      "/career/cv/versions",
    );
    expect(within(dialog).getByRole("link", { name: "Kit de candidature" })).toHaveAttribute(
      "href",
      "/applications/a1/kit",
    );
    expect(within(dialog).getByRole("link", { name: "Entretien d'entraînement" })).toHaveAttribute(
      "href",
      "/applications/a1/interview",
    );
    expect(within(dialog).getByRole("link", { name: "Comité de recrutement" })).toHaveAttribute(
      "href",
      "/applications/a1/committee",
    );
  });

  it("saves only the fields that changed", async () => {
    const { user, state, dialog } = await openDrawer();
    const title = within(dialog).getByLabelText("Poste");
    await user.clear(title);
    await user.type(title, "Data engineer senior");
    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }));
    expect(state.patches).toEqual([{ id: "a1", body: { title: "Data engineer senior" } }]);
    expect(await within(dialog).findByText("Fiche enregistrée.")).toBeVisible();
    expect(dialog).toHaveAccessibleName("Acme, Data engineer senior");
  });

  it("keeps unsaved edits when another write in the drawer re-reads the application", async () => {
    const { user, state, dialog } = await openDrawer("/applications/a2");
    const title = within(dialog).getByLabelText("Poste");
    await user.clear(title);
    await user.type(title, "Analyste senior");
    await user.type(within(dialog).getByLabelText("Note"), "Rappeler jeudi");
    await user.click(within(dialog).getByRole("button", { name: "Ajouter la note" }));
    await within(dialog).findByText("Note ajoutée.");
    expect(within(dialog).getByLabelText("Poste")).toHaveValue("Analyste senior");
    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }));
    expect(state.patches).toEqual([{ id: "a2", body: { title: "Analyste senior" } }]);
  });

  it("takes the date a status change sets, and never sends it back as an edit", async () => {
    const { user, state, dialog } = await openDrawer("/applications/a2");
    expect(within(dialog).getByLabelText("Postulée le")).toHaveValue("");
    const company = within(dialog).getByLabelText("Entreprise");
    await user.clear(company);
    await user.type(company, "Beta SAS");
    await user.click(within(dialog).getByRole("button", { name: "J'ai postulé" }));
    await within(dialog).findByText("Statut changé : Postulée.");
    expect(within(dialog).getByLabelText("Postulée le")).toHaveValue(todayString());
    expect(within(dialog).getByLabelText("Entreprise")).toHaveValue("Beta SAS");
    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }));
    expect(state.patches).toEqual([{ id: "a2", body: { company: "Beta SAS" } }]);
  });

  it("clears the unsaved mark once its own save went through", async () => {
    const { user, dialog } = await openDrawer();
    const title = within(dialog).getByLabelText("Poste");
    await user.clear(title);
    await user.type(title, "Data engineer senior");
    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }));
    await within(dialog).findByText("Fiche enregistrée.");
    expect(within(dialog).getByLabelText("Poste")).toHaveValue("Data engineer senior");
    expect(within(dialog).getByRole("button", { name: "Enregistrer" })).toBeDisabled();
  });

  it("clears an optional field with null", async () => {
    const { user, state, dialog } = await openDrawer();
    await user.clear(within(dialog).getByLabelText("Notes"));
    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }));
    expect(state.patches[0]?.body).toEqual({ notes: null });
  });

  it("refuses an empty company and says so on the field", async () => {
    const { user, state, dialog } = await openDrawer();
    await user.clear(within(dialog).getByLabelText("Entreprise"));
    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }));
    expect(state.patches).toHaveLength(0);
    expect(within(dialog).getByLabelText("Entreprise")).toBeInvalid();
    expect(within(dialog).getByText("Obligatoire.")).toBeVisible();
  });

  it("refuses a contact without a name", async () => {
    const { user, state, dialog } = await openDrawer();
    await user.click(within(dialog).getByRole("button", { name: "Ajouter un contact" }));
    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }));
    expect(state.patches).toHaveLength(0);
    expect(within(dialog).getByText("Chaque contact a besoin d'un nom.")).toBeVisible();
  });

  it("saves the contacts, replacing the list", async () => {
    const { user, state, dialog } = await openDrawer();
    await user.click(within(dialog).getByRole("button", { name: "Ajouter un contact" }));
    await user.type(within(dialog).getByLabelText("Nom, contact 2"), "Sam Martin");
    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }));
    expect(state.patches[0]?.body).toEqual({
      contacts: [
        { name: "Camille Durand", role: "Responsable data", url: null },
        { name: "Sam Martin", role: null, url: null },
      ],
    });
  });

  it("records « J'ai postulé » at today's date by default", async () => {
    const { user, state, dialog } = await openDrawer("/applications/a2");
    await user.click(within(dialog).getByRole("button", { name: "J'ai postulé" }));
    expect(state.events).toEqual([
      { id: "a2", body: { kind: "status", status: "applied", on: todayString() } },
    ]);
    expect(await within(dialog).findByText("Statut changé : Postulée.")).toBeVisible();
    expect(within(dialog).queryByRole("button", { name: "J'ai postulé" })).toBeNull();
  });

  it("records « J'ai postulé » at the chosen date", async () => {
    const { user, state, dialog } = await openDrawer("/applications/a2");
    const day = within(dialog).getByLabelText("Date de candidature");
    await user.clear(day);
    await user.type(day, "2026-11-10");
    await user.click(within(dialog).getByRole("button", { name: "J'ai postulé" }));
    expect(state.events[0]?.body).toEqual({ kind: "status", status: "applied", on: "2026-11-10" });
  });

  it("bounds the dates of « J'ai postulé » and of a status change to today, and refuses a future one", async () => {
    const { user, state, dialog } = await openDrawer("/applications/a2");
    const applied = within(dialog).getByLabelText("Date de candidature");
    expect(applied).toHaveAttribute("max", todayString());
    expect(within(dialog).getByLabelText("Date du changement")).toHaveAttribute(
      "max",
      todayString(),
    );
    await user.clear(applied);
    await user.type(applied, "2999-01-01");
    await user.click(within(dialog).getByRole("button", { name: "J'ai postulé" }));
    expect(within(dialog).getByText("Cette date est dans le futur.")).toBeVisible();
    const changed = within(dialog).getByLabelText("Date du changement");
    await user.clear(changed);
    await user.type(changed, "2999-01-01");
    await user.click(within(dialog).getByRole("button", { name: "Changer le statut" }));
    expect(within(dialog).getAllByText("Cette date est dans le futur.")).toHaveLength(2);
    expect(state.events).toEqual([]);
  });

  it("changes the status at a date, with the interview date for Entretien", async () => {
    const { user, state, dialog } = await openDrawer();
    expect(within(dialog).queryByRole("option", { name: "Postulée" })).toBeNull();
    await user.selectOptions(within(dialog).getByLabelText("Nouveau statut"), "interview");
    await user.type(within(dialog).getByLabelText("Date de l'entretien"), "2026-11-25");
    await user.click(within(dialog).getByRole("button", { name: "Changer le statut" }));
    expect(state.events[0]).toEqual({
      id: "a1",
      body: { kind: "status", status: "interview", on: todayString(), interview_on: "2026-11-25" },
    });
    expect(await within(dialog).findByText("Statut changé : Entretien.")).toBeVisible();
  });

  it("lets January add the posting text to a fiche that has none, to open its kit", async () => {
    const { user, state, dialog } = await openDrawer();
    expect(within(dialog).getByText(/Cette fiche n'a pas de texte d'offre/)).toBeVisible();
    const add = within(dialog).getByRole("button", { name: "Ajouter le texte de l'offre" });
    expect(add).toBeDisabled();
    await user.type(
      within(dialog).getByLabelText("Texte de l'offre"),
      "Nous cherchons une data engineer.",
    );
    await user.click(add);
    expect(state.patches).toEqual([
      { id: "a1", body: { posting_text: "Nous cherchons une data engineer." } },
    ]);
    expect(await within(dialog).findByText(/Le texte de l'offre est enregistré/)).toBeVisible();
    expect(
      within(dialog).queryByRole("button", { name: "Ajouter le texte de l'offre" }),
    ).toBeNull();
  });

  it("offers no posting text field when the fiche already has one", async () => {
    const { dialog } = await openDrawer("/applications/a1", {
      details: { a1: { posting_text: "Texte déjà là." } },
    });
    expect(within(dialog).queryByLabelText("Texte de l'offre")).toBeNull();
    expect(within(dialog).getByText(/Le texte de l'offre est enregistré/)).toBeVisible();
  });

  it("adds a note to the history", async () => {
    const { user, state, dialog } = await openDrawer();
    await user.type(within(dialog).getByLabelText("Note"), "Rappeler jeudi");
    await user.click(within(dialog).getByRole("button", { name: "Ajouter la note" }));
    expect(state.events[0]).toEqual({ id: "a1", body: { kind: "note", text: "Rappeler jeudi" } });
    expect(await within(dialog).findByText("Note ajoutée.")).toBeVisible();
    expect(within(dialog).getByLabelText("Note")).toHaveValue("");
  });

  it("lists the pending reminders of the application and handles them", async () => {
    const reminders = [reminderOut(), reminderOut({ id: "r9", application_id: "a2" })];
    const { user, state, dialog } = await openDrawer("/applications/a1", { reminders });
    const card = await within(dialog).findByRole("article");
    expect(within(card).getByText("Relance LinkedIn à 7 jours")).toBeVisible();
    await user.click(within(card).getByRole("button", { name: "Fait" }));
    expect(state.reminderActions).toEqual([{ id: "r1", action: "done" }]);
    expect(
      await within(dialog).findByText("Aucune relance en attente pour cette fiche."),
    ).toBeVisible();
  });

  it("shows an error when the server refuses a write", async () => {
    const { user, dialog } = await openDrawer("/applications/a1", {
      event: () =>
        new Response(
          JSON.stringify({
            error: { code: "validation_error", message: "Date invalide.", details: null },
          }),
          {
            status: 422,
            headers: { "content-type": "application/json" },
          },
        ),
    });
    await user.type(within(dialog).getByLabelText("Note"), "x");
    await user.click(within(dialog).getByRole("button", { name: "Ajouter la note" }));
    expect(await within(dialog).findByText("Date invalide.")).toBeVisible();
  });

  it("closes with Escape and goes back to the board", async () => {
    const { user, router } = await openDrawer();
    await user.keyboard("{Escape}");
    await waitFor(() => expect(router.state.location.pathname).toBe("/applications"));
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("closes with its button", async () => {
    const { user, router, dialog } = await openDrawer();
    await user.click(within(dialog).getByRole("button", { name: "Fermer la fiche" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/applications"));
  });

  it("says when the application does not exist, and goes back to the board", async () => {
    const { user, router } = setup("/applications/inconnue");
    expect(await screen.findByText("Fiche introuvable")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Retour au suivi" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/applications"));
  });
});
