import { screen, waitFor, within } from "@testing-library/react";
import { HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { alertOut, applicationOut } from "@/test/applicationsApi";
import { renderApplications } from "@/test/applicationsHarness";
import { apiError } from "@/test/councilHarness";
import { createFakeSocketServer } from "@/test/fakeSocket";
import { todayString } from "../../dates";
import { expectCoherentOutline } from "@/test/headingOutline";
import { applicationsManifest } from "../../manifest";
import { NewApplicationPage } from "./NewApplicationPage";

function setup(api: Parameters<typeof renderApplications>[2] = {}) {
  const sockets = createFakeSocketServer();
  const routes = applicationsManifest.routes.map((route) =>
    route.path === "applications/new"
      ? { path: route.path, element: <NewApplicationPage createSocket={sockets.factory} /> }
      : route,
  );
  const view = renderApplications(routes, "/applications/new", {
    applications: [applicationOut({ id: "a1" }), applicationOut({ id: "a9", title: "Autre" })],
    ...api,
  });
  return { ...view, sockets };
}

describe("NewApplicationPage, à la main", () => {
  it("has one h1, then h2 sections (one h1 per applications page)", () => {
    setup();
    expectCoherentOutline();
  });

  it("caps the company and the title at 200 characters (company and title capped at 200)", () => {
    setup();
    expect(screen.getByLabelText("Entreprise")).toHaveAttribute("maxLength", "200");
    expect(screen.getByLabelText("Poste")).toHaveAttribute("maxLength", "200");
  });

  it("creates the application with what was typed and opens it", async () => {
    const { user, state, router } = setup();
    await user.type(screen.getByLabelText("Entreprise"), "Delta");
    await user.type(screen.getByLabelText("Poste"), "Développeuse");
    await user.selectOptions(screen.getByLabelText("Statut"), "applied");
    await user.type(screen.getByLabelText("Postulée le"), "2026-11-10");
    await user.selectOptions(screen.getByLabelText("Canal"), "linkedin");
    await user.click(screen.getByRole("button", { name: "Créer la fiche" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/applications/new1"));
    expect(state.creates).toEqual([
      {
        company: "Delta",
        title: "Développeuse",
        url: null,
        status: "applied",
        applied_on: "2026-11-10",
        channel: "linkedin",
        notes: null,
        contacts: [],
      },
    ]);
    expect(await screen.findByRole("dialog", { name: "Delta, Développeuse" })).toBeVisible();
  });

  it("sends no application date for a fiche still to apply", async () => {
    const { user, state } = setup();
    await user.type(screen.getByLabelText("Entreprise"), "Delta");
    await user.type(screen.getByLabelText("Poste"), "Développeuse");
    await user.type(screen.getByLabelText("Postulée le"), "2026-11-10");
    await user.click(screen.getByRole("button", { name: "Créer la fiche" }));
    await waitFor(() => expect(state.creates).toHaveLength(1));
    expect(state.creates[0]).toMatchObject({ status: "to_apply", applied_on: null });
  });

  it("refuses an empty company or title and says so", async () => {
    const { user, state } = setup();
    await user.click(screen.getByRole("button", { name: "Créer la fiche" }));
    expect(state.creates).toHaveLength(0);
    expect(screen.getAllByText("Obligatoire.")).toHaveLength(2);
    expect(screen.getByLabelText("Entreprise")).toBeInvalid();
  });

  it("bounds the application date to today and refuses a future one", async () => {
    const { user, state } = setup();
    const day = screen.getByLabelText("Postulée le");
    expect(day).toHaveAttribute("max", todayString());
    await user.type(screen.getByLabelText("Entreprise"), "Delta");
    await user.type(screen.getByLabelText("Poste"), "Développeuse");
    await user.selectOptions(screen.getByLabelText("Statut"), "applied");
    await user.type(day, "2999-01-01");
    await user.click(screen.getByRole("button", { name: "Créer la fiche" }));
    expect(state.creates).toHaveLength(0);
    expect(screen.getByText("Cette date est dans le futur.")).toBeVisible();
    expect(day).toBeInvalid();
  });

  it("refuses a contact without a name", async () => {
    const { user, state } = setup();
    await user.type(screen.getByLabelText("Entreprise"), "Delta");
    await user.type(screen.getByLabelText("Poste"), "Développeuse");
    await user.click(screen.getByRole("button", { name: "Ajouter un contact" }));
    await user.click(screen.getByRole("button", { name: "Créer la fiche" }));
    expect(state.creates).toHaveLength(0);
    expect(screen.getByText("Chaque contact a besoin d'un nom.")).toBeVisible();
  });

  it("sends the contacts with the application", async () => {
    const { user, state } = setup();
    await user.type(screen.getByLabelText("Entreprise"), "Delta");
    await user.type(screen.getByLabelText("Poste"), "Développeuse");
    await user.click(screen.getByRole("button", { name: "Ajouter un contact" }));
    await user.type(screen.getByLabelText("Nom, contact 1"), "Sam Martin");
    await user.click(screen.getByRole("button", { name: "Créer la fiche" }));
    await waitFor(() => expect(state.creates).toHaveLength(1));
    expect(state.creates[0]).toMatchObject({
      contacts: [{ name: "Sam Martin", role: null, url: null }],
    });
  });

  it("shows the duplicate alert on a 409 and offers its three choices", async () => {
    const { user, state, router } = setup({
      create: () =>
        HttpResponse.json(
          apiError("application_duplicate", "Cette fiche existe déjà.", { alerts: [alertOut()] }),
          { status: 409 },
        ),
    });
    await user.type(screen.getByLabelText("Entreprise"), "Acme");
    await user.type(screen.getByLabelText("Poste"), "Data engineer");
    await user.click(screen.getByRole("button", { name: "Créer la fiche" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Doublon probable");
    expect(alert).toHaveTextContent("Attention, tu as déjà une fiche chez Acme");
    expect(screen.queryByText("Cette fiche existe déjà.")).toBeNull();
    await user.click(within(alert).getByRole("button", { name: "Ouvrir la fiche existante" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/applications/a9"));
    expect(state.creates).toHaveLength(1);
  });

  it("creates the application with the confirmed distinct ones on « C'est un autre poste »", async () => {
    let answered = 0;
    const { user, state, router } = setup({
      create: () => {
        answered += 1;
        return answered === 1
          ? HttpResponse.json(
              apiError("application_duplicate", "Existe déjà.", { alerts: [alertOut()] }),
              { status: 409 },
            )
          : HttpResponse.json(
              {
                application: {
                  ...applicationOut({ id: "new2" }),
                  contacts: [],
                  events: [],
                  reminders: [],
                  notes: null,
                  letter: null,
                  posting_text: null,
                },
                info: [],
              },
              { status: 201 },
            );
      },
    });
    await user.type(screen.getByLabelText("Entreprise"), "Acme");
    await user.type(screen.getByLabelText("Poste"), "Data engineer");
    await user.click(screen.getByRole("button", { name: "Créer la fiche" }));
    await user.click(await screen.findByRole("button", { name: "C'est un autre poste" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/applications/new2"));
    expect(state.creates[1]).toMatchObject({ company: "Acme", distinct_from: ["a9"] });
  });

  it("closes the duplicate alert on Annuler and creates nothing", async () => {
    const { user, state } = setup({
      create: () =>
        HttpResponse.json(
          apiError("application_duplicate", "Existe déjà.", { alerts: [alertOut()] }),
          {
            status: 409,
          },
        ),
    });
    await user.type(screen.getByLabelText("Entreprise"), "Acme");
    await user.type(screen.getByLabelText("Poste"), "Data engineer");
    await user.click(screen.getByRole("button", { name: "Créer la fiche" }));
    await user.click(await screen.findByRole("button", { name: "Annuler" }));
    expect(screen.queryByRole("alert")).toBeNull();
    expect(state.creates).toHaveLength(1);
  });

  it("shows the same-company info once the application is created", async () => {
    const view = setup({
      create: () =>
        HttpResponse.json(
          {
            application: {
              ...applicationOut({ id: "new3", company: "Acme", title: "Autre poste" }),
              contacts: [],
              events: [],
              reminders: [],
              notes: null,
              letter: null,
              posting_text: null,
            },
            info: [
              alertOut({
                level: "info",
                message:
                  "Pour info : tu as postulé chez Acme il y a 12 jours, pour le poste Analyste.",
              }),
            ],
          },
          { status: 201 },
        ),
    });
    const { user } = view;
    view.rows.push(applicationOut({ id: "new3", company: "Acme", title: "Autre poste" }));
    await user.type(screen.getByLabelText("Entreprise"), "Acme");
    await user.type(screen.getByLabelText("Poste"), "Autre poste");
    await user.click(screen.getByRole("button", { name: "Créer la fiche" }));
    const note = await screen.findByRole("note");
    expect(note).toHaveTextContent("Pour info : tu as postulé chez Acme il y a 12 jours");
    expect(within(note).queryByRole("button")).toBeNull();
  });

  it("shows another refusal as an error", async () => {
    const { user } = setup({
      create: () =>
        HttpResponse.json(apiError("internal_error", "Le serveur ne répond pas."), { status: 500 }),
    });
    await user.type(screen.getByLabelText("Entreprise"), "Acme");
    await user.type(screen.getByLabelText("Poste"), "Data engineer");
    await user.click(screen.getByRole("button", { name: "Créer la fiche" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Le serveur ne répond pas.");
  });
});
